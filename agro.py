"""Conocimiento recuperable, pronóstico y reglas explicables del piloto."""
import collections
import datetime as dt
import json
import math
import re
import threading
import time
import unicodedata
import urllib.parse
import urllib.request

ZONES = {"Viacha": (-16.65,-68.30), "Achacachi": (-16.05,-68.68), "Patacamaya": (-17.24,-67.92),"Tarata":(-17.61,-66.02),"Yamparáez":(-19.18,-65.12)}
ZONES.update({"La Paz":(-16.536172,-68.06435),"Palos Blancos":(-15.564881,-67.319786),"Tiraque":(-17.47645,-65.652847)})
CROPS = ["Papa","Quinua","Maíz","Haba","Cebada","Lechuga","Cacao"]
STAGES = ["Sin verificar","Emergencia","Desarrollo","Floración","Maduración"]
PLANS = {"Gratuito": 5, "Productor": 50, "Asociación": 100}
SCENES = ["Helada","Estable","Granizo","Lluvia intensa","Viento fuerte","Déficit de lluvia","Cambio brusco"]
TZ = dt.timezone(dt.timedelta(hours=-4))
def now():
    return dt.datetime.now(TZ)
def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if not unicodedata.combining(c))
def tokens(s):
    return [w for w in re.findall(r'[a-z]+', norm(s)) if len(w)>2 and w not in {'para','con','por','una','que','del','como','mis','las','los','hay','hoy','puedo','hacer','esta','tengo'}]
def retrieve(query, docs):
    """Sparse term vectors with inverse document frequency and cosine similarity."""
    corpus=[collections.Counter(tokens(d['title']+' '+d['tags']+' '+d['body'])) for d in docs]
    df=collections.Counter(w for words in corpus for w in words)
    def vector(words):
        return {w:n*(1+math.log((1+len(docs))/(1+df[w]))) for w,n in words.items()}
    q=vector(collections.Counter(tokens(query)))
    size=lambda v: math.sqrt(sum(i*i for i in v.values())) or 1
    candidates=[]
    for d, words in zip(docs,corpus):
        v=vector(words)
        score=sum(val*v.get(w,0) for w,val in q.items())/(size(v)*size(q))
        if score>0.035: candidates.append((score,d))
    return [d for _,d in sorted(candidates,key=lambda x:-x[0])][:2]

BASE = [
("Vigilancia de heladas","Todos","helada frio proteger temperatura madrugada","Revisa la temperatura cerca de las plantas al amanecer. Observa primero las partes bajas de la parcela y registra si hubo escarcha."),
("Seguimiento del suelo","Todos","riego regar agua sequia deficit lluvia humedad seco","Comprueba la humedad en varios puntos antes de decidir el riego. Anota cuándo llovió por última vez y si el suelo sigue húmedo."),
("Papa en floración","Papa","flores floracion tuberculos agua riego papa","Durante la formación de tubérculos conviene vigilar los cambios de humedad. Revisa el suelo y conversa con el técnico si encuentras estrés persistente."),
("Registro de la quinua","Quinua","quinua panoja floracion grano maduracion cosecha","Anota la etapa de las panojas y compara plantas de varios sectores. El color y la maduración pueden variar entre variedades."),
("Después de una tormenta","Todos","granizo lluvia intensa drenaje tormenta inundacion","Cuando sea seguro ingresar, observa si hay agua acumulada y fotografía el mismo sector para comparar su recuperación."),
("Ráfagas y cambios térmicos","Todos","viento rafagas cambio brusco temperatura amplitud","Revisa los soportes y las protecciones existentes antes del evento. Después registra daños visibles y la hora aproximada."),
("Observación de síntomas","Todos","manchas amarillas plaga hojas enfermas enfermedad insectos","Registra cuándo aparecieron los síntomas, qué parte de la planta afectan y cuántas plantas los presentan. Comparte las observaciones con un técnico local.")
]
CACHE={}
LOCK=threading.Lock()
def forecast(zone,mode,scene,coords=None,force=False):
    today=now().date()
    if mode=='demo':
        lows=[5,5,6,4,6,5,4]; highs=[17,18,18,16,16,17,16]; rains=[2,4,1,2,0,2,1]; gust=[20,18,24,20,15,18,21]; codes=[3]*7
        if scene=='Helada': lows[1:3]=[-3,-1]
        elif scene=='Granizo': codes[1]=96
        elif scene=='Lluvia intensa': rains[1]=34
        elif scene=='Viento fuerte': gust[1]=62
        elif scene=='Déficit de lluvia': rains=[0]*7
        elif scene=='Cambio brusco': lows[1]=14; highs[1]=27
        days=[dict(date=str(today+dt.timedelta(days=i)),low=lows[i],high=highs[i],rain=rains[i],gust=gust[i],code=codes[i]) for i in range(7)]
        return dict(days=days,source="Escenario simulado · NEXTECH",stamp=now().isoformat(timespec="minutes"),mode=mode)
    lat,lon=coords or ZONES[zone]
    key=(float(lat),float(lon))
    with LOCK:
        cached=CACHE.get(key)
        if not force and cached and time.time()-cached[0]<600 and cached[1]['days'][0]['date']==str(today): return cached[1]
    fields=['temperature_2m_min','temperature_2m_max','precipitation_sum','wind_gusts_10m_max','weather_code','precipitation_probability_max']
    current=['temperature_2m','relative_humidity_2m','wind_speed_10m','precipitation']
    query=dict(latitude=lat,longitude=lon,daily=','.join(fields),current=','.join(current+['wind_direction_10m']),timezone='America/La_Paz',forecast_days=7)
    url='https://api.open-meteo.com/v1/forecast?'+urllib.parse.urlencode(query)
    source='Open-Meteo · modelo meteorológico'
    try:
        with urllib.request.urlopen(url,timeout=10) as resp: payload=json.load(resp)
    except OSError:
        with urllib.request.urlopen(url.replace('/v1/forecast?','/v1/gfs?'),timeout=10) as resp: payload=json.load(resp)
        source='Open-Meteo · modelo alternativo GFS'
    raw=payload['daily']; obs=payload['current']
    days=[dict(date=date,**{k:raw[f][i] for k,f in zip(('low','high','rain','gust','code','prob'),fields)}) for i,date in enumerate(raw['time'])]
    values=[v for d in days for k,v in d.items() if k!='date']+[obs.get(k) for k in current]
    if len(days)!=7 or any(type(v) not in (int,float) or not math.isfinite(v) for v in values): raise ValueError("Datos meteorológicos incompletos")
    direction=obs.get('wind_direction_10m')
    if direction is not None and (type(direction) not in (int,float) or not 0<=direction<=360):raise ValueError('Dirección de viento inválida')
    if not 0<=obs['relative_humidity_2m']<=100 or min(obs['precipitation'],obs['wind_speed_10m'])<0:raise ValueError('Observación inconsistente')
    if any(d['low']>d['high'] or not 0<=d['prob']<=100 or min(d['rain'],d['gust'])<0 for d in days):raise ValueError('Valores diarios inconsistentes')
    if days[0]['date']!=str(today): raise ValueError("Pronóstico fuera de fecha")
    measurement=dt.datetime.fromisoformat(obs['time']).replace(tzinfo=TZ)
    if not -1200 <= (now()-measurement).total_seconds() <= 7200: raise ValueError("Datos actuales fuera de vigencia")
    result=dict(days=days,current={**{k:obs[k] for k in current},'wind_direction_10m':obs.get('wind_direction_10m')},valid=measurement.isoformat(timespec='minutes'),source=source,stamp=now().isoformat(timespec="seconds"),mode="live")
    with LOCK: CACHE[key]=(time.time(),result)
    return result

def risks(days,crop,stage,current=None):
    frost={'Papa':1,'Quinua':-1,'Cebada':0,'Maíz':2,'Haba':1}.get(crop,1)+(1 if stage in ('Floración','Emergencia') else 0)
    result=[]
    for i,d in enumerate(days):
        def add(kind,evidence,action):
            result.append(dict(kind=kind,date=d['date'],evidence=evidence,action=action))
        heat={'Papa':29,'Quinua':32,'Maíz':36,'Haba':30,'Cebada':32}.get(crop,32)
        if d['high']>=heat: add("Calor extremo",f"Máxima {d['high']:.1f} °C ≥ umbral piloto {heat} °C para {crop}","Comprueba la humedad del suelo y registra señales de estrés térmico en varias plantas.")
        if i==0 and current and current.get('relative_humidity_2m',100)<25:
            add("Aire seco",f"Humedad del aire {current['relative_humidity_2m']} % < 25 %","Comprueba la humedad del suelo antes de decidir el riego.")
        if d['low']<=frost: add("Helada",f"Mínima {d['low']} °C ≤ umbral piloto {frost} °C","Comprueba la mínima en la parte baja de tu parcela y revisa las protecciones disponibles.")
        if d['code'] in (96,99): add("Granizo",f"Código meteorológico {d['code']} compatible con granizo","Revisa las protecciones existentes antes de la tormenta.")
        if d['rain']>=25: add("Lluvia intensa",f"{d['rain']} mm previstos en el día ≥ 25 mm","Revisa las salidas de drenaje cuando sea seguro.")
        if d['gust']>=45: add("Viento fuerte",f"Ráfagas de {d['gust']} km/h ≥ 45 km/h","Comprueba las sujeciones de las cubiertas.")
        if i and abs(d['low']-days[i-1]['low'])>=8: add("Cambio brusco",f"Variación de mínimas de {abs(d['low']-days[i-1]['low']):g} °C en 24 h","Contrasta las mínimas con un termómetro local.")
        if i==6 and sum(x['rain'] for x in days[:7])<3: add("Déficit de lluvia","Menos de 3 mm en siete días de previsión","Comprueba la humedad del suelo. Una semana seca por sí sola no confirma sequía.")
    return result
