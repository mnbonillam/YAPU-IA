"""Canal WhatsApp y planificador. Solo envía escenarios reales a números con alta."""
import hashlib
import hmac
import logging
import os
import threading
import urllib.request
import uuid
from core import *
import operaciones as ops

gate=threading.Lock()
schedule_wake=threading.Event()
def valid_signature(data,signature):
    key=os.getenv('WA_APP_SECRET','')
    return bool(key) and hmac.compare_digest(signature,'sha256='+hmac.new(key.encode(),data,hashlib.sha256).hexdigest())
def graph():
    return 'https://graph.facebook.com/'+os.environ['WA_GRAPH_VERSION']+'/'
def bearer(): return {'Authorization':'Bearer '+os.environ['WA_TOKEN']}
def send(phone,payload):
    return request_json(graph()+os.environ['WA_PHONE_ID']+'/messages',dict(messaging_product='whatsapp',to=phone,**payload),bearer())
def transcribe(media):
    if not os.getenv('OPENAI_API_KEY'): return None
    with urllib.request.urlopen(urllib.request.Request(graph()+media,headers=bearer()),timeout=10) as r: url=json.load(r)['url']
    with urllib.request.urlopen(urllib.request.Request(url,headers=bearer()),timeout=15) as r: audio=r.read(10_000_001)
    if len(audio)>10_000_000: return None
    boundary=uuid.uuid4().hex
    payload=(f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="nota.ogg"\r\nContent-Type: audio/ogg\r\n\r\n'.encode()+audio+f'\r\n--{boundary}--\r\n'.encode())
    req=urllib.request.Request('https://api.openai.com/v1/audio/transcriptions',data=payload,headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY'],'Content-Type':'multipart/form-data; boundary='+boundary})
    with urllib.request.urlopen(req,timeout=25) as r: return json.load(r)['text']
HELP = (
    "🌱 *¡Bienvenido a Yapu IA!*\n"
    "¿Cómo estará el tiempo en tu parcela? Registra tu cultivo para consultar el pronóstico y recibir avisos.\n\n"
    "*Para empezar*\nEnvía tu municipio, cultivo y etapa en este orden. Puedes copiar este ejemplo:\n"
    "ALTA Viacha/Papa/Floración\n\n"
    "*Opciones de registro*\n"
    f"• Municipios: {', '.join(ZONES)}.\n"
    f"• Cultivos: {', '.join(CROPS)}.\n"
    f"• Etapas: {', '.join(STAGES)}.\n\n"
    "*Tus datos*\nAl enviar ALTA aceptas guardar tu teléfono, parcela y consultas. "
    "Si usas voz y el servicio está habilitado, el proveedor de IA procesará el audio. "
    "Escribe BAJA para eliminar tu perfil."
)

def match(s,items): return next((v for v in items if norm(s.strip())==norm(v)),None)
def respond(c,phone,m,web_uid=None):
    p=c.execute('SELECT * FROM users WHERE phone=?',(phone,)).fetchone()
    if web_uid:
        # El canal de prueba tiene identidad propia para conservar todas las parcelas reales.
        row=c.execute("SELECT trial FROM channel_trials WHERE owner=?",(web_uid,)).fetchone()
        if not row:
            trial=create_user(c)
            c.execute('UPDATE users SET owner=? WHERE id=?',(web_uid,trial))
            c.execute('INSERT INTO channel_trials VALUES(?,?)',(web_uid,trial))
            web_uid=trial
        else: web_uid=row['trial']
        candidate=profile(c,web_uid); p=candidate if candidate['consent'] else None
    q=m.get('text',{}).get('body','').strip()
    if q.upper().startswith('ALTA '):
        vals=q[5:].split('/')
        if len(vals)!=3: return HELP
        z,cr,st=[match(v,opts) for v,opts in zip(vals,[ZONES,CROPS,STAGES])]
        if not all((z,cr,st)): return HELP
        uid=web_uid or (p['id'] if p else create_user(c,phone))
        update_profile(c,uid,dict(name="Parcela WhatsApp",zone=z,crop=cr,stage=st,mode="demo" if web_uid else "live",scene="Helada" if web_uid else "Estable",consent=True))
        return (f"✅ *Parcela registrada*\n\n📍 *Municipio:* {z}\n"
                f"🌱 *Cultivo:* {cr}\n*Etapa:* {st}\n\n"
                "*Tu primera consulta*\n¿Hay riesgo de helada mañana?\n\n"
                "También puedes compartir la ubicación de tu terreno para ajustar el pronóstico. "
                "Escribe BAJA para salir.")
    if not p: return HELP
    if norm(q).strip(" ¡!¿?.") in ("hola", "menu", "ayuda", "buenas", "buenos dias"):
        return (f"🌱 *Tu parcela en {p['zone']}*\n{p['crop']} · {p['stage']}\n\n"
                "*¿Qué quieres consultar?*\n"
                "• ¿Qué temperatura se espera hoy?\n• ¿Hay riesgo de helada mañana?\n"
                "• ¿Cómo reviso la humedad del suelo?\n\n"
                "Escribe tu pregunta o comparte la ubicación del terreno.")
    if m.get('type')=='location':
        point=m['location']
        update_profile(c,p['id'],{**dict(p),'consent':True,'lat':point['latitude'],'lon':point['longitude']})
        return '📍 *Ubicación guardada*\n\nLos próximos pronósticos usarán las coordenadas compartidas.'
    if q.upper().startswith('VINCULAR ') and not web_uid:
        key=hashlib.sha256(q.split(None,1)[1].strip().upper().encode()).hexdigest()
        row=c.execute('SELECT u.name FROM enlaces e JOIN users u ON u.id=e.parcela WHERE clave=? AND vence>? AND u.consent=1',(key,now().isoformat())).fetchone()
        if not row:return '🔗 *Código vencido o desconocido*\n\nAbre Alertas en el panel y genera un código nuevo.'
        c.execute('UPDATE enlaces SET receptor=?,clave=NULL,vence=NULL WHERE clave=?',(p['id'],key))
        return '🔔 *Parcela vinculada*\n\nRecibirás avisos de '+row[0]+'.\n\nEscribe BAJA para cancelar la suscripción.'
    if q.upper().startswith('ACUSE '):
        code=q[6:].strip()
        if not code.isdigit(): return '*Confirmar recepción*\nEnvía ACUSE seguido del número de tu aviso.\n\nEjemplo para el aviso 12:\nACUSE 12'
        changed=c.execute("UPDATE alerts SET ack=COALESCE(ack,?) WHERE id=? AND (user=? OR user IN (SELECT parcela FROM enlaces WHERE receptor=?)) AND active=1 AND day>=?",(now().isoformat(timespec='seconds'),int(code),p['id'],p['id'],str(now().date())))
        return '✅ *Acuse registrado*\nEl aviso quedó marcado como recibido.' if changed.rowcount else '*Aviso desconocido o finalizado*\nRevisa el número que figura en el aviso.'
    if q.upper()=='BAJA':
        if web_uid:
            c.execute('DELETE FROM users WHERE id=?',(web_uid,)); return 'Perfil de demostración eliminado.'
        c.execute('DELETE FROM users WHERE phone=?',(phone,)); c.execute('DELETE FROM inbox WHERE phone=?',(phone,))
        return '*Perfil eliminado*\nTu teléfono ha dejado de recibir alertas de esta parcela.'
    if q.upper().startswith('ECO '):
        parts=q.upper().split()
        if len(parts)!=4 or not parts[1].isdigit() or any(v not in ('SI','NO') for v in parts[2:]): return '*Cómo evaluar un aviso*\nEnvía ECO, el número del aviso y dos respuestas.\n\n• Primera: ¿ocurrió? SI o NO.\n• Segunda: ¿te sirvió? SI o NO.\n\nEjemplo para el aviso 12:\nECO 12 SI NO'
        res=c.execute('UPDATE alerts SET occurred=?,useful=? WHERE id=? AND (user=? OR user IN (SELECT parcela FROM enlaces WHERE receptor=?))',(parts[2]=='SI',parts[3]=='SI',parts[1],p['id'],p['id']))
        return '✅ *Observación guardada*\nGracias por contarnos qué pasó en tu parcela.' if res.rowcount else 'Alerta desconocida.'
    if m.get('type')=='audio':
        try: q=transcribe(m['audio']['id'])
        except Exception: q=None
        if not q: return '🎙️ *No pude leer la nota de voz*\nEnvíame la pregunta por escrito.'
    if not q: return 'Envía tu pregunta por texto o nota de voz.'
    try: return ask(c,dict(p),q,whatsapp=True)
    except ValueError as e: return str(e)

def webhook(body):
    for entry in body.get('entry',[]):
        for change in entry.get('changes',[]):
            value=change.get('value',{})
            if value.get('metadata',{}).get('phone_number_id')!=os.getenv('WA_PHONE_ID'): continue
            with db() as c:
                for event in value.get('statuses',[]):
                    reason=', '.join(str(e.get('code','')) for e in event.get('errors',[]))
                    ops.receipt(c,event['id'],event['status'],event['timestamp'],reason)
            for event in value.get('statuses',[]):
                with db() as c: owner=c.execute('SELECT user FROM timeline WHERE external=?',(event['id'],)).fetchone()
                if owner: ops.publish(owner['user'])
            for m in value.get('messages',[]):
                phone,mid=m['from'],m['id']
                with gate:
                    with db() as c:
                        c.execute('BEGIN IMMEDIATE')
                        row=c.execute('SELECT * FROM inbox WHERE id=?',(mid,)).fetchone()
                        if row and row['done']: continue
                        reply=row['reply'] if row else respond(c,phone,m)
                        who=c.execute('SELECT id FROM users WHERE phone=?',(phone,)).fetchone()
                        if who and m.get('timestamp'):
                            c.execute('UPDATE users SET last_inbound=max(coalesce(last_inbound,0),?) WHERE id=?',(int(m['timestamp']),who['id']))
                        if who: ops.log_message(c,who['id'],'WhatsApp','Productor',m.get('text',{}).get('body','['+m.get('type','mensaje')+']'),mid)
                        if not row: c.execute('INSERT INTO inbox VALUES(?,?,?,0)',(mid,phone,reply))
                    sent=send(phone,dict(type='text',text=dict(body=reply[:4000])))
                    with db() as c:
                        if who:
                            ext=sent['messages'][0]['id']
                            ops.log_message(c,who['id'],'WhatsApp','Asistente',reply,ext)
                            ops.receipt(c,ext,'accepted',time.time())
                        c.execute('UPDATE inbox SET done=1,phone=NULL,reply=NULL WHERE id=?',(mid,))
                if who: ops.publish(who['id'])
def tick():
    with db() as c: users=rows(c,'SELECT * FROM users WHERE consent=1')
    for p in users:
        try:
            w=ops.sample(p) if p['mode']=='live' else weather(p)
            with db() as c:
                active=risks(w['days'],p['crop'],p['stage'],w.get('current')) if p['mode']=='live' else evaluate(c,p,w)
                pending=rows(c,'SELECT * FROM alerts WHERE user=? AND ctx=? AND sent=0 ORDER BY day',(p['id'],ctx(p)))
            if p['mode']=='live': ops.publish(p['id'])
            with db() as c:
                recipient=c.execute('SELECT u.phone FROM enlaces e JOIN users u ON u.id=e.receptor WHERE e.parcela=? AND u.consent=1',(p['id'],)).fetchone()
            phone=recipient[0] if recipient else p['phone']
            if not (phone and p['mode']=='live' and os.getenv('WA_ALERT_TEMPLATE')): continue
            for r in pending:
                if not any(a['date']==r['day'] and a['kind']==r['kind'] for a in active): continue
                vals=[r['kind'],ctx(p),r['day'],r['evidence'],r['action'],r['source']+' · '+r['stamp']+' · Pronóstico incierto; umbral piloto',str(r['id'])]
                try:
                    sent=send(phone,dict(type='template',template=dict(name=os.environ['WA_ALERT_TEMPLATE'],language={'code':os.getenv('WA_LANGUAGE','es')},components=[{'type':'body','parameters':[{'type':'text','text':v} for v in vals]}])))
                except Exception:
                    with db() as c:c.execute("INSERT INTO envios_fallidos VALUES(?,1,'Pendiente de reintento',?) ON CONFLICT(alerta) DO UPDATE SET intentos=intentos+1,estado=excluded.estado,fecha=excluded.fecha",(r['id'],now().isoformat(timespec='seconds')))
                    continue
                with db() as c:
                    c.execute("UPDATE envios_fallidos SET estado='Aceptada en reintento',fecha=? WHERE alerta=?",(now().isoformat(timespec='seconds'),r['id']))
                    ext=sent['messages'][0]['id']
                    ops.log_message(c,p['id'],'WhatsApp','Alerta',' · '.join(vals),ext)
                    ops.receipt(c,ext,'accepted',time.time())
                    c.execute('UPDATE alerts SET sent=1 WHERE id=?',(r['id'],))
        except Exception as e: logging.warning('Revisión diferida (%s)',type(e).__name__)
def scheduler():
    while True:
        try: tick()
        except Exception as e: logging.warning('Planificador (%s)',type(e).__name__)
        schedule_wake.wait(600)
        schedule_wake.clear()

def operator_reply(p,body):
    """El equipo puede responder dentro de la ventana abierta por el productor."""
    body=clean(body,1000)
    if not p['phone'] or not all(os.getenv(k) for k in ('WA_TOKEN','WA_GRAPH_VERSION','WA_PHONE_ID')):
        raise ValueError('Esta parcela requiere un alta real por WhatsApp y un canal configurado.')
    if not p['last_inbound'] or time.time()-p['last_inbound']>=86400:
        raise ValueError('La ventana de atención venció. El productor debe escribir por WhatsApp.')
    try: result=send(p['phone'],dict(type='text',text=dict(body=body)))
    except Exception as e: raise ValueError('Meta no confirmó la solicitud. Revisa la conversación antes de reenviar.') from e
    mid=result['messages'][0]['id']
    with db() as c:
        ops.log_message(c,p['id'],'WhatsApp','Equipo',body,mid)
        ops.receipt(c,mid,'accepted',time.time())
