import json
import unittest
from unittest.mock import patch
import atlas,agro,app,core,canal
import test_sistema

class Atlas(unittest.TestCase):
    setUp=test_sistema.Flujo.setUp
    tearDown=test_sistema.Flujo.tearDown
    call=test_sistema.Flujo.call
    def dashboard(self):
        status,d=self.call('atlas');self.assertEqual(status,200,d);return d
    def register(self):
        pid=self.call('atlas/producer',dict(nombre='Productora de prueba',telefono='',comunidad='Viacha'))[1]['id']
        d=dict(productor=pid,name='Lote de ensayo',area=1.2,crop='Papa',stage='Floración',zone='Viacha',lat=-16.65,lon=-68.3,consent=True)
        num=self.call('atlas/parcel',d)[1]['number'];return pid,num,d
    def test_first_open_offline(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('La precarga debe ser local')):
            a=self.dashboard();b=self.dashboard()
        self.assertEqual(len(a['parcels']),5);self.assertEqual(len(b['producers']),2)
        for p in a['parcels']:
            self.assertTrue(p['weather']['current']);self.assertTrue(p['ejemplo'])
            history=self.call('atlas/history?number='+str(p['number']))[1]
            self.assertGreaterEqual(len(history['history']),168)
            self.assertTrue(history['evaluations'])
    def test_relation_update_archive(self):
        p,n,d=self.register()
        self.assertEqual(self.call('atlas/parcel',{**d,'number':n,'area':0})[0],400)
        self.assertEqual(self.call('atlas/parcel',{**d,'number':n,'area':3})[0],200)
        self.assertEqual(next(x for x in self.dashboard()['parcels'] if x['number']==n)['area'],3)
        self.call('atlas/archive',{'id':p});out=self.dashboard()
        self.assertFalse(next(x for x in out['producers'] if x['id']==p)['activo'])
        self.assertNotIn(n,[x['number'] for x in out['parcels']])
    def test_simulated_delivery_isolated(self):
        n=self.dashboard()['parcels'][0]['number'];old=self.call('atlas/history?number='+str(n))[1]
        _,r=self.call('atlas/simulate',dict(number=n,scene='Helada',factor=2))
        self.assertTrue(r['delivery']);self.assertNotEqual(r['baseline']['low'],r['scenario']['low'])
        self.call('atlas/sim-ack',{'id':r['id']})
        self.assertTrue(self.call('atlas/run?id='+str(r['id']))[1]['delivery']['acuse'])
        self.assertEqual(old,self.call('atlas/history?number='+str(n))[1])
        self.cookie='';self.assertEqual(self.call('atlas/run?id='+str(r['id']))[0],400)
    def test_workspaces(self):
        pid,n,_=self.register();self.cookie='';self.dashboard()
        self.assertEqual(self.call('atlas/history?number='+str(n))[0],400)
        self.assertEqual(self.call('atlas/archive',{'id':pid})[0],400)
    def test_weather_risk_notice_to_panel(self):
        pid,n,d=self.register();ref=self.dashboard()['parcels'][-1]['weather']
        ref['days'][0].update(low=-6,date=str(agro.now().date()));ref['stamp']=agro.now().isoformat()
        with patch('operaciones.forecast',return_value=ref):
            for _ in range(2):self.assertEqual(self.call('ops/refresh',{'number':n})[0],200)
        h=self.call('atlas/history?number='+str(n))[1]
        self.assertTrue(h['history']);self.assertTrue(h['evaluations']);self.assertTrue(h['notifications'])
        found=[a for a in h['alerts'] if a['kind']=='Helada' and a['day']==str(agro.now().date())]
        self.assertEqual(len(found),1);self.assertEqual(self.call('ops/ack',{'number':n,'alert':found[0]['id']})[0],200)
    def test_subscription_code_one_use(self):
        _,n,_=self.register();code=self.call('atlas/link',{'number':n})[1]['code']
        with core.db() as c:
            phone='59100000001';canal.respond(c,phone,{'text':{'body':'ALTA Viacha/Papa/Floración'}})
            cmd={'text':{'body':'VINCULAR '+code}}
            self.assertIn('Recibirás',canal.respond(c,phone,cmd));self.assertIn('vencido',canal.respond(c,phone,cmd))
    def test_climate_scenarios(self):
        n=self.dashboard()['parcels'][0]['number']
        for s in atlas.SCENARIOS:
            with self.subTest(s=s):
                status,r=self.call('atlas/simulate',dict(number=n,scene=s,factor=2))
                self.assertEqual(status,200);self.assertTrue(any(x['kind']==s for x in r['after']))
