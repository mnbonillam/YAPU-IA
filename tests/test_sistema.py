import hashlib
import hmac
import http.client
import json
import os
import tempfile
import threading
import unittest
from contextlib import closing
from urllib.parse import quote
from pathlib import Path
from unittest.mock import patch
import agro,app,canal,core

class Flujo(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data=patch.object(core,'DATA',Path(self.tmp.name));self.data.start()
        self.env=patch.dict(os.environ,{'OPENAI_API_KEY':'','WA_PHONE_ID':'test','WA_APP_SECRET':'local-test'});self.env.start()
        core.init()
        self.srv=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        self.thread=threading.Thread(target=self.srv.serve_forever,daemon=True);self.thread.start()
        self.cookie=''
    def tearDown(self):
        self.srv.shutdown();self.srv.server_close();self.thread.join()
        self.env.stop();self.data.stop();self.tmp.cleanup()
    def call(self,path,data=None,admin=False):
        client=http.client.HTTPConnection(*self.srv.server_address,timeout=10)
        headers={'Cookie':self.cookie,'Content-Type':'application/json'}
        if admin:headers['X-Yapu-Admin']=app.ADMIN
        client.request('POST' if data is not None else 'GET','/api/'+path,json.dumps(data) if data is not None else None,headers)
        r=client.getresponse()
        if r.getheader('Set-Cookie'):self.cookie=r.getheader('Set-Cookie').split(';')[0]
        raw=json.loads(r.read());client.close();return r.status,raw
    def state(self):return self.call('state')[1]
    def consent(self):
        p=self.state()['profile'];p['consent']=True;p['mode']='demo'
        self.assertEqual(self.call('profile',p)[0],200)
    def test_context_and_dedup(self):
        self.consent();s=self.state();self.assertEqual(len(s['weather']['days']),7)
        self.assertEqual(s['alerts'],self.state()['alerts'])
        self.assertTrue(all(x['source'].startswith('Escenario') for x in s['alerts']))
    def test_all_scenarios(self):
        for name in agro.SCENES:
            with self.subTest(name=name):
                _,v=self.call('simulate',dict(scene=name,crop='Papa',stage='Floración'))
                if name=='Estable':self.assertEqual(v['risks'],[])
                else:self.assertIn(name,[r['kind'] for r in v['risks']])
    def test_sensitive_query_and_revision(self):
        self.assertEqual(self.call('chat',{'q':'¿Qué dosis aplico?'})[0],200)
        s=self.state();self.assertIn('técnico',s['chat'][0]['a'])
        cid=s['cases'][0]['id']
        self.assertEqual(self.call('admin/case',dict(id=cid,status='Revisado'),True)[0],200)
        self.assertEqual(self.state()['cases'][0]['status'],'Revisado')
    def test_retrieval_and_limit(self):
        for i in range(5):self.assertEqual(self.call('chat',{'q':'humedad del suelo'})[0],200)
        self.assertEqual(self.call('chat',{'q':'riego'})[0],400)
        self.assertIn('Fuente:',self.state()['chat'][0]['a'])
    def test_feedback_isolation(self):
        self.consent();aid=self.state()['alerts'][0]['id'];args={'id':aid,'occurred':False,'useful':True}
        self.assertEqual(self.call('feedback',args)[0],200)
        self.assertEqual(self.state()['alerts'][0]['useful'],1)
        self.cookie='';self.assertEqual(self.call('feedback',args)[0],400)
    def test_unicode_team_access(self):
        def status(path, headers):
            with closing(http.client.HTTPConnection(*self.srv.server_address, timeout=5)) as conn:
                conn.request('GET', path, headers=headers)
                response = conn.getresponse()
                response.read()
                return response.status

        password = 'Peña %20 🌱'
        with patch.object(app, 'ADMIN', password):
            headers = {'X-Yapu-Admin-UTF8': quote(password, safe='')}
            self.assertEqual(status('/api/admin', headers), 200)
            for path in ('/api/admin', '/api/ops', '/api/ops/wait?seen=-1'):
                self.assertEqual(status(path, {'X-Yapu-Admin-UTF8': 'equivocada'}), 403)
            self.assertEqual(status('/api/admin', {}), 403)
        with patch.object(app, 'ADMIN', 'Peña'):
            self.assertEqual(status('/api/admin', {'X-Yapu-Admin': 'Peña'}), 200)
        with patch.dict(os.environ, {'WA_VERIFY_TOKEN': password}):
            url = '/webhook?hub.mode=subscribe&hub.challenge=ok&hub.verify_token='
            self.assertEqual(status(url + quote(password), {}), 200)
            self.assertEqual(status(url + quote('falló'), {}), 403)
        self.assertFalse(canal.valid_signature(b'body', 'inválida'))

    def test_admin_access_and_edit(self):
        self.assertEqual(self.call('admin')[0],403)
        d=dict(title='Ficha de prueba',tags='panojas',crop='Quinua',body='Registrar observaciones.',source='Equipo')
        self.assertEqual(self.call('admin/doc',d,True)[0],200)
        docs=self.call('admin',admin=True)[1]['docs'];self.assertIn(d['title'],[x['title'] for x in docs])
    def test_live_outage(self):
        self.consent();p=self.state()['profile'];p.update(mode='live',consent=True)
        self.call('profile',p)
        with patch('core.weather',side_effect=OSError()):
            s=self.state();self.assertIsNone(s['weather']);self.assertTrue(s['error']);self.assertFalse(s['risks'])
    def test_market_bilateral(self):
        self.consent();seller=self.cookie
        self.call('market',dict(action='offer',price='1000.00',crop='Papa',description='Lote demo'))
        oid=self.state()['market'][0]['id']
        self.assertEqual(self.call('market',dict(action='reserve',id=oid))[0],400)
        self.cookie='';self.consent()
        self.assertEqual(self.call('market',dict(action='reserve',id=oid))[0],200)
        self.call('market',dict(action='confirm',id=oid))
        self.assertEqual(self.state()['market'][0]['fee'],0)
        self.cookie=seller;self.call('market',dict(action='confirm',id=oid))
        lot=self.state()['market'][0];self.assertEqual((lot['status'],lot['fee']),('Confirmada',2000))
    def test_channel_onboarding(self):
        _,r=self.call('channel',{'text':'ALTA Achacachi/Quinua/Emergencia'})
        self.assertIn('registrada',r['reply'])
        self.assertEqual(self.state()['profile']['crop'],'Papa')
        self.assertEqual(self.call('ops')[1]['parcels'],[])
        self.assertIn('Fuente:',self.call('channel',{'text':'¿Habrá helada?'})[1]['reply'])
    def test_whatsapp_duplicate(self):
        m={'id':'m1','from':'59100000000','type':'text','text':{'body':'ALTA Viacha/Papa/Floración'}}
        b={'entry':[{'changes':[{'value':{'metadata':{'phone_number_id':'test'},'messages':[m]}}]}]}
        with patch('canal.send',return_value={'messages':[{'id':'out1'}]}) as send:
            canal.webhook(b);canal.webhook(b);self.assertEqual(send.call_count,1)
        with core.db() as c:self.assertEqual(c.execute("SELECT mode FROM users WHERE phone=?",(m['from'],)).fetchone()[0],'live')
    def test_whatsapp_directory(self):
        self.call('channel', {'text':'ALTA Achacachi/Quinua/Emergencia'})
        phone='59100001234'
        with core.db() as c:
            canal.respond(c,phone,{'text':{'body':'ALTA Viacha/Papa/Floración'}})
        self.assertEqual(self.call('admin/whatsapp')[0],403)
        status,body=self.call('admin/whatsapp',admin=True)
        self.assertEqual(status,200)
        records=body['registrations']
        self.assertEqual(len(records),1)
        self.assertEqual([records[0][k] for k in ('ending','zone','crop','stage')],
                         ['1234','Viacha','Papa','Floración'])
        self.assertNotIn(phone,json.dumps(body))
        with core.db() as c:
            canal.respond(c,phone,{'text':{'body':'BAJA'}})
        self.assertEqual(self.call('admin/whatsapp',admin=True)[1]['registrations'],[])

    def test_signature(self):
        data=b'example';sig=hmac.new(b'local-test',data,hashlib.sha256).hexdigest()
        self.assertTrue(canal.valid_signature(data,'sha256='+sig));self.assertFalse(canal.valid_signature(data,'sha256=bad'))
    def test_forecast_provider_and_cache(self):
        import io
        from datetime import timedelta
        dates=[str(agro.now().date()+timedelta(days=i)) for i in range(7)]
        payload={'daily':{'time':dates,'temperature_2m_min':[3]*7,'temperature_2m_max':[19]*7,'precipitation_sum':[2]*7,'wind_gusts_10m_max':[25]*7,'weather_code':[3]*7}}
        payload['current']=dict(time=agro.now().strftime('%Y-%m-%dT%H:%M'),temperature_2m=12,relative_humidity_2m=40,wind_speed_10m=10,precipitation=0)
        payload['daily']['precipitation_probability_max']=[15]*7
        with patch.dict(agro.CACHE,{},clear=True),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(payload).encode())) as req:
            a=agro.forecast('Viacha','live','Estable')
            b=agro.forecast('Viacha','live','Helada')
            self.assertEqual(req.call_count,1);self.assertEqual(a,b)
            self.assertEqual(a['days'][1]['low'],3);self.assertEqual(a['mode'],'live')

    def test_association_limit(self):
        with core.db() as c:
            for i in range(50):
                uid=core.create_user(c);c.execute("UPDATE users SET plan='Asociación' WHERE id=?",(uid,))
            uid=core.create_user(c)
            n=c.execute('SELECT rowid FROM users WHERE id=?',(uid,)).fetchone()[0]
        self.assertEqual(self.call('admin/plan',dict(number=n,plan='Asociación'),True)[0],400)

    def test_profile_deletion_releases_reservation(self):
        self.consent();seller=self.cookie
        self.call('market',dict(action='offer',price='12.50',crop='Quinua',description='Muestra'))
        oid=self.state()['market'][0]['id'];self.cookie='';self.consent()
        self.call('market',dict(action='reserve',id=oid));self.call('delete',{})
        self.cookie=seller;self.assertEqual(self.state()['market'][0]['status'],'Abierta')

    def test_scheduler_delivery(self):
        with core.db() as c:
            canal.respond(c,'59100000000',{'text':{'body':'ALTA Viacha/Papa/Floración'}})
        w=agro.forecast('Viacha','demo','Helada');w['source']='Proveedor de prueba';w['mode']='live'
        with patch.dict(os.environ,{'WA_ALERT_TEMPLATE':'alerta'}),patch('operaciones.forecast',return_value=w),patch('canal.send',return_value={'messages':[{'id':'out1'}]}) as send:
            canal.tick();count=send.call_count;self.assertGreater(count,0);canal.tick();self.assertEqual(count,send.call_count)

if __name__=='__main__':unittest.main()
