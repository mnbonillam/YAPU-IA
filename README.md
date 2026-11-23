# Yapu IA

Panel agroclimático para Bolivia, gestión de parcelas y asistente por WhatsApp. Un único proceso Python atiende el panel y el webhook y ejecuta la revisión periódica de riesgos. SQLite guarda los registros en un volumen persistente. La primera visita carga el catálogo de referencia y lecturas fechadas.

## Publicar en Railway

1. En Railway, abre **New Project → Deploy from GitHub repo**, autoriza este repositorio y selecciona **mnbonillam/YAPU-IA**, rama **main**. Conserva la carpeta raíz. Railway lee el Dockerfile y railway.toml. El arranque es automático.
2. Añade un **Volume** al servicio Yapu con ruta de montaje **/data**. Usa una sola réplica y desactiva el modo de suspensión (Serverless/App Sleeping) para mantener activo el planificador.
3. En **Variables**, añade los valores de la tabla. Aplica los cambios y despliega. El contenedor ya configura el host, la ruta de datos y las cookies HTTPS.
4. En **Settings → Networking → Public Networking → Generate Domain** crea el dominio del servicio. Si te pide puerto, usa el puerto PORT efectivo del servicio (8765 por defecto en el contenedor). Abre el dominio y luego **/api/health**, que devuelve {"ok":true}.
5. En Meta, abre la app que administra el número de producción. En **WhatsApp → Configuración → Webhooks**, pega el dominio HTTPS de Railway seguido de **/webhook** y el valor de WA_VERIFY_TOKEN. Pulsa **Verificar y guardar** y suscribe **messages**. Comprueba que la app esté suscrita a la cuenta empresarial del número registrado y habilitada para recibir eventos de producción. Para verificar la suscripción usa GET /ID_DE_CUENTA/subscribed_apps en el Explorador Graph y, si tu app falta, POST a la misma ruta con un token autorizado.
6. Desde otro celular abre el enlace https://wa.me/ seguido del número internacional sin signos. Envía **ALTA Viacha/Papa/Floración**. Comprueba que recibas respuesta. En el panel registra una parcela y comprueba que persista tras un redeploy desde el mismo navegador. Las sesiones del panel se identifican por cookie.
7. Para avisos automáticos vincula el teléfono desde Alertas con el código VINCULAR y configura la plantilla aprobada de la tabla. Las pruebas del laboratorio tienen su propio buzón. Consulta [Integraciones](INTEGRACIONES.md) para el formato de la plantilla y los estados de entrega.

| Variable | Valor en Railway |
|---|---|
| YAPU_ADMIN_KEY | Contraseña larga y aleatoria para el equipo administrador |
| WA_PHONE_ID | Phone Number ID del número de producción |
| WA_PUBLIC_NUMBER | Número del negocio con código de país y solo dígitos |
| WA_GRAPH_VERSION | Versión habilitada en la app, con prefijo v |
| WA_TOKEN | Token vigente de usuario del sistema con acceso a la cuenta y permiso para enviar mensajes |
| WA_APP_SECRET | Clave secreta de la misma app Meta |
| WA_VERIFY_TOKEN | Cadena aleatoria privada, idéntica en Meta y en Railway |
| WA_ALERT_TEMPLATE | Nombre exacto de la plantilla aprobada para avisos proactivos |
| WA_LANGUAGE | Idioma aprobado para esa plantilla, por ejemplo es |
| OPENAI_API_KEY | Opcional para funciones de IA externa |

Las claves se guardan exclusivamente como variables del servicio. El dominio del panel y el webhook comparten el proceso. El ZIP de origen incluye datos públicos de referencia. Los registros personales de la instalación de Windows requieren una migración independiente del archivo SQLite a /data.

## Desarrollo y pruebas

Python 3.10 o superior. Para Windows abre INICIAR_WINDOWS.bat. Para otros sistemas usa `python app.py`. Ejecuta `python -m unittest discover -s tests -q` desde la raíz. Más detalles en [manual del proyecto](LEEME.md) y [documentación de API](docs/API.md).
