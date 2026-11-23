import contextlib
import json
import os
import secrets
import sqlite3
from pathlib import Path
from agro import *

ROOT=Path(__file__).resolve().parent
DATA=Path(os.getenv("YAPU_DATA",str(ROOT/"datos")))
@contextlib.contextmanager
def db():
    con=sqlite3.connect(DATA/"yapu.sqlite",timeout=25)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        with con: yield con
    finally: con.close()
def init():
    global DATA
    DATA=Path(os.environ['YAPU_DATA']) if os.getenv('YAPU_DATA') else DATA
    DATA.mkdir(parents=True,exist_ok=True)
    with db() as c:
        c.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT, zone TEXT, crop TEXT, stage TEXT, mode TEXT, scene TEXT, plan TEXT DEFAULT 'Gratuito', phone TEXT UNIQUE, consent INTEGER DEFAULT 0, joined TEXT);
        CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY,user TEXT REFERENCES users(id) ON DELETE CASCADE,q TEXT,a TEXT,stamp TEXT);
        CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY,user TEXT REFERENCES users(id) ON DELETE CASCADE,ctx TEXT,kind TEXT,day TEXT,evidence TEXT,action TEXT,source TEXT,stamp TEXT,occurred INTEGER,useful INTEGER,sent INTEGER DEFAULT 0, UNIQUE(user,ctx,kind,day));
        CREATE TABLE IF NOT EXISTS knowledge(id INTEGER PRIMARY KEY,title TEXT,crop TEXT,tags TEXT,body TEXT,source TEXT);
        CREATE TABLE IF NOT EXISTS cases(id INTEGER PRIMARY KEY,user TEXT REFERENCES users(id) ON DELETE CASCADE,question TEXT,stamp TEXT,status TEXT DEFAULT 'Pendiente');
        CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY,phone TEXT,reply TEXT,done INTEGER DEFAULT 0);
        """)
        from mercado import install
        install(c)
        from operaciones import install as install_operations
        install_operations(c)
        import atlas
        atlas.install(c)
        if not c.execute('SELECT 1 FROM knowledge').fetchone():
            c.executemany('INSERT INTO knowledge(title,crop,tags,body,source) VALUES(?,?,?,?,"Ficha piloto NEXTECH")',BASE)
            c.execute("UPDATE knowledge SET source=? WHERE title='Papa en floración'",("FAO · Potato and water (i1127e02), adaptación NEXTECH · 2026-11",))
def rows(c,sql,params=()): return [dict(r) for r in c.execute(sql,params)]
def profile(c,uid):
    r=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    if not r: raise ValueError("Perfil no disponible")
    return dict(r)
def create_user(c,phone=None):
    uid=secrets.token_urlsafe(32)
    c.execute("INSERT INTO users(id,name,zone,crop,stage,mode,scene,phone,joined) VALUES(?,?,?,?,?,?,?,?,?)",(uid,"Mi parcela","Viacha","Papa","Floración","live","Helada",phone,now().isoformat()))
    return uid
def ctx(p):
    location=(f"{p['zone']} ({p['lat']:.5f}, {p['lon']:.5f})" if p.get('lat') is not None else p['zone'])
    return ' · '.join([location,p['crop'],p['stage'],p['scene'] if p['mode']=='demo' else 'En línea'])
def evaluate(c,p,w):
    alerts=risks(w['days'],p['crop'],p['stage'],w.get('current'))
    if w['mode']=='live': c.execute('UPDATE alerts SET active=0 WHERE user=? AND active=1',(p['id'],))
    for r in alerts:
        c.execute("""INSERT INTO alerts(user,ctx,kind,day,evidence,action,source,stamp,active)
        VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(user,ctx,kind,day) DO UPDATE SET
        evidence=excluded.evidence,action=excluded.action,source=excluded.source,stamp=excluded.stamp,active=excluded.active""",(p['id'],ctx(p),r['kind'],r['date'],r['evidence'],r['action'],w['source'],w['stamp'],int(w['mode']=='live')))
        if w['mode']=='live':
            aid=c.execute('SELECT id FROM alerts WHERE user=? AND ctx=? AND kind=? AND day=?',(p['id'],ctx(p),r['kind'],r['date'])).fetchone()[0]
            c.execute("INSERT OR IGNORE INTO timeline(user,channel,direction,body,stamp,external) VALUES(?,'Panel','Alerta',?,?,?)",(p['id'],f"{r['kind']} · {p['name']} · {r['date']}. {r['evidence']}. {r['action']}",w['stamp'],'panel-alert-'+str(aid)))
    return alerts
def weather(p):
    from operaciones import coords
    return forecast(p['zone'],p['mode'],p['scene'],coords(p))
def state(uid):
    with db() as c: p=profile(c,uid)
    try: w=weather(p) if p['consent'] else None; err=None if w else 'Registra tu parcela para consultar el clima.'
    except Exception: w=None; err='El proveedor meteorológico no respondió con datos completos. Reintenta o selecciona el modo demostración.'
    from mercado import listing
    with db() as c:
        active=risks(w['days'],p['crop'],p['stage']) if w else []
        if w and p['mode']=='demo': evaluate(c,p,w)
        history=rows(c,"SELECT id,ctx,kind,day,evidence,action,source,stamp,occurred,useful FROM alerts WHERE user=? ORDER BY id DESC LIMIT 250",(uid,))
        return dict(market=listing(c,uid),profile={k:p[k] for k in ('name','zone','crop','stage','mode','scene','plan','consent','lat','lon')},weather=w,error=err,risks=active,alerts=history,chat=rows(c,'SELECT q,a,stamp FROM (SELECT * FROM chats WHERE user=? ORDER BY id DESC LIMIT 30) ORDER BY id',(uid,)),cases=rows(c,'SELECT id,question,stamp,status FROM cases WHERE user=? ORDER BY id DESC LIMIT 30',(uid,)),ctx=ctx(p),zones=list(ZONES),crops=CROPS,stages=STAGES,scenes=SCENES,plans=PLANS,used=c.execute('SELECT COUNT(*) FROM chats WHERE user=? AND substr(stamp,1,10)=?',(uid,str(now().date()))).fetchone()[0])
def clean(value,n=1000):
    if not isinstance(value,str) or not value.strip() or len(value.strip())>n: raise ValueError(f"Ingresa texto de 1 a {n} caracteres.")
    return value.strip()
def choice(value,options):
    if value not in options: raise ValueError("Opción inválida")
    return value
def update_profile(c,uid,d):
    name=clean(d.get('name'),60)
    zone,crop,stage,mode,scene=[choice(d.get(k),opts) for k,opts in [('zone',ZONES),('crop',CROPS),('stage',STAGES),('mode',['demo','live']),('scene',SCENES)]]
    if d.get('consent') is not True: raise ValueError('Confirma el consentimiento para guardar tu parcela.')
    from operaciones import coordinate
    old=profile(c,uid)
    lat,lon=(old['lat'],old['lon']) if old['zone']==zone else (None,None)
    if 'lat' in d or 'lon' in d:
        if d.get('lat') is not None or d.get('lon') is not None: lat,lon=coordinate(d.get('lat'),90),coordinate(d.get('lon'),180)
    if (lat,lon,zone,crop,stage,mode)!=(old['lat'],old['lon'],old['zone'],old['crop'],old['stage'],old['mode']):
        c.execute('DELETE FROM meteo WHERE user=?',(uid,))
        c.execute('UPDATE alerts SET active=0 WHERE user=?',(uid,))
    c.execute('UPDATE users SET lat=?,lon=? WHERE id=?',(lat,lon,uid))
    c.execute("UPDATE users SET name=?,zone=?,crop=?,stage=?,mode=?,scene=?,consent=1 WHERE id=?",(name,zone,crop,stage,mode,scene,uid))

def request_json(url,payload,headers):
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json',**headers})
    with urllib.request.urlopen(req,timeout=15) as r: return json.load(r)

def ask(c,p,q):
    q=clean(q,800); stamp=now().isoformat(timespec="seconds")
    count=c.execute("SELECT COUNT(*) FROM chats WHERE user=? AND substr(stamp,1,10)=?",(p['id'],stamp[:10])).fetchone()[0]
    if count>=PLANS[p['plan']]: raise ValueError("Alcanzaste el límite diario del plan. Se renueva a medianoche de Bolivia.")
    docs=retrieve(q,rows(c,"SELECT * FROM knowledge WHERE crop IN ('Todos',?)",(p['crop'],)))
    risky=any(w in norm(q) for w in ('dosis','veneno','pesticid','plaguicid','fungicid','insecticid','fumig','intox','diagnos','enferm','mancha','quimic','herbicid'))
    meteo=any(w in norm(q) for w in ('clima','pronostic','temperatura','alerta','frio','helada','granizo','lluv','viento','riesgo','sequia','manana','semana'))
    if risky or (not docs and not meteo):
        cid=c.execute('INSERT INTO cases(user,question,stamp) VALUES(?,?,?)',(p['id'],q,stamp)).lastrowid
        msg=f"Faltan datos para orientar esta decisión con confianza. Registré el caso #{cid} para revisión del equipo. Consulta con un técnico de tu zona y lleva fotos, la etapa del cultivo y la fecha de aparición. No se ha contactado automáticamente a un técnico."
        src='Protocolo de revisión NEXTECH'
    else:
        src=', '.join(dict.fromkeys(d['source']+' / '+d['title'] for d in docs))
        parts=[]
        if meteo:
            try:
                w=weather(p); rr=risks(w['days'],p['crop'],p['stage'])
                target=next((x for x in SCENES if norm(x) in norm(q)),None)
                if 'frio' in norm(q): target='Helada'
                if 'sequia' in norm(q): target='Déficit de lluvia'
                which=1 if 'manana' in norm(q) else 0 if 'hoy' in norm(q) else None
                if which is not None:
                    period=w['days'][which]
                    rr=[r for r in rr if r['date']==period['date']]
                    parts.append(f"Para el {period['date']}: mínima {period['low']} °C, máxima {period['high']} °C y lluvia {period['rain']} mm.")
                if target: rr=[r for r in rr if r['kind']==target]
                if rr:
                    r=rr[0]; parts.append(f"{r['kind']} el {r['date']}. {r['evidence']}. {r['action']}")
                else: parts.append("Las reglas del piloto no detectan el riesgo consultado en el periodo consultado.")
                src=(w['source']+' ('+w['stamp']+')'+(' · '+src if src else ''))
            except Exception: parts.append("No se pudo consultar el pronóstico. Reintenta antes de decidir."); src=src or 'Consulta meteorológica sin datos'
        if docs: parts.append(docs[0]['body'])
        msg=' '.join(parts)
        if os.getenv('OPENAI_API_KEY') and p['consent']:
            try:
                result=request_json('https://api.openai.com/v1/chat/completions',dict(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),messages=[dict(role='system',content='Reformula el material en español sencillo, máximo 65 palabras. Conserva fecha, cifras, incertidumbre y acciones. No agregues diagnósticos, dosis ni información.'),dict(role='user',content=msg)]),{'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']})
                paraphrase=result['choices'][0]['message']['content'].strip()
                if paraphrase: msg=paraphrase+'\nDatos y orientación de referencia: '+' '.join(parts)
            except Exception: pass
    a=f"{p['crop']} · {p['stage']} · {p['zone']}\n{msg}\nFuente: {src}. Consulta: {stamp[:10]}. Orientación piloto; las condiciones de tu parcela pueden variar."
    c.execute('INSERT INTO chats(user,q,a,stamp) VALUES(?,?,?,?)',(p['id'],q,a,stamp))
    return a
