"""Parcelas y telemetría persistentes. Los identificadores de sesión nunca salen en el panel."""
import json
import math
import os
import datetime as dt
from agro import now,TZ,ZONES,forecast
from core import db,rows,profile,create_user,update_profile,evaluate,ctx,clean

def install(c):
    for table,columns in {'users':{'last_inbound':'INTEGER','lat':'REAL','lon':'REAL','owner':'TEXT REFERENCES users(id) ON DELETE CASCADE'},'alerts':{'ack':'TEXT','active':'INTEGER DEFAULT 0'}}.items():
        existing={r[1] for r in c.execute('PRAGMA table_info('+table+')')}
        for key,definition in columns.items():
            if key not in existing: c.execute(f'ALTER TABLE {table} ADD COLUMN {key} {definition}')
    c.executescript("""
    CREATE TABLE IF NOT EXISTS channel_trials(owner TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,trial TEXT UNIQUE REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS meteo(user TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,data TEXT,error TEXT,checked TEXT);
    CREATE TABLE IF NOT EXISTS timeline(id INTEGER PRIMARY KEY,user TEXT REFERENCES users(id) ON DELETE CASCADE,channel TEXT,direction TEXT,body TEXT,stamp TEXT,external TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS receipts(external TEXT PRIMARY KEY,status TEXT,stamp INTEGER,detail TEXT);
    CREATE INDEX IF NOT EXISTS tl_user ON timeline(user,id);
    """)

def coordinate(raw,limit):
    if raw is None or raw=='' or isinstance(raw,bool): raise ValueError('Completa ambas coordenadas.')
    v=float(raw)
    if not math.isfinite(v) or abs(v)>limit: raise ValueError('Coordenada fuera de rango.')
    return round(v,6)
def coords(p):
    return (p['lat'],p['lon']) if p['lat'] is not None and p['lon'] is not None else ZONES[p['zone']]
def access(c,uid,number,team):
    r=c.execute("SELECT * FROM users WHERE rowid=? AND consent=1 AND mode='live' AND (? OR id=? OR owner=?)",(number,team,uid,uid)).fetchone()
    if not r: raise ValueError('Parcela no disponible.')
    return dict(r)
def save(c,uid,d,team):
    if d.get('number'): target=access(c,uid,d['number'],team)['id']
    elif not profile(c,uid)['consent']: target=uid
    else:
        target=create_user(c);c.execute('UPDATE users SET owner=? WHERE id=?',(uid,target))
    lat,lon=coordinate(d.get('lat'),90),coordinate(d.get('lon'),180)
    update_profile(c,target,{**d,'mode':'live','scene':'Estable','lat':lat,'lon':lon})
    return c.execute('SELECT rowid FROM users WHERE id=?',(target,)).fetchone()[0]

def sample(p,force=False):
    try: w=forecast(p['zone'],'live','Estable',coords(p),force=force)
    except Exception:
        with db() as c:
            if c.execute('SELECT 1 FROM users WHERE id=?',(p['id'],)).fetchone():
                c.execute("""INSERT INTO meteo(user,error,checked) VALUES(?,?,?) ON CONFLICT(user) DO UPDATE SET error=excluded.error,checked=excluded.checked""",(p['id'],'Sin actualización del proveedor',now().isoformat(timespec='seconds')))
        raise
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        latest=profile(c,p['id'])
        if coords(latest)!=coords(p) or ctx(latest)!=ctx(p): raise ValueError('La parcela cambió; actualiza de nuevo.')
        evaluate(c,p,w)
        from atlas import readings
        readings(c,p,w)
        c.execute("""INSERT INTO meteo(user,data,checked) VALUES(?,?,?) ON CONFLICT(user) DO UPDATE SET data=excluded.data,error=NULL,checked=excluded.checked""",(p['id'],json.dumps(w),w['stamp']))
    return w

def board(c,uid,team):
    parcels=rows(c,"""SELECT u.rowid AS number,u.name,u.crop,u.stage,u.zone,u.lat,u.lon,u.phone IS NOT NULL AS wa,u.last_inbound,m.data,m.checked,m.error
    FROM users u LEFT JOIN meteo m ON m.user=u.id WHERE u.consent=1 AND u.mode='live' AND (? OR u.id=? OR u.owner=?) ORDER BY u.rowid""",(team,uid,uid))
    for p in parcels:
        p['located']=p['lat'] is not None
        p['lat'],p['lon']=coords(p)
        data=p.pop('data');p['weather']=json.loads(data) if data else None
        if p['weather'] and (now()-dt.datetime.fromisoformat(p['weather']['valid'])).total_seconds()>7200:
            p['error']='Último dato fuera de vigencia'
    alerts=rows(c,"""SELECT a.id,u.rowid AS number,u.name,a.kind,a.ctx,a.day,a.evidence,a.action,a.source,a.stamp,a.ack,a.active
    FROM alerts a JOIN users u ON u.id=a.user WHERE u.consent=1 AND u.mode='live' AND a.source LIKE 'Open-Meteo%' AND a.active=1 AND a.day>=? AND (? OR u.id=? OR u.owner=?) ORDER BY a.day,a.id""",(str(now().date()),team,uid,uid))
    for a in alerts: a['level']='Medio' if a['kind'] in ('Déficit de lluvia','Cambio brusco','Aire seco') else 'Alto'
    messages=rows(c,"""SELECT t.id,u.rowid AS number,t.channel,t.direction,t.body,t.stamp,r.status,r.detail
    FROM timeline t JOIN users u ON u.id=t.user LEFT JOIN receipts r ON r.external=t.external
    WHERE u.consent=1 AND u.mode='live' AND (? OR u.id=? OR u.owner=?) ORDER BY t.id DESC LIMIT 150""",(team,uid,uid))
    return dict(parcels=parcels,alerts=alerts,messages=messages,team=team,whatsapp=all(os.getenv(k) for k in ('WA_TOKEN','WA_PHONE_ID','WA_GRAPH_VERSION','WA_APP_SECRET','WA_VERIFY_TOKEN')),template=bool(os.getenv('WA_ALERT_TEMPLATE')))

def acknowledge(c,uid,d,team):
    p=access(c,uid,d.get('number'),team)
    if not c.execute("UPDATE alerts SET ack=COALESCE(ack,?) WHERE id=? AND user=? AND active=1 AND source LIKE 'Open-Meteo%' AND day>=?",(now().isoformat(timespec='seconds'),d.get('alert'),p['id'],str(now().date()))).rowcount: raise ValueError('Aviso no disponible.')
def log_message(c,user,channel,direction,body,external=None):
    c.execute('INSERT OR IGNORE INTO timeline(user,channel,direction,body,stamp,external) VALUES(?,?,?,?,?,?)',(user,channel,direction,body,now().isoformat(timespec='seconds'),external))
def receipt(c,mid,status,stamp,detail=''):
    if status not in ('accepted','sent','delivered','read','failed'): return
    old=c.execute('SELECT status,stamp FROM receipts WHERE external=?',(mid,)).fetchone()
    order={'accepted':0,'sent':1,'failed':2,'delivered':3,'read':4}
    if old and order[old['status']]>=order[status]: return
    c.execute('INSERT OR REPLACE INTO receipts VALUES(?,?,?,?)',(mid,status,int(stamp),detail))

# Despierta a los paneles que esperan cambios de su parcela o del equipo.
import threading
import time
_changed=threading.Condition()
_versions={}
_team_version=0
def revision(uid,team):
    with _changed: return _team_version if team else _versions.get(uid,0)
def publish(user):
    global _team_version
    with db() as c:
        row=c.execute('SELECT owner FROM users WHERE id=?',(user,)).fetchone()
    with _changed:
        _team_version+=1
        for key in {user,row['owner'] if row else None}-{None}: _versions[key]=_team_version
        _changed.notify_all()
def await_change(uid,team,seen):
    with _changed:
        _changed.wait_for(lambda:revision(uid,team)!=seen,timeout=18)
        return revision(uid,team)
