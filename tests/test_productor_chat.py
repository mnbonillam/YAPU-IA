import unittest
import test_atlas
class ProductorChat(unittest.TestCase):
    setUp=test_atlas.Atlas.setUp
    tearDown=test_atlas.Atlas.tearDown
    call=test_atlas.Atlas.call
    def test_alta_consulta_persistencia_y_aislamiento(self):
        self.assertFalse(self.call('productor/chat')[1]['alta'])
        for text in ('ALTA Viacha/Papa/Floración','¿Hay riesgo de helada mañana?'):
            self.assertEqual(self.call('productor/chat',{'text':text})[0],200)
        view=self.call('productor/chat')[1]
        self.assertTrue(view['alta']);self.assertEqual(len(view['mensajes']),2)
        self.assertIn('Fuente:',view['mensajes'][-1]['respuesta'])
        self.cookie='';self.assertFalse(self.call('productor/chat')[1]['mensajes'])
    def test_laboratorio_chat_acuse(self):
        n=self.call('atlas')[1]['parcels'][0]['number']
        r=self.call('atlas/simulate',{'number':n,'scene':'Helada','factor':2})[1]
        a=self.call('productor/chat')[1]['avisos'][0];self.assertEqual(a['id'],r['id'])
        self.call('atlas/sim-ack',{'id':a['id']})
        self.assertTrue(self.call('productor/chat')[1]['avisos'][0]['acuse'])
        self.assertTrue(self.call('atlas/run?id='+str(a['id']))[1]['delivery']['acuse'])
