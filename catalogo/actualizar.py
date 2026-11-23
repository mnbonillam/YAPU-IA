"""Regenera las capturas meteorológicas distribuidas con el piloto."""
import concurrent.futures
import datetime as dt
import json
from pathlib import Path
import urllib.parse
import urllib.request

SITES=[(r['site'],r['lat'],r['lon']) for r in json.loads(Path(__file__).with_name('predios.json').read_text(encoding='utf-8'))]
CURRENT='temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m'
DAILY='temperature_2m_min,temperature_2m_max,precipitation_sum,wind_gusts_10m_max,weather_code,precipitation_probability_max'
def download(site):
    name,lat,lon=site
    query=dict(latitude=lat,longitude=lon,current=CURRENT,hourly=CURRENT,daily=DAILY,past_days=7,forecast_days=7,timezone='America/La_Paz')
    url='https://api.open-meteo.com/v1/forecast?'+urllib.parse.urlencode(query)
    with urllib.request.urlopen(url,timeout=35) as r: data=json.load(r)
    assert len(data['daily']['time'])==14 and data['current']['temperature_2m'] is not None
    return dict(site=name,lat=lat,lon=lon,url=url,retrieved=dt.datetime.now(dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=-4))).isoformat(timespec='seconds'),response=data)
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: result=list(pool.map(download,SITES))
    path=Path(__file__).with_name('clima.json')
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8');tmp.replace(path)
    for s in result: print(s['site'],s['response']['current']['time'],s['response']['current']['temperature_2m'])
