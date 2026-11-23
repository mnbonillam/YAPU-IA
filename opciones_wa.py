"""Menús nativos de WhatsApp. Cada selección conserva su ruta de alta."""
from agro import ZONES, CROPS, STAGES

CONSULTAS = {
    "hoy": ("Clima de hoy", "¿Qué temperatura se espera hoy?"),
    "helada": ("Helada mañana", "¿Hay riesgo de helada mañana?"),
    "riego": ("Revisar humedad", "¿Cómo reviso la humedad del suelo?"),
}


def texto(body):
    return {"type": "text", "text": {"body": body[:4000]}}


def opciones(body, items, lista=None):
    if lista:
        action = {"button": lista, "sections": [{"rows": [
            {"id": key, "title": title} for key, title in items]}]}
    else:
        action = {"buttons": [{"type": "reply", "reply": {"id": key, "title": title}}
                              for key, title in items]}
    return {"type": "interactive", "interactive": {
        "type": "list" if lista else "button", "body": {"text": body}, "action": action}}


def seleccion(message):
    interactive = message.get("interactive", {})
    return interactive.get(interactive.get("type"), {}) if message.get("type") == "interactive" else {}


def bienvenida():
    return opciones("🌱 *¡Hola! Soy Yapu IA.*\n\nRegistra tu cultivo para consultar el clima y los riesgos de tu parcela.",
                    [("alta", "Registrar cultivo")])


def menu(body):
    if len(body) > 1024:
        return texto(body[:3950] + "\n\nEscribe Menú para ver las opciones.")
    return opciones(body, [(key, item[0]) for key, item in CONSULTAS.items()])


def respuesta(c, phone, message, respond):
    current = c.execute("SELECT consent FROM users WHERE phone=?", (phone,)).fetchone()
    enrolled = bool(current and current["consent"])
    chosen = seleccion(message).get("id", "")
    path = chosen.split("/")
    if path[0] == "alta" and not enrolled:
        values = path[1:]
        steps = [(ZONES, "📍 ¿En qué municipio está tu parcela?", "Elegir municipio"),
                 (CROPS, "🌱 ¿Qué cultivas en tu parcela?", "Elegir cultivo"),
                 (STAGES, "🌿 ¿En qué etapa está tu cultivo?", "Elegir etapa")]
        if any(v not in step[0] for v, step in zip(values, steps)):
            return bienvenida()
        if len(values) < 3:
            choices, question, label = steps[len(values)]
            return opciones(question, [(chosen + "/" + v, v) for v in choices], label)
        if len(values) == 3:
            zone, crop, stage = values
            return opciones(f"*Confirma tu parcela*\n📍 {zone}\n🌱 {crop} · {stage}\n\n"
                            "Al registrarte aceptas guardar tu teléfono, parcela y consultas. "
                            "Si usas voz y está habilitada, el proveedor de IA procesará el audio. "
                            "Puedes eliminar tu perfil con BAJA.",
                            [(chosen + "/ok", "Aceptar y registrar"), ("alta", "Volver a elegir")])
        if len(values) != 4 or values[-1] != "ok":
            return bienvenida()
        message = {"type": "text", "text": {"body": "ALTA " + "/".join(values[:3])}}
    elif chosen:
        if not enrolled:
            return bienvenida()
        query = CONSULTAS.get(chosen, ("", "Menú"))[1]
        message = {"type": "text", "text": {"body": query}}
    reply = respond(c, phone, message)
    active = c.execute("SELECT consent FROM users WHERE phone=?", (phone,)).fetchone()
    if active and active["consent"]:
        return menu(reply)
    if message.get("text", {}).get("body", "").strip().upper() == "BAJA":
        return texto(reply)
    if message.get("text", {}).get("body", "").upper().startswith("ALTA "):
        return opciones("Revisa el municipio, el cultivo y la etapa. También puedes elegirlos aquí.",
                        [("alta", "Registrar cultivo")])
    return bienvenida()
