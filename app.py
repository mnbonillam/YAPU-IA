import argparse
import http.cookies
import urllib.error
import logging
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs,unquote_to_bytes
from core import *
from canal import operator_reply
import operaciones as ops
import atlas
import productor_chat
from mercado import mutate
from canal import respond,valid_signature,webhook,scheduler,schedule_wake

ADMIN=secrets.token_urlsafe(16)
PUBLIC=os.getenv('YAPU_HTTPS','')=='1'
class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args): pass
    def out(self,data,status=200,mime='application/json; charset=utf-8'):
        raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin'); self.send_header('X-Frame-Options','DENY')
        if getattr(self,'new_cookie',None):
            self.send_header('Set-Cookie','yapu='+self.new_cookie+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000'+('; Secure' if PUBLIC else ''))
        self.end_headers(); self.wfile.write(raw)
    def identity(self):
        jar=http.cookies.SimpleCookie(self.headers.get('Cookie','')); val=jar.get('yapu')
        with db() as c:
            if val and c.execute("SELECT 1 FROM users WHERE id=? AND phone IS NULL",(val.value,)).fetchone(): return val.value
            self.new_cookie=create_user(c); return self.new_cookie
    def team_requested(self):
        return bool(self.headers.get('X-Yapu-Admin-UTF8') or self.headers.get('X-Yapu-Admin'))

    def admin(self):
        encoded = self.headers.get('X-Yapu-Admin-UTF8')
        if encoded is None:
            supplied = self.headers.get('X-Yapu-Admin', '').encode('utf-8')
        elif encoded.isascii():
            supplied = unquote_to_bytes(encoded)
        else:
            supplied = b''
        if not supplied or not secrets.compare_digest(supplied, ADMIN.encode('utf-8')):
            raise PermissionError('La clave de administración es incorrecta.')
    def do_GET(self):
        path=urlsplit(self.path).path
        try:
            if path=='/api/productor/chat':
                uid=self.identity()
                with db() as c:return self.out(productor_chat.conversation(c,uid))
            if path.startswith('/api/atlas'):
                uid=self.identity()
                with db() as c:
                    if path=='/api/atlas':
                        if not c.execute('SELECT 1 FROM atlas_spaces WHERE owner=?',(uid,)).fetchone():
                            atlas.seed(c,uid);c.commit();schedule_wake.set()
                        return self.out(atlas.dashboard(c,uid))
                    query=parse_qs(urlsplit(self.path).query)
                    if path=='/api/atlas/history':return self.out(atlas.detail(c,uid,query.get('number',[''])[0]))
                    if path=='/api/atlas/run':
                        row=c.execute('SELECT resultado FROM ensayos WHERE owner=? AND id=?',(uid,query.get('id',[''])[0])).fetchone()
                        if not row:raise ValueError('Ensayo desconocido.')
                        result=json.loads(row[0]);n=query['id'][0];result['id']=int(n)
                        delivery=c.execute('SELECT destinatario,recibido,acuse FROM envios_prueba WHERE ensayo=?',(n,)).fetchone()
                        if delivery:result['delivery']=dict(delivery)
                        return self.out(result)
                    return self.out({'error':'Ruta desconocida'},404)
            if path=='/api/reference':
                try: return self.out(forecast('Viacha','live','Estable',force='refresh=1' in self.path))
                except Exception: return self.out({'error':'Sin clima vigente de Viacha.'},503)
            if path in ('/api/ops','/api/ops/wait'):
                team=self.team_requested()
                if team: self.admin()
                uid=self.identity()
                if path.endswith('/wait'):
                    seen=int(parse_qs(urlsplit(self.path).query).get('seen',['0'])[0])
                    return self.out({'version':ops.await_change(uid,team,seen)})
                rev=ops.revision(uid,team)
                with db() as c: return self.out({**ops.board(c,uid,team),'version':rev})
            if path=='/api/state': return self.out(state(self.identity()))
            if path=='/api/health': return self.out({'ok':True})
            if path=='/api/admin':
                self.admin()
                with db() as c:
                    users=rows(c,'SELECT rowid AS number,name,zone,crop,plan FROM users ORDER BY rowid DESC')
                    stats=dict(c.execute('SELECT count(*) AS alerts,count(occurred) AS responses,sum(occurred) AS occurred,sum(useful) AS useful FROM alerts').fetchone())
                    return self.out(dict(users=users,stats=stats,docs=rows(c,'SELECT * FROM knowledge ORDER BY id'),cases=rows(c,'SELECT cases.id,users.name,question,status FROM cases JOIN users ON users.id=cases.user ORDER BY cases.id DESC')))
            if path=='/webhook':
                q=parse_qs(urlsplit(self.path).query); token=os.getenv('WA_VERIFY_TOKEN','')
                if token and q.get('hub.mode')==['subscribe'] and secrets.compare_digest(q.get('hub.verify_token',[''])[0].encode(),token.encode()):
                    return self.out(q.get('hub.challenge',[''])[0].encode(),mime='text/plain')
                raise PermissionError('Verificación denegada')
            filename={'/':'atlas.html','/cuaderno':'index.html','/whatsapp':'whatsapp.html','/app.js':'app.js','/style.css':'style.css','/campo.webp':'campo.webp','/marca.png':'marca.png'}.get(path)
            extra=['whatsapp.js','whatsapp.css','atlas.js','atlas.css','ops.js','ops.css','vendor/leaflet.min.js','vendor/leaflet.css']
            if path[1:] in extra: filename=path[1:]
            if filename: return self.out((ROOT/'web'/filename).read_bytes(),mime=mimetypes.guess_type(filename)[0] or 'application/octet-stream')
            self.out({'error':'Ruta desconocida'},404)
        except PermissionError as e: self.out({'error':str(e)},403)
        except ValueError as e: self.out({'error':str(e)},400)
        except Exception: logging.exception('Error de lectura'); self.out({'error':'No se pudo abrir la vista.'},500)
    def receive_whatsapp(self):
        stage = 'longitud'
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1000000:
                logging.warning('WhatsApp 400: longitud ausente o fuera de rango; fragmentado=%s',
                                self.headers.get('Transfer-Encoding', '').lower() == 'chunked')
                return self.out({'error': 'Tamaño inválido'}, 400)
            raw = self.rfile.read(length)
            if not valid_signature(raw, self.headers.get('X-Hub-Signature-256', '')):
                logging.warning('WhatsApp 403: firma inválida')
                return self.out({'error': 'Firma inválida'}, 403)
            stage = 'JSON'
            body = json.loads(raw)
            stage = 'evento'
            for entry in body.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    matches = value.get('metadata', {}).get('phone_number_id') == os.getenv('WA_PHONE_ID')
                    counts = (len(value.get('messages', [])), len(value.get('statuses', [])))
                    if matches:
                        print('WhatsApp evento: mensajes=%d estados=%d' % counts, flush=True)
                    else:
                        logging.warning('WhatsApp evento de otro número: mensajes=%d estados=%d', *counts)
                    for status in value.get('statuses', []):
                        if status.get('status') == 'failed':
                            codes = [e.get('code') for e in status.get('errors', []) if isinstance(e.get('code'), int)]
                            logging.warning('WhatsApp entrega fallida: codigos_meta=%s', codes)
            stage = 'procesamiento'
            webhook(body)
        except urllib.error.HTTPError as exc:
            try:
                code = json.loads(exc.read(16384)).get('error', {}).get('code')
            except (ValueError, AttributeError):
                code = None
            logging.warning('WhatsApp solicitud externa rechazada: HTTP=%d codigo_meta=%s',
                            exc.code, code if isinstance(code, int) else 'desconocido')
            return self.out({'error': 'Envío pendiente'}, 503)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            field = exc.args[0] if isinstance(exc, KeyError) and exc.args else None
            known = ('id', 'from', 'status', 'timestamp', 'messages', 'WA_TOKEN', 'WA_PHONE_ID', 'WA_GRAPH_VERSION')
            logging.warning('WhatsApp 400: etapa=%s tipo=%s campo=%s', stage, type(exc).__name__,
                            field if field in known else '-')
            return self.out({'error': 'Evento inválido'}, 400)
        return self.out({'ok': True})

    def do_POST(self):
        try:
            if self.path=='/webhook': return self.receive_whatsapp()
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=1000000: raise ValueError('Tamaño inválido')
            raw=self.rfile.read(length)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise ValueError('Se requiere JSON')
            d=json.loads(raw)
            if not isinstance(d,dict): raise ValueError('Formato inválido')
            uid=self.identity()
            if self.path=='/api/productor/chat':
                with db() as c:
                    c.execute('BEGIN IMMEDIATE');result=productor_chat.message(c,uid,d)
                ops.publish(uid);return self.out(result)
            if self.path.startswith('/api/atlas/'):
                action=self.path.rsplit('/',1)[1]
                with db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    if action=='producer': result=atlas.producer(c,uid,d)
                    elif action=='parcel':
                        p=atlas.plant(c,uid,d.get('productor'),d)
                        result={'number':c.execute('SELECT rowid FROM users WHERE id=?',(p['id'],)).fetchone()[0]}
                    elif action=='archive': atlas.deactivate(c,uid,d);result={'ok':True}
                    elif action=='simulate':result=atlas.simulate(c,uid,d)
                    elif action=='sim-ack':
                        if not c.execute('UPDATE envios_prueba SET acuse=COALESCE(acuse,?) WHERE ensayo=? AND ensayo IN (SELECT id FROM ensayos WHERE owner=?)',(now().isoformat(timespec='seconds'),d.get('id'),uid)).rowcount:raise ValueError('Notificación de ensayo desconocida.')
                        result={'ok':True}
                    elif action=='link':result=atlas.link_code(c,uid,d)
                    else:raise ValueError('Acción desconocida.')
                ops.publish(uid)
                return self.out(result)
            if self.path.startswith('/api/ops/'): 
                team=self.team_requested()
                if team: self.admin()
                action=self.path.rsplit('/',1)[1]
                with db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    if action=='parcel':
                        result={'number':ops.save(c,uid,d,team)}
                        p=ops.access(c,uid,result['number'],team)
                    elif action=='ack':
                        p=ops.access(c,uid,d.get('number'),team)
                        ops.acknowledge(c,uid,d,team);result={'ok':True}
                    elif action=='ask':
                        p=ops.access(c,uid,d.get('number'),team)
                        question=clean(d.get('text'),800);reply=ask(c,p,question)
                        ops.log_message(c,p['id'],'Panel','Equipo' if team else 'Productor',question)
                        ops.log_message(c,p['id'],'Panel','Asistente',reply);result={'ok':True}
                    elif action=='message':
                        p=ops.access(c,uid,d.get('number'),team)
                        ops.log_message(c,p['id'],'Panel','Equipo' if team else 'Productor',clean(d.get('text'),1000));result={'ok':True}
                    elif action in ('refresh','whatsapp'):
                        if action=='whatsapp': self.admin()
                        p=ops.access(c,uid,d.get('number'),team)
                    else: raise ValueError('Acción desconocida')
                if action=='whatsapp':
                    operator_reply(p,d.get('text'));result={'ok':True}
                if action=='refresh':
                    try: ops.sample(p,force=True);result={'ok':True}
                    except Exception: return self.out({'error':'No se obtuvo clima vigente. Revisa la conexión al proveedor.'},503)
                ops.publish(p['id'])
                return self.out(result)
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                if self.path=='/api/channel':
                    reply=respond(c,None,{'type':'text','text':{'body':clean(d.get('text'),800)}},uid)
                    return self.out({'reply':reply})
                if self.path=='/api/simulate':
                    scene=choice(d.get('scene'),SCENES); crop=choice(d.get('crop'),CROPS); stage=choice(d.get('stage'),STAGES)
                    return self.out({'risks':risks(forecast('Viacha','demo',scene)['days'],crop,stage)})
                if self.path=='/api/profile': update_profile(c,uid,d)
                elif self.path=='/api/market': mutate(c,profile(c,uid),d)
                elif self.path=='/api/chat': ask(c,profile(c,uid),d.get('q'))
                elif self.path=='/api/feedback':
                    if type(d.get('occurred'))!=bool or type(d.get('useful'))!=bool: raise ValueError('Completa ambas respuestas')
                    if not c.execute('UPDATE alerts SET occurred=?,useful=? WHERE id=? AND user=?',(d['occurred'],d['useful'],d.get('id'),uid)).rowcount: raise ValueError('Alerta desconocida')
                elif self.path.startswith('/api/admin/'):
                    self.admin()
                    if self.path.endswith('/doc'):
                        values=(clean(d.get('title'),80),choice(d.get('crop'),['Todos']+CROPS),clean(d.get('tags'),200),clean(d.get('body'),1200),clean(d.get('source'),200))
                        if d.get('id'): c.execute('UPDATE knowledge SET title=?,crop=?,tags=?,body=?,source=? WHERE id=?',values+(d['id'],))
                        else: c.execute('INSERT INTO knowledge(title,crop,tags,body,source) VALUES(?,?,?,?,?)',values)
                    elif self.path.endswith('/plan'):
                        plan=choice(d.get('plan'),PLANS)
                        if plan=='Asociación' and c.execute("SELECT COUNT(*) FROM users WHERE plan='Asociación' AND rowid<>?",(d['number'],)).fetchone()[0]>=50: raise ValueError('El grupo piloto alcanzó 50 socios.')
                        c.execute('UPDATE users SET plan=? WHERE rowid=?',(plan,d['number']))
                    elif self.path.endswith('/case'): c.execute('UPDATE cases SET status=? WHERE id=?',(choice(d.get('status'),['Pendiente','Revisado']),d.get('id')))
                    else: raise ValueError('Acción desconocida')
                elif self.path=='/api/delete':
                    c.execute('DELETE FROM users WHERE id=?',(uid,))
                else: return self.out({'error':'Ruta desconocida'},404)
            self.out({'ok':True})
        except PermissionError as e: self.out({'error':str(e)},403)
        except (ValueError,KeyError,TypeError) as e: self.out({'error':str(e)},400)
        except Exception: logging.exception('Error de operación'); self.out({'error':'Operación pendiente. Vuelve a intentar.'},503)

def main():
    global ADMIN
    env=ROOT/'.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k,v=line.split('=',1); os.environ.setdefault(k.strip(),v.strip())
    global PUBLIC
    PUBLIC=os.getenv('YAPU_HTTPS','')=='1'
    ADMIN=os.getenv('YAPU_ADMIN_KEY') or ADMIN
    parser=argparse.ArgumentParser(); parser.add_argument('--abrir',action='store_true'); args=parser.parse_args()
    init(); host=os.getenv('YAPU_HOST','127.0.0.1'); port=int(os.getenv('PORT','8765'))
    server=ThreadingHTTPServer((host,port),Handler)
    print(f'Yapu IA en puerto {port}', flush=True)
    if host in ('localhost', '127.0.0.1') and not PUBLIC:
        print(f'Clave del equipo: {ADMIN}', flush=True)
    threading.Thread(target=scheduler,daemon=True).start()
    if args.abrir: webbrowser.open(f'http://localhost:{port}')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
if __name__=='__main__': main()
