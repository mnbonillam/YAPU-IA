"""Inicia el receptor local exclusivo para las pruebas de Meta."""
import getpass
import os
import re
import secrets
import shutil
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlsplit
from app import Handler,ThreadingHTTPServer
from core import init

ROOT=Path(__file__).resolve().parent

class Receptor(Handler):
    def do_GET(self):
        if urlsplit(self.path).path!='/webhook':return self.out({},404)
        super().do_GET()
    def do_POST(self):
        if self.path!='/webhook':return self.out({},404)
        super().do_POST()

def main():
    binary=shutil.which('cloudflared') or next((str(p) for p in (ROOT/'cloudflared.exe',ROOT/'cloudflared-windows-amd64.exe') if p.is_file()),None)
    if not binary:
        print('Instala Cloudflare Tunnel en Windows con: winget install --id Cloudflare.cloudflared -e')
        print('Después vuelve a abrir CONECTAR_WHATSAPP.bat. También puedes colocar cloudflared.exe junto al archivo BAT.')
        return
    config=ROOT/'.env'
    if config.exists():
        for line in config.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key,value=line.split('=',1);os.environ.setdefault(key.strip(),value.strip())
    os.environ.setdefault('WA_PHONE_ID','1422972450905408')
    os.environ.setdefault('WA_PUBLIC_NUMBER','15551417667')
    os.environ.setdefault('WA_GRAPH_VERSION','v23.0')
    for key,label in [('WA_TOKEN','Token de acceso de WhatsApp'),('WA_APP_SECRET','Clave secreta de la aplicación Meta')]:
        if not os.getenv(key):
            value=getpass.getpass(label+' (pega y pulsa Enter, no se muestra): ').strip()
            if not value:raise ValueError('Falta '+label)
            os.environ[key]=value
    os.environ['WA_VERIFY_TOKEN']=os.getenv('WA_VERIFY_TOKEN') or secrets.token_urlsafe(24)
    init()
    with ThreadingHTTPServer(('127.0.0.1',0),Receptor) as server:
        threading.Thread(target=server.serve_forever,daemon=True).start()
        print('Token de verificación para Meta:',os.environ['WA_VERIFY_TOKEN'],flush=True)
        print('Abriendo URL HTTPS temporal…',flush=True)
        cmd=[binary,'tunnel','--url','http://127.0.0.1:'+str(server.server_port)]
        with subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace') as tunnel:
            announced=False
            try:
                for line in tunnel.stdout:
                    url=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com\b',line)
                    if url and not announced:
                        print('URL de devolución de llamada:',url.group()+'/webhook',flush=True)
                        print('En Meta: verifica y guarda. Suscríbete al campo messages. Mantén abierta esta ventana.',flush=True)
                        announced=True
                    elif 'ERR' in line:print(line.strip(),flush=True)
                if not announced:print('El túnel terminó sin publicar la URL. Revisa la conexión y vuelve a ejecutar.')
            finally:
                if tunnel.poll() is None:tunnel.terminate()
                server.shutdown()
if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('Conexión cerrada.')
    except (OSError,ValueError) as e:print(str(e))
