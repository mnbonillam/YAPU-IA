"""Catastro, historial meteorológico y ensayos del espacio de trabajo."""
import copy
import datetime as dt
import json
import re
from pathlib import Path
from agro import now,TZ,risks,ZONES,CROPS,STAGES
from core import rows,create_user,update_profile,profile,clean,choice,evaluate
import operaciones as ops

def install(c):
    import productor_chat
    productor_chat.install(c)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS enlaces(parcela TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,clave TEXT UNIQUE,vence TEXT,receptor TEXT REFERENCES users(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS atlas_spaces(owner TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS productores(id INTEGER PRIMARY KEY,owner TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,nombre TEXT NOT NULL,telefono TEXT NOT NULL DEFAULT '',comunidad TEXT NOT NULL,notas TEXT NOT NULL DEFAULT '',activo INTEGER DEFAULT 1,ejemplo INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS parcelas(user TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,productor INTEGER NOT NULL REFERENCES productores(id),area REAL CHECK(area>0),altitud REAL,caracteristicas TEXT DEFAULT '',activo INTEGER DEFAULT 1,ejemplo INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS registros_clima(user TEXT REFERENCES users(id) ON DELETE CASCADE,hora TEXT,fuente TEXT,temp REAL,hum REAL,lluvia REAL,viento REAL,direccion REAL,PRIMARY KEY(user,hora,fuente));
    CREATE TABLE IF NOT EXISTS evaluaciones(user TEXT REFERENCES users(id) ON DELETE CASCADE,hora TEXT,contexto TEXT,resultado TEXT,PRIMARY KEY(user,hora,contexto));
    CREATE TABLE IF NOT EXISTS auditoria(id INTEGER PRIMARY KEY,owner TEXT REFERENCES users(id) ON DELETE CASCADE,productor INTEGER,accion TEXT,fecha TEXT);
    CREATE TABLE IF NOT EXISTS envios_prueba(ensayo INTEGER PRIMARY KEY REFERENCES ensayos(id) ON DELETE CASCADE,destinatario TEXT NOT NULL,recibido TEXT NOT NULL,acuse TEXT);
    CREATE TABLE IF NOT EXISTS envios_fallidos(alerta INTEGER PRIMARY KEY REFERENCES alerts(id) ON DELETE CASCADE,intentos INTEGER NOT NULL,estado TEXT NOT NULL,fecha TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS ensayos(id INTEGER PRIMARY KEY,owner TEXT REFERENCES users(id) ON DELETE CASCADE,parcela TEXT,escenario TEXT,resultado TEXT,fecha TEXT);
    """)
def audit(c,uid,producer,text):
    c.execute('INSERT INTO auditoria(owner,productor,accion,fecha) VALUES(?,?,?,?)',(uid,producer,text,now().isoformat(timespec='seconds')))
def level(kind): return 'Medio' if kind in ('Déficit de lluvia','Cambio brusco','Aire seco') else 'Alto'
def readings(c,p,w):
    cur=w.get('current') or {}
    if not cur or not w.get('valid'):return
    c.execute('INSERT OR REPLACE INTO registros_clima VALUES(?,?,?,?,?,?,?,?)',(p['id'],w['valid'],w['source'],cur['temperature_2m'],cur.get('relative_humidity_2m'),cur.get('precipitation'),cur.get('wind_speed_10m'),cur.get('wind_direction_10m')))
    risk=risks(w['days'],p['crop'],p['stage'],cur)
    c.execute('INSERT OR REPLACE INTO evaluaciones VALUES(?,?,?,?)',(p['id'],w['valid'],p['crop']+' · '+p['stage'],json.dumps(risk,ensure_ascii=False)))
def plant(c,uid,pr,d,example=0):
    owner=c.execute('SELECT id,ejemplo FROM productores WHERE id=? AND owner=? AND activo=1',(pr,uid)).fetchone()
    if not owner:raise ValueError('Selecciona un productor activo de este espacio.')
    if owner['ejemplo'] and not example:raise ValueError('Registra al productor responsable antes de añadir su parcela.')
    if d.get('number'):
        p=ops.access(c,uid,d['number'],False);target=p['id']
    else:
        target=create_user(c);c.execute('UPDATE users SET owner=? WHERE id=?',(uid,target))
    area=None if example and d.get('area') is None else ops.coordinate(d.get('area'),1000000)
    if area is not None and area<=0:raise ValueError('El área debe ser mayor que cero.')
    alt=d.get('altitud');alt=ops.coordinate(alt,9000) if alt not in ('',None) else None
    update_profile(c,target,{**d,'mode':'live','scene':'Estable','consent':d.get('consent') is True,'lat':ops.coordinate(d.get('lat'),90),'lon':ops.coordinate(d.get('lon'),180)})
    c.execute("""INSERT INTO parcelas(user,productor,area,altitud,caracteristicas,ejemplo) VALUES(?,?,?,?,?,?) ON CONFLICT(user) DO UPDATE SET productor=excluded.productor,area=excluded.area,altitud=excluded.altitud,caracteristicas=excluded.caracteristicas""",(target,pr,area,alt,str(d.get('caracteristicas',''))[:500],example))
    audit(c,uid,pr,('Actualización' if d.get('number') else 'Registro')+' de parcela · '+d['name'])
    return profile(c,target)
def seed(c,uid):
    if not c.execute('INSERT OR IGNORE INTO atlas_spaces VALUES(?)',(uid,)).rowcount:return
    catalog=json.loads((Path(__file__).parent/'catalogo/clima.json').read_text(encoding='utf-8'))
    records=json.loads((Path(__file__).parent/'catalogo/predios.json').read_text(encoding='utf-8'))
    institutions={}
    for item,record in zip(catalog,records):
        if (record['site'],record['lat'],record['lon'])!=(item['site'],item['lat'],item['lon']):raise ValueError('Catálogo y captura incompatibles.')
        nombre=record['institution']
        if nombre not in institutions:
            institutions[nombre]=c.execute("INSERT INTO productores(owner,nombre,comunidad,notas,ejemplo) VALUES(?,?,?,'Entidad documentada públicamente. La precarga es una referencia académica y no acredita alta en Yapu.',1)",(uid,nombre,'Bolivia')).lastrowid
        pr=institutions[nombre]
        data=item['response'];o=data['current'];daily=data['daily'];hourly=data['hourly']
        p=plant(c,uid,pr,dict(name=record['name'],area=record['area'],crop=record['crop'],stage='Sin verificar',zone=item['site'],lat=item['lat'],lon=item['lon'],altitud=record['alt'],caracteristicas=record['note'],consent=True),1)
        valid=o['time']+'-04:00';source='Open-Meteo · modelo meteorológico'
        keys=['temperature_2m_min','temperature_2m_max','precipitation_sum','wind_gusts_10m_max','weather_code','precipitation_probability_max']
        days=[dict(date=t,**{k:daily[v][i] for k,v in zip(('low','high','rain','gust','code','prob'),keys)}) for i,t in enumerate(daily['time']) if t>=valid[:10]]
        w=dict(days=days,current=o,valid=valid,stamp=item['retrieved'],source=source,mode='live')
        c.execute('INSERT INTO meteo(user,data,checked) VALUES(?,?,?)',(p['id'],json.dumps(w),w['stamp']))
        fields=['temperature_2m','relative_humidity_2m','precipitation','wind_speed_10m','wind_direction_10m']
        c.executemany('INSERT OR IGNORE INTO registros_clima VALUES(?,?,?,?,?,?,?,?)',[(p['id'],t+'-04:00',source,*[hourly[k][i] for k in fields]) for i,t in enumerate(hourly['time']) if t<=o['time']])
        for i,date in enumerate(daily['time']):
            if date>=valid[:10]: break
            day=dict(date=date,**{k:daily[v][i] for k,v in zip(('low','high','rain','gust','code','prob'),keys)})
            retrospective=risks([day],p['crop'],p['stage'])
            c.execute('INSERT OR IGNORE INTO evaluaciones VALUES(?,?,?,?)',(p['id'],date+'T23:59-04:00','Retrospectiva diaria · '+p['crop'],json.dumps(retrospective,ensure_ascii=False)))
        readings(c,p,w);evaluate(c,p,w)
        audit(c,uid,pr,'Serie meteorológica importada · '+item['site'])
def producer(c,uid,d):
    pid=d.get('id')
    if pid and not c.execute('SELECT 1 FROM productores WHERE owner=? AND id=?',(uid,pid)).fetchone():raise ValueError('Productor desconocido.')
    phone=str(d.get('telefono','')).strip()
    if phone and not re.fullmatch(r'[+\d ()-]{6,25}',phone):raise ValueError('Revisa el teléfono.')
    vals=(clean(d.get('nombre'),100),phone,clean(d.get('comunidad'),100),str(d.get('notas',''))[:500])
    if pid:c.execute('UPDATE productores SET nombre=?,telefono=?,comunidad=?,notas=? WHERE id=?',vals+(pid,))
    else:pid=c.execute('INSERT INTO productores(nombre,telefono,comunidad,notas,owner) VALUES(?,?,?,?,?)',vals+(uid,)).lastrowid
    audit(c,uid,pid,'Ficha de productor guardada · '+vals[0]);return {'id':pid}
def deactivate(c,uid,d):
    if d.get('id'):
        pid=d['id']
        if not c.execute('UPDATE productores SET activo=0 WHERE owner=? AND id=?',(uid,pid)).rowcount:raise ValueError('Productor desconocido.')
        targets=rows(c,'SELECT user FROM parcelas WHERE productor=?',(pid,))
    else:
        p=ops.access(c,uid,d.get('number'),False);targets=[{'user':p['id']}]
        row=c.execute('SELECT productor FROM parcelas WHERE user=?',(p['id'],)).fetchone();pid=row[0] if row else None
    for t in targets:
        c.execute('UPDATE parcelas SET activo=0 WHERE user=?',(t['user'],))
        c.execute('UPDATE users SET consent=0 WHERE id=?',(t['user'],))
        c.execute('UPDATE alerts SET active=0 WHERE user=?',(t['user'],))
    audit(c,uid,pid,'Desactivación · '+str(len(targets))+' parcela(s) fuera del monitoreo')
def dashboard(c,uid):
    data=ops.board(c,uid,False)
    records=rows(c,'SELECT u.rowid AS number,p.* FROM parcelas p JOIN users u ON u.id=p.user JOIN productores pr ON pr.id=p.productor WHERE pr.owner=?',(uid,))
    meta={p['number']:p for p in records}
    for p in data['parcels']:
        m=meta.get(p['number'],{});p.update({k:m.get(k) for k in ('productor','area','altitud','ejemplo','caracteristicas')})
    data['archived']=rows(c,"SELECT u.rowid AS number,u.name,u.zone,p.area,p.productor FROM parcelas p JOIN users u ON u.id=p.user JOIN productores pr ON pr.id=p.productor WHERE pr.owner=? AND p.activo=0 ORDER BY u.rowid",(uid,))
    data.update(producers=rows(c,'SELECT id,nombre,telefono,comunidad,notas,activo,ejemplo FROM productores WHERE owner=? ORDER BY id',(uid,)),audit=rows(c,'SELECT productor,accion,fecha FROM auditoria WHERE owner=? ORDER BY id DESC LIMIT 120',(uid,)),runs=rows(c,'SELECT id,parcela,escenario,fecha FROM ensayos WHERE owner=? ORDER BY id DESC LIMIT 30',(uid,)),catalog=json.loads((Path(__file__).parent/'catalogo/predios.json').read_text(encoding='utf-8')),zones=ZONES,crops=CROPS,stages=STAGES)
    return data
def detail(c,uid,n):
    p=c.execute("SELECT id FROM users WHERE rowid=? AND (id=? OR owner=?)",(n,uid,uid)).fetchone()
    if not p:raise ValueError('Parcela desconocida.')
    params=(p['id'],)
    return dict(failures=rows(c,'SELECT f.* FROM envios_fallidos f JOIN alerts a ON a.id=f.alerta WHERE a.user=? ORDER BY f.fecha DESC',params),history=rows(c,'SELECT hora,fuente,temp,hum,lluvia,viento,direccion FROM registros_clima WHERE user=? ORDER BY hora DESC LIMIT 192',params),evaluations=rows(c,'SELECT hora,contexto,resultado FROM evaluaciones WHERE user=? ORDER BY hora DESC LIMIT 30',params),alerts=rows(c,"SELECT id,kind,day,evidence,action,stamp,ack,source,CASE WHEN ack IS NOT NULL THEN 'Atendida' WHEN active=0 OR day<? THEN 'Vencida' ELSE 'Activa' END AS estado FROM alerts WHERE user=? ORDER BY day DESC LIMIT 100",(str(now().date()),p['id'])),notifications=rows(c,"SELECT t.body,t.stamp,t.channel,r.status FROM timeline t LEFT JOIN receipts r ON r.external=t.external WHERE t.user=? AND t.direction='Alerta' ORDER BY t.id DESC LIMIT 50",params))
SCENARIOS=['Helada','Lluvia intensa','Déficit de lluvia','Calor extremo','Aire seco','Viento fuerte']
def simulate(c,uid,d):
    p=ops.access(c,uid,d.get('number'),False)
    rec=c.execute('SELECT data FROM meteo WHERE user=?',(p['id'],)).fetchone()
    if not rec or not rec[0]:raise ValueError('Actualiza el clima de esta parcela primero.')
    w=json.loads(rec[0]);scene=choice(d.get('scene'),SCENARIOS);factor=float(d.get('factor',1))
    if not 0.25<=factor<=2:raise ValueError('Intensidad fuera de rango.')
    days=copy.deepcopy(w['days']);cur=w['current'].copy()
    for day in days:
        if scene=='Helada':day['low']-=round(12*factor,1)
        elif scene=='Calor extremo':day['high']+=round(22*factor,1)
        elif scene=='Lluvia intensa':day['rain']+=round(40*factor,1)
        elif scene=='Déficit de lluvia':day['rain']=round(day['rain']*max(0,1-factor),1)
        elif scene=='Viento fuerte':day['gust']+=round(55*factor,1)
    if scene=='Aire seco':cur['relative_humidity_2m']=max(1,round(cur['relative_humidity_2m']-65*factor))
    before=risks(w['days'],p['crop'],p['stage'],w['current']);after=risks(days,p['crop'],p['stage'],cur)
    hit=next((r for r in after if r['kind']==scene),None)
    msg=(f"SIMULACIÓN · {scene}\n📍 {p['name']} · {p['crop']}\n\nQué se espera\n{hit['evidence']}\n\nQué puedes hacer\n{hit['action']}" if hit else 'Ningún aviso de este fenómeno alcanza el umbral a esta intensidad.')
    result=dict(scene=scene,factor=factor,before=before,after=after,source=w['source'],valid=w['valid'],baseline=w['days'][0],scenario=days[0],humidity=[w['current']['relative_humidity_2m'],cur['relative_humidity_2m']],notice=msg,level=level(scene) if hit else 'Bajo')
    stamp=now().isoformat(timespec='seconds')
    result['id']=c.execute('INSERT INTO ensayos(owner,parcela,escenario,resultado,fecha) VALUES(?,?,?,?,?)',(uid,p['name'],scene,json.dumps(result,ensure_ascii=False),stamp)).lastrowid
    recipient=c.execute('SELECT pr.nombre FROM productores pr JOIN parcelas l ON l.productor=pr.id WHERE l.user=?',(p['id'],)).fetchone()
    if hit:
        name=recipient[0] if recipient else p['name']
        c.execute('INSERT INTO envios_prueba(ensayo,destinatario,recibido) VALUES(?,?,?)',(result['id'],name,stamp))
        result['delivery']={'destinatario':name,'recibido':stamp,'acuse':None}
    audit(c,uid,None,'Ensayo '+scene+' · '+p['name']);return result

def link_code(c,uid,d):
    import secrets,hashlib
    p=ops.access(c,uid,d.get('number'),False)
    if c.execute('SELECT ejemplo FROM parcelas WHERE user=?',(p['id'],)).fetchone()[0]:raise ValueError('Usa una parcela registrada por ti para vincular WhatsApp.')
    code=secrets.token_hex(6).upper()
    c.execute('INSERT INTO enlaces(parcela,clave,vence) VALUES(?,?,?) ON CONFLICT(parcela) DO UPDATE SET clave=excluded.clave,vence=excluded.vence',(p['id'],hashlib.sha256(code.encode()).hexdigest(),(now()+dt.timedelta(minutes=15)).isoformat()))
    return {'code':code}
