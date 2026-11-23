"""Configura el número propio de Yapu en la instalación local."""
import getpass
import json
import os
import re
import secrets
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def graph(version, path, token, method="GET"):
    req = urllib.request.Request(
        f"https://graph.facebook.com/{version}/{path}", method=method,
        headers={"Authorization": "Bearer " + token},
        data=b"" if method == "POST" else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            error = json.loads(exc.read()).get("error", {})
        except (ValueError, AttributeError):
            error = {}
        raise ValueError(f"Meta rechazó la consulta (HTTP {exc.code}, código {error.get('code', 'desconocido')}). Revisa los permisos del token y la cuenta seleccionada.") from None


def find_phone(version, account, phone_id, token):
    path = account + "/phone_numbers?fields=id,display_phone_number,verified_name&limit=100"
    cursor = ""
    while True:
        page = graph(version, path + cursor, token)
        for phone in page.get("data", []):
            if phone.get("id") == phone_id:
                return phone
        paging = page.get("paging", {})
        after = paging.get("cursors", {}).get("after")
        if not paging.get("next") or not after:
            raise ValueError("El número indicado no figura en esa cuenta con ese token.")
        cursor = "&after=" + urllib.parse.quote(after, safe="")


def save_env(path, values):
    original = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    lines = [s for s in original.splitlines() if s.partition("=")[0].strip() not in values]
    lines.extend(f"{key}={value}" for key, value in values.items())
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        tmp = Path(temp.name)
    try:
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main():
    print("Usa los datos de tu número de producción. Las claves se guardarán en el archivo .env privado de esta instalación.")
    version = input("Versión Graph que muestra Meta [v27.0]: ").strip() or "v27.0"
    account = input("Identificador de cuenta de WhatsApp Business (WABA ID): ").strip()
    phone_id = input("Phone Number ID del número propio: ").strip()
    if not re.fullmatch(r"v[0-9]+\.[0-9]+", version) or not all(re.fullmatch(r"[0-9]+", v) for v in (account, phone_id)):
        raise ValueError("Revisa la versión y los dos identificadores numéricos.")
    if phone_id == "1422972450905408":
        raise ValueError("Seleccionaste el número de prueba. Copia el ID del número propio.")
    token = getpass.getpass("Token de acceso de la app Yapu: ").strip()
    secret = getpass.getpass("Clave secreta de la misma app: ").strip()
    if not token or not secret:
        raise ValueError("Falta una credencial.")
    phone = find_phone(version, account, phone_id, token)
    number = re.sub(r"[^0-9]", "", phone.get("display_phone_number", ""))
    if not re.fullmatch(r"[1-9][0-9]{6,14}", number):
        raise ValueError("Meta no devolvió un teléfono internacional válido.")
    print(f"Meta reconoce +{number} · {phone.get('verified_name', '')}")
    if input("¿Usar este número y guardar en este equipo? [s/N]: ").lower().strip() != "s":
        return
    values = dict(WA_GRAPH_VERSION=version, WA_PHONE_ID=phone_id, WA_PUBLIC_NUMBER=number,
                  WA_TOKEN=token, WA_APP_SECRET=secret, WA_VERIFY_TOKEN=secrets.token_urlsafe(32))
    save_env(ROOT / ".env", values)
    print("Configuración guardada. Reinicia el panel y abre CONECTAR_WHATSAPP.bat. Verifica nuevamente el webhook con los datos que muestre.")
    if input("¿Suscribir esta app a los webhooks de esta cuenta en Meta? [s/N]: ").strip().lower() == "s":
        if graph(version, account + "/subscribed_apps", token, "POST").get("success") is not True:
            raise ValueError("Meta no confirmó la suscripción. La configuración local ya está guardada.")
        print("Meta confirmó la suscripción de la app. Activa también el campo messages en el panel.")
    print("Enlace para compartir después de probar la respuesta: https://wa.me/" + number)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print("Configuración interrumpida.", exc)
        raise SystemExit(1)
