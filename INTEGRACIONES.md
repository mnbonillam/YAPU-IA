# Conectar el piloto

## Clima

En **Mi parcela → Configurar parcela** selecciona **Pronóstico en línea**. El backend solicita a Open-Meteo las condiciones actuales y los valores diarios en las coordenadas de la parcela y los conserva temporalmente. Requiere acceso del servidor a api.open-meteo.com. Comprueba las condiciones comerciales del proveedor antes de ofrecer suscripciones. No se han habilitado alianzas ni datos de SENAMHI.

## WhatsApp Business

1. Configura tu aplicación de Meta y su número de WhatsApp Business. Para verificar el canal, utiliza destinatarios habilitados en tu cuenta de prueba.
2. Despliega la aplicación detrás de HTTPS con un volumen persistente. Usa un solo proceso. Copia `.env.example` a `.env` o configura las variables en tu plataforma.
3. Define `WA_PHONE_ID`, `WA_TOKEN`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN` y `WA_GRAPH_VERSION`. Para la versión usa el identificador con prefijo v que muestre tu aplicación Meta. Mantén las claves fuera del repositorio.
4. Configura como callback **https://TU-DOMINIO/webhook**, usa el mismo token de verificación y suscribe el campo **messages** para la cuenta de WhatsApp correspondiente. El mismo endpoint acepta el desafío por GET y verifica la firma SHA-256 de los POST.
5. Escribe **ALTA Viacha/Papa/Floración** desde el teléfono de prueba. Comparte la ubicación del terreno y envía «¿Hay riesgo de helada mañana?». Verifica el nombre del cultivo, la fuente y la fecha. **BAJA** elimina ese perfil y deja de programar alertas.

### Plantilla para avisos proactivos

Crea una plantilla con **siete parámetros de cuerpo**, sin encabezado dinámico. Solicita su aprobación en el idioma configurado. Define `WA_ALERT_TEMPLATE` con su nombre exacto y `WA_LANGUAGE` con el código exacto autorizado. Ejemplo de cuerpo:

> Aviso agrícola Yapu IA. Fenómeno {{1}}. Parcela {{2}}. Fecha prevista {{3}}. Evidencia {{4}}. Orientación {{5}}. Fuente y consulta {{6}}. Para evaluar el aviso, responde ECO {{7}} SI NO, cambiando las dos respuestas según si ocurrió y si fue útil.

Las alertas se revisan al iniciar y cada 10 minutos. Solo los perfiles de WhatsApp con alta reciben envíos reales. El panel muestra la aceptación de la API y evoluciona a enviado, entregado, leído o fallido cuando llegan los eventos firmados del proveedor. Los acuses de una alerta se registran independientemente de las confirmaciones de lectura. Si la conexión falla justo después de que el proveedor acepte un envío puede producirse un duplicado al reintentar. No hay mediciones de latencia ni disponibilidad de producción.

### Voz y agente de lenguaje opcionales

Configura `OPENAI_API_KEY` para transcribir las notas de voz entrantes OGG (hasta 10 MB en este piloto). El procesador responde en texto. La clave también activa la reformulación de orientación en perfiles con consentimiento. Puedes cambiar `OPENAI_MODEL` por un modelo de chat disponible en tu cuenta. El sistema utiliza directamente las fichas y reglas cuando estas funciones están deshabilitadas o falla la reformulación. La transcripción requiere audio válido, saldo, conectividad y permiso del proveedor. En la web, la lectura y el dictado dependen del navegador y sus permisos.

## Alojamiento

El ZIP incluye Dockerfile. Desde la carpeta extraída puedes crear una imagen con `docker build -t yapu-ia .`. Ejemplo local de contenedor:

```bash
docker run --rm -p 127.0.0.1:8765:8765 -v yapu-datos:/data yapu-ia
```

Para un piloto remoto, configura tus credenciales como secretos del alojamiento, un volumen persistente en /data y HTTPS mediante proxy inverso. Define `YAPU_HOST=0.0.0.0`, el `PORT` que indique el proveedor y `YAPU_HTTPS=1` tras activar HTTPS. Asigna una clave aleatoria larga a `YAPU_ADMIN_KEY`. El contenedor se ejecuta como usuario sin privilegios. La ruta **GET /api/health** sirve para un control básico de disponibilidad. El proceso debe seguir en ejecución para despachar alertas. GitHub Pages por sí solo no ejecuta el backend.

## Comprobación antes del piloto en campo

Verifica el alta y la baja con dos números autorizados. Valida la transcripción con una nota en español y confirma la recepción de una plantilla aprobada con datos de prueba en una instancia de ensayo. Comprueba el respaldo y la restauración en un directorio independiente. Conserva por separado los datos de ensayo y los del piloto real. Antes de incorporar productores, define el responsable de revisar las derivaciones y revisa los umbrales con un especialista local.

La publicación en nube, el envío a teléfonos físicos, el cobro de suscripciones y la validación agronómica siguen pendientes del equipo titular.

## Asociación de una parcela del Atlas a un destinatario real

En Alertas, selecciona una parcela propia y genera un código. Desde el teléfono inscrito con ALTA envía VINCULAR seguido de ese código. Solo se almacena su hash y vence en quince minutos. Se usa una vez. El planificador consultará el número del perfil vinculado al enviar la plantilla aprobada. Un teléfono escrito en la ficha de contacto por sí solo no habilita envíos. BAJA desde WhatsApp elimina el perfil receptor y revoca el vínculo. Usa ACUSE seguido del identificador del aviso o ECO para retroalimentación.

El flujo simulado de Laboratorio funciona sin cuenta Meta. Registra entrega en un buzón de prueba, permite acusar recibo y aguanta reinicios mediante SQLite. «Publicada en el panel», «recibida en buzón de prueba» y «entregada por WhatsApp» corresponden a eventos diferentes.

## Prueba desde el teléfono de Marcela

En Meta, selecciona tu propio teléfono en Destinatario, verifícalo y envía la plantilla de prueba. El número emisor de este proyecto es +1 555 141 7667. El identificador numérico del emisor ya está en conectar_whatsapp.py.

En Windows instala cloudflared y ejecuta CONECTAR_WHATSAPP.bat. El programa solicita el token de acceso de WhatsApp y la clave secreta de la aplicación. Los valores introducidos se guardan en memoria durante esa ejecución. El programa muestra el token de verificación y la URL HTTPS terminada en /webhook. Copia ambos al formulario de webhooks de Meta, verifica, guarda y suscribe messages. Desde el celular verificado escribe ALTA Viacha/Papa/Floración al número de prueba y luego pregunta por el clima. Para abrir el panel local, usa también INICIAR_WINDOWS.bat desde esta misma carpeta. El receptor y el panel comparten la base local. Este arranque del receptor sirve para respuestas a mensajes entrantes. Para programar envíos proactivos configura el .env y la plantilla aprobada según las instrucciones anteriores.

Con un túnel temporal, vuelve a copiar URL y token de verificación en Meta cuando reinicies el receptor. Si el token de acceso caduca, genera otro en Meta. El campo de mensajes puede requerir que tu aplicación figure suscrita a la cuenta de WhatsApp Business. En las herramientas de Meta comprueba la cuenta 1885939885925417. Evita ejecutar dos receptores para la misma URL.

## Alta de tu número propio desde Windows

1. En Meta → WhatsApp → Paso 2, agrega tu número, verifica el SMS o llamada y completa el registro hasta que el número figure conectado. Si ya usas esa línea en WhatsApp, revisa las opciones de coexistencia o migración que te ofrece Meta antes de modificar la cuenta existente.
2. En Configuración de la API selecciona ese número y copia su Phone Number ID, el ID de la cuenta de WhatsApp Business y la versión Graph. En la configuración del negocio crea un usuario del sistema con acceso a tu app y a la cuenta WhatsApp. Genera un token para la app con whatsapp_business_management y whatsapp_business_messaging. La clave secreta está en Configuración de la app → Básica.
3. Descomprime este ZIP. Ejecuta CONFIGURAR_MI_NUMERO.bat. Introduce los datos, comprueba el número que devuelve Meta y confirma con s. Puedes suscribir la app a la cuenta desde el asistente. La configuración se guarda en .env de esta carpeta. Guarda este archivo en privado y exclúyelo al compartir copias del proyecto.
4. Cierra los procesos anteriores de Yapu. Abre INICIAR_WINDOWS.bat y CONECTAR_WHATSAPP.bat. En Meta, configura exactamente la URL terminada en /webhook y el token de verificación de la ventana. Verifica, guarda y activa messages. Para uso público, completa los requisitos de publicación que aparezcan en el panel de la app.
5. Desde otro celular, abre el enlace wa.me mostrado por el asistente y envía ALTA Viacha/Papa/Floración. Comprueba la respuesta en ese mismo chat. Con túnel temporal, deja la PC y ambas ventanas activas y actualiza la URL en Meta si cambia. Para servicio continuo usa un servidor con HTTPS estable y volumen persistente, como se indica en la sección de despliegue.
