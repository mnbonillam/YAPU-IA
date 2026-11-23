import sqlite3
import unittest
from unittest.mock import Mock
from opciones_wa import respuesta


class Opciones(unittest.TestCase):
    def test_registro_con_toques_y_consulta(self):
        with sqlite3.connect(':memory:') as c:
            c.row_factory = sqlite3.Row
            c.execute('CREATE TABLE users(phone TEXT, consent INTEGER)')
            def answer(conn, phone, message):
                query = message['text']['body']
                if query.startswith('ALTA '):
                    self.assertEqual(query, 'ALTA Viacha/Papa/Floración')
                    conn.execute('INSERT INTO users VALUES(?, 1)', (phone,))
                return query
            responder = Mock(side_effect=answer)
            msg = {'type':'text','text':{'body':'Hola'}}
            for pick in ('Registrar cultivo', 'Viacha', 'Papa', 'Floración', 'Aceptar y registrar', 'Clima de hoy'):
                payload = respuesta(c, 'test', msg, responder)['interactive']
                action = payload['action']
                if 'buttons' in action:
                    typ = 'button_reply'
                    items = [b['reply'] for b in action['buttons']]
                else:
                    typ = 'list_reply'
                    items = action['sections'][0]['rows']
                selected = next(i for i in items if i['title'] == pick)
                msg = {'type':'interactive','interactive':{'type':typ, typ:selected}}
            self.assertIn('temperatura', respuesta(c, 'test', msg, responder)['interactive']['body']['text'])
            self.assertEqual(c.execute('SELECT count(*) FROM users').fetchone()[0], 1)
