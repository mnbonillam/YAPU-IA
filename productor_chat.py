"""Conversación local del productor y notificaciones del laboratorio."""
import json
import os
import re
from agro import now
from core import rows, clean
from canal import respond

def install(c):
    c.execute("""CREATE TABLE IF NOT EXISTS chat_productor(
        id INTEGER PRIMARY KEY,owner TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        pregunta TEXT NOT NULL,respuesta TEXT NOT NULL,fecha TEXT NOT NULL)""")
def conversation(c,uid):
    exchanges=rows(c,'SELECT id,pregunta,respuesta,fecha FROM (SELECT * FROM chat_productor WHERE owner=? ORDER BY id DESC LIMIT 80) ORDER BY id',(uid,))
    alerts=rows(c,"""SELECT e.id,e.parcela,e.escenario,e.resultado,b.recibido,b.acuse
    FROM ensayos e JOIN envios_prueba b ON e.id=b.ensayo WHERE e.owner=? ORDER BY e.id DESC LIMIT 40""",(uid,))
    for a in alerts:
        result=json.loads(a.pop('resultado'))
        a.update(texto=result['notice'],nivel=result['level'])
    line=os.getenv('WA_PUBLIC_NUMBER','').lstrip('+')
    enabled=all(os.getenv(k) for k in ('WA_PHONE_ID','WA_TOKEN','WA_APP_SECRET','WA_GRAPH_VERSION','WA_VERIFY_TOKEN'))
    enrolled=c.execute('SELECT u.consent FROM channel_trials t JOIN users u ON u.id=t.trial WHERE t.owner=?',(uid,)).fetchone()
    return dict(mensajes=exchanges,avisos=alerts,alta=bool(enrolled and enrolled[0]),numero=line if enabled and re.fullmatch(r'[1-9]\d{6,14}',line) else None)
def message(c,uid,body):
    text=clean(body.get('text'),800)
    reply=respond(c,None,{'type':'text','text':{'body':text}},uid)
    c.execute('INSERT INTO chat_productor(owner,pregunta,respuesta,fecha) VALUES(?,?,?,?)',(uid,text,reply,now().isoformat(timespec='milliseconds')))
    return {'ok':True}
