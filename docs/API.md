# API de los cinco módulos

Base local http://localhost:8765/api. Las solicitudes POST usan Content-Type application/json. La primera consulta al atlas asigna la cookie HttpOnly que identifica el espacio persistente del navegador. Los registros se identifican por id (productor, alerta o ensayo) y number (parcela). La API devuelve JSON. Las consultas privadas validan la sesión en el servidor.

| Método y ruta bajo /api | Entrada | Resultado |
|---|---|---|
| GET /atlas | Cookie, si existe | Red del espacio, catálogo público, productores, parcelas, últimas condiciones, alertas vigentes, mensajes, actividad y ensayos. Primera visita importa el catálogo en una transacción. |
| POST /atlas/producer | nombre, comunidad, telefono opcional, notas opcionales, id para editar | Identificador del productor. |
| POST /atlas/parcel | productor, name, zone, crop, stage, lat, lon, area, altitud opcional, caracteristicas opcionales, consent=true; number para editar | Número de parcela. El formulario solicita después su primera actualización de clima. |
| POST /atlas/archive | id de productor o number de parcela | Desactivación lógica. Al desactivar el titular se detiene también el monitoreo de sus terrenos. |
| POST /ops/refresh | number | Obtiene condiciones y pronóstico. Registra evaluación, actualiza avisos, crea notificaciones y despierta los paneles conectados. |
| GET /atlas/history?number=N | Parcela del espacio | Últimas 192 lecturas, 30 evaluaciones, hasta 100 avisos, las últimas 50 notificaciones y los intentos de envío fallidos del canal externo. Una parcela archivada conserva su historial. |
| POST /atlas/simulate | number, scene, factor entre 0.25 y 2 | Comparación analítica, intensidad aplicada sobre la base meteorológica en el servidor, aviso del fenómeno y código de ensayo. Si se supera el umbral se registra una entrega en el buzón de prueba. |
| GET /atlas/run?id=N | Ensayo del espacio | Resultado guardado con su recepción y acuse, cuando existan. |
| POST /atlas/sim-ack | id | Confirma la recepción simulada y conserva la hora del primer acuse. |
| POST /ops/ack | number, alert | Fecha de acuse de un aviso real activo. El panel se actualiza automáticamente. |
| GET /ops/wait?seen=V | Versión previamente observada | Espera de hasta 18 segundos o respuesta inmediata si cambia el espacio. El cliente vuelve a leer el estado confirmado. |
| POST /atlas/link | number de parcela propia registrada | Código de un solo uso por 15 minutos para el teléfono que dio ALTA en WhatsApp. |
| POST /ops/message, /ops/ask | number, text | Mensaje interno o respuesta contextual. |
| POST /ops/whatsapp | number, text, cabecera X-Yapu-Admin | Respuesta del operador en una conversación de WhatsApp habilitada. |
| GET /health | — | Disponibilidad del proceso. |

Los métodos POST de edición y desactivación permiten usar formularios Windows/navegador con la API local. Los errores de validación llevan HTTP 400; los de autorización de equipo llevan 403. Una actualización meteorológica fallida devuelve 503 y conserva el último registro disponible. Los campos de fecha climática incluyen zona horaria UTC−4.

## Sesión de prueba con Python

Primero inicia la aplicación. Desde otra consola puedes ejecutar lo siguiente para verificar consultas sin depender del navegador.

```python
import json, urllib.request, http.cookiejar
cliente = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base = "http://localhost:8765/api/"
def api(ruta, datos=None):
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    req = urllib.request.Request(base + ruta, data=cuerpo, headers={"Content-Type":"application/json"})
    with cliente.open(req) as respuesta:
        return json.load(respuesta)
panel = api("atlas")
n = panel["parcels"][0]["number"]
print(api("atlas/history?number=" + str(n))["history"][0])
ensayo = api("atlas/simulate", {"number": n, "scene":"Helada", "factor": 2})
print(ensayo["notice"])
if "delivery" in ensayo:
    api("atlas/sim-ack", {"id": ensayo["id"]})
    print(api("atlas/run?id=" + str(ensayo["id"]))["delivery"])
```

Las APIs de contenidos, suscripciones, consultas por WhatsApp, casos remitidos a revisión, mercado y administración del cuaderno continúan en app.py. El webhook público es /webhook, fuera de /api. Requiere una aplicación de Meta configurada y firma válida. Consulta INTEGRACIONES.md para su instalación.
