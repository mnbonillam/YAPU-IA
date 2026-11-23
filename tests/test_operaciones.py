import http.client
import json
import threading
import time
import unittest
from unittest.mock import patch
import agro,app,canal,core,operaciones as ops
import test_sistema

class Monitor(unittest.TestCase):
    setUp=test_sistema.Flujo.setUp
    tearDown=test_sistema.Flujo.tearDown
    call=test_sistema.Flujo.call
    def parcel(self,name='Parcela A'):
        status,r=self.call('ops/parcel',dict(name=name,zone='Viacha',crop='Papa',stage='Floración',consent=True,lat=-16.654321,lon=-68.301234))
        self.assertEqual(status,200,r);return r['number']
    def sample(self,n,scene='Helada'):
        w=agro.forecast('Viacha','demo',scene)
        w.update(mode='live',source='Open-Meteo · prueba controlada',valid=agro.now().isoformat(),current={'temperature_2m':10})
        with patch('operaciones.forecast',return_value=w) as f:
            status,r=self.call('ops/refresh',{'number':n});self.assertEqual(status,200,r)
            self.assertEqual(f.call_args.args[3],(-16.654321,-68.301234))
    def test_no_artificial_parcels(self):
        self.assertEqual(self.call('ops')[1]['parcels'],[])
    def test_alert_lifecycle(self):
        n=self.parcel();self.sample(n);a=self.call('ops')[1]['alerts'][0]
        for i in range(2):
            self.assertEqual(self.call('ops/ack',{'number':n,'alert':a['id']})[0],200)
        self.assertTrue(self.call('ops')[1]['alerts'][0]['ack'])
        self.sample(n,'Estable');self.assertEqual(self.call('ops')[1]['alerts'],[])
    def test_multiple_and_private(self):
        first=self.parcel();second=self.parcel('Parcela B')
        self.assertEqual(len(self.call('ops')[1]['parcels']),2)
        self.cookie='';self.assertEqual(self.call('ops')[1]['parcels'],[])
        self.assertEqual(self.call('ops/message',{'number':second,'text':'texto'})[0],400)
        self.assertEqual(len(self.call('ops',admin=True)[1]['parcels']),2)
    def test_push_between_roles(self):
        n=self.parcel();seen=self.call('ops')[1]['version']
        cookie=self.cookie
        def post():
            time.sleep(.12)
            c=http.client.HTTPConnection(*self.srv.server_address)
            c.request('POST','/api/ops/message',json.dumps({'number':n,'text':'Hay escarcha en campo'}),{'Content-Type':'application/json','X-Yapu-Admin':app.ADMIN,'Cookie':cookie})
            c.getresponse().read();c.close()
        t=threading.Thread(target=post);t.start()
        start=time.monotonic();_,v=self.call('ops/wait?seen='+str(seen));t.join()
        self.assertGreater(v['version'],seen);self.assertLess(time.monotonic()-start,3)
        msg=self.call('ops')[1]['messages'][0];self.assertEqual(msg['direction'],'Equipo')
        self.assertEqual(msg['body'],'Hay escarcha en campo')
    def test_outage_keeps_labelled_snapshot(self):
        n=self.parcel();self.sample(n)
        with patch('operaciones.forecast',side_effect=OSError()):self.assertEqual(self.call('ops/refresh',{'number':n})[0],503)
        p=self.call('ops')[1]['parcels'][0];self.assertTrue(p['error']);self.assertTrue(p['weather'])
    def test_read_receipt_no_regression(self):
        with core.db() as c:
            ops.receipt(c,'wamid.test','read',123)
            ops.receipt(c,'wamid.test','sent',124)
            self.assertEqual(c.execute('SELECT status FROM receipts').fetchone()[0],'read')
    def test_webhook_status_and_operator_window(self):
        self.parcel()
        m=dict(id='in1',timestamp=str(int(time.time())),type='text',text={'body':'ALTA Viacha/Papa/Floración'})
        m['from']='59100000000'
        val={'metadata':{'phone_number_id':'test'},'messages':[m]}
        body={'entry':[{'changes':[{'value':val}]}]}
        with patch('canal.send',return_value={'messages':[{'id':'mid1'}]}):canal.webhook(body)
        val.pop('messages');val['statuses']=[{'id':'mid1','status':'delivered','timestamp':str(int(time.time()))}]
        canal.webhook(body)
        board=self.call('ops',admin=True)[1]
        reply=next(x for x in board['messages'] if x['direction']=='Asistente')
        self.assertEqual(reply['status'],'delivered')
        n=reply['number']
        with patch.dict('os.environ',{'WA_TOKEN':'test','WA_GRAPH_VERSION':'vTEST'}),patch('canal.send',return_value={'messages':[{'id':'mid2'}]}) as send:
            self.assertEqual(self.call('ops/whatsapp',{'number':n,'text':'Respuesta'},admin=True)[0],200)
            self.assertEqual(send.call_count,1)
            with core.db() as c:c.execute('UPDATE users SET last_inbound=1 WHERE rowid=?',(n,))
            self.assertEqual(self.call('ops/whatsapp',{'number':n,'text':'Otra'},admin=True)[0],400)
            self.assertEqual(send.call_count,1)
