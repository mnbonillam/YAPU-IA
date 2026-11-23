# Yapu IA · Cuaderno de campo

**NEXTECH · Universidad Mayor de San Andrés · INF-264**  
El futuro de tu cosecha, en tus manos.

Prototipo del asistente agrícola por WhatsApp de Marcela Nadia Bonilla Mamani, Eynar Aron Castañeta Machicado, Angela Evelyn Cusi Limachi, Monzerrat Fabiana Mendoza Durán y Belinda Villca Arcaya. Piloto de papa y quinua en Viacha, Achacachi y Patacamaya, La Paz.

## Primera pantalla de esta versión

Abre **Resumen**. El ZIP incluye capturas reales de Open-Meteo para cinco predios agrícolas documentados. Las fechas del modelo y de la descarga viajan con los datos. La carga inicial funciona con la red desconectada. La cartografía base de OpenStreetMap y las actualizaciones posteriores requieren internet.

En **Parcelas → Fuentes** puedes abrir las publicaciones sobre Choquenaira, Patacamaya, Cota Cota, Sapecho y Toralapa. Cuatro predios se agrupan bajo la Facultad de Agronomía de la UMSA y uno bajo INIAF. Son referencias públicas. Su inclusión no acredita una suscripción, participación en el piloto, cultivo actual ni recepción de avisos. La etapa comienza como «Sin verificar». Los campos sin respaldo aparecen con un guion.

La primera visita al atlas importa una copia de la red de referencia para ese espacio de trabajo, con cinco marcadores, dos entidades, siete días anteriores de clima horario, pronóstico y evaluaciones retrospectivas calculadas. La importación se realiza una sola vez por sesión persistente. El número de alertas se calcula del clima y su vigencia. Registrar productores propios crea registros distintos de las referencias.

**Para la exposición** sigue [el recorrido de los cinco módulos](docs/DEMOSTRACION.md). La [guía de módulos](docs/MODULOS.md) vincula código, dependencias, pruebas e instrucciones de cada integrante. El [contrato API](docs/API.md) explica las operaciones. El esquema PostgreSQL aportado se conserva en docs junto con su correspondencia con SQLite.

## Abrir en Windows

1. Extrae **todo** el ZIP a una carpeta con permiso de escritura.
2. Ten instalado **Python 3.10 o posterior**. La aplicación usa su biblioteca estándar.
3. Haz doble clic en **INICIAR_WINDOWS.bat**. Se abrirá el navegador. Si hace falta, escribe **http://localhost:8765**.
4. Deja abierta la consola. Allí aparece la clave para **Equipo**. Para detener el sistema, presiona Ctrl+C en esa ventana.

En Linux o macOS, desde la carpeta del proyecto, usa `python3 app.py --abrir`. También puedes usar `py -3 app.py --abrir` en PowerShell. El arranque local utiliza Python. La cartografía y el clima en vivo requieren internet. Los archivos HTML se sirven desde Python. Si el puerto está ocupado, copia `.env.example` a `.env` y cambia PORT.

## Recorrido del centro operativo

1. Desde el atlas abre **Cuaderno, equipo y mercado** para entrar al monitor de mensajería. El atlas precargado y este monitor comparten las parcelas del navegador.
2. Pulsa **Registrar parcela**, ingresa un nombre, municipio, cultivo, etapa y las coordenadas del terreno. Puedes usar GPS si el navegador tiene permiso. Al guardar se consulta el proveedor. Vuelve a registrar para monitorear más de una parcela.
3. Selecciona un marcador o usa el selector. La temperatura, humedad, viento y precipitación son valores del modelo para esa ubicación. Compara la hora del dato con la hora de consulta y revisa las máximas, mínimas y probabilidades de lluvia de los próximos tres días.
4. Una alerta muestra evidencia, fecha, severidad y orientación. **Acusar recibo** deja la fecha registrada y cambia el filtro donde aparece el aviso. La confirmación posterior de si ocurrió sigue en la bitácora. Si el pronóstico cambia y deja de superar el umbral, el aviso sale de la lista operativa.
5. Abre una ventana privada en la misma dirección. Pulsa **Equipo**, introduce la clave de la consola y selecciona **Abrir monitor del equipo**. Desde la primera ventana envía un mensaje al panel de la parcela. El operador lo recibe en su vista y puede responder. La conexión de espera HTTP despierta cuando se confirma un cambio en la base de datos. Ante una reconexión el cliente recupera el estado guardado.
6. Para ver mensajes de **WhatsApp real**, configura el webhook público HTTPS y el número de Meta según **INTEGRACIONES.md**. Luego el productor escribe ALTA desde su teléfono. Puede compartir su ubicación como mensaje de WhatsApp, consultar y acusar un aviso con `ACUSE número`. La opción **Responder por WhatsApp** aparece en la vista del equipo para una parcela de ese canal dentro de su ventana de atención.
7. **Consultar al asistente** usa la parcela seleccionada en el monitor. **Mi parcela**, **Asistente**, **Alertas** y **Mercado** permiten trabajar con el perfil principal. El laboratorio y el canal de prueba se mantienen para ensayos.

El monitor global está reservado al equipo. El productor ve sus propias parcelas. Las sesiones web se identifican con una cookie del navegador. Al perderla se pierde el acceso directo a ese perfil desde ese navegador. Si actualizas una instalación, conserva tu directorio de datos, crea un respaldo y arranca esta versión sobre una copia. La migración de SQLite añade campos y tablas en el primer inicio. Los perfiles anteriores de demostración quedan fuera del monitor; para incorporarlos, configura su clima en línea.

## Alcance frente al proyecto

| Requisito | Implementación y alcance |
|---|---|
| RF1 · Alta por WhatsApp | Alta con consentimiento, municipio, cultivo y etapa, actualización mediante otra ALTA y eliminación con BAJA. Hay simulador web y webhook para Meta. Una parcela por alta de WhatsApp y varias por titular en el monitor web. |
| RF2 · Agente experto | Recuperación de fichas con vectores dispersos TF-IDF y similitud coseno, reglas por cultivo/etapa y respuesta contextual trazable. Funciona localmente. GPT opcional reformula la orientación, junto a su texto de referencia. |
| RF3 · Pronóstico | Previsión diaria de siete días, caché de 10 minutos por coordenadas, consulta con hora boliviana y modo de demostración separado. |
| RF4 · Alertas | Helada, indicio meteorológico de granizo, déficit de lluvia semanal, lluvia intensa, viento y cambio brusco de mínimas. Revisión al iniciar y cada 10 minutos mientras el servidor esté encendido. Entrega en panel, y por plantilla aprobada si el canal está conectado. |
| RF5 · Medios | Mensajes de texto, notas de voz de WhatsApp con transcripción opcional y respuesta escrita. Dictado/lectura en navegadores compatibles y exportación de aviso PNG en la web. |
| RF6 · Derivación | Ante términos de riesgo o falta de coincidencias se crea un caso identificable en la cola del equipo; el cierre de revisión se refleja en el historial del productor. |
| RF7 · Planes | Gratuito, Productor Bs 20/mes y Asociación Bs 400/mes, un grupo piloto de hasta 50 socios. Límites de demostración de 5, 50 y 100 consultas diarias por productor, respectivamente. Cambios manuales por el equipo. |
| RF8 · Retroalimentación | Dos preguntas independientes por alerta en panel y por WhatsApp con ECO. El origen simulado o meteorológico queda visible en la bitácora. |
| RF9 · Administración | Fichas editables y recuperables por el agente, usuarios y planes, cola técnica, total de evaluaciones y utilidad reportada. |
| Modelo comercial | Publicación, reserva, cancelación y confirmación bilateral. Comisión del vendedor calculada en centavos. La aplicación registra operaciones del piloto y no procesa cobros. |

## Datos y decisiones del piloto

La consulta utiliza las coordenadas registradas, o el centro municipal si se hizo el alta por WhatsApp sin enviar ubicación. Los cultivos de una misma zona pueden experimentar condiciones distintas. Las fechas se interpretan en UTC−4. Las alertas históricas conservan el contexto; el panel principal vuelve a calcular el riesgo con el pronóstico vigente. Cuando falla el proveedor se indica el error y, si existe, se conserva el último registro identificado por su fecha. El escenario de prueba siempre lleva la etiqueta de simulación.

Los **umbrales son hipótesis configurables para demostrar el motor**, pendientes de revisión por variedad, altitud y etapa. En el código, la helada parte de 1 °C para papa y −1 °C para quinua; suma 1 °C en emergencia o floración. Los demás disparadores son lluvia diaria de al menos 25 mm, ráfaga de al menos 45 km/h, diferencia de mínimas sucesivas de al menos 8 °C, códigos WMO 96/99 y precipitación semanal menor de 3 mm. Un déficit semanal no establece un diagnóstico de sequía. La decisión agronómica requiere contrastar con observaciones locales.

Las fichas iniciales son orientaciones piloto NEXTECH. La ficha de papa incluye como referencia técnica el material FAO sobre agua y desarrollo de tubérculos. El panel permite registrar fuente y versión de las fichas revisadas. Para medir desempeño real, hacer seguimiento separado de observaciones de campo y evaluar también eventos que el sistema no alertó. El contador global incluye las demostraciones.

Fuentes de consulta:

- [Open-Meteo, variables, códigos meteorológicos y atribución](https://open-meteo.com/en/docs).
- [FAO, material sobre papa y agua](https://www.fao.org/4/i1127e/i1127e02.pdf).
- [FAO, quinua y contexto andino](https://www.fao.org/quinoa/en/).
- [Meta, WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/).
- [OpenAI, transcripción](https://developers.openai.com/api/docs/guides/speech-to-text).

## Arquitectura y uso de datos

`web/` contiene la interfaz en español, el logotipo del PDF y una ilustración original del altiplano. `app.py` expone la API REST y sirve el frontend. `agro.py` contiene las reglas y el conector climático. `core.py` coordina perfiles, recuperación, conversaciones y SQLite. `canal.py` procesa mensajes y tareas programadas. `mercado.py` registra las operaciones comerciales.

La base se crea en `datos/yapu.sqlite`. Cada navegador identifica su perfil mediante una cookie HttpOnly. Una sesión privada representa otro usuario. Las cuentas de WhatsApp utilizan su número y son independientes de la sesión web. El acceso de equipo usa una clave separada, conservada en memoria del navegador. En instalaciones expuestas, usa HTTPS, clave fija de equipo en el entorno y una sola instancia del planificador. La aplicación persiste datos mientras la carpeta o el volumen permanezcan disponibles.

La sincronización de mensajes es independiente de la actualización meteorológica. Al esperar cambios el servidor retiene la consulta del navegador hasta 18 segundos y contesta de inmediato al confirmar un mensaje o acuse. El cliente reconecta automáticamente. Las reglas agronómicas siguen siendo hipótesis del piloto.

## Pruebas y respaldo

Desde esta carpeta ejecuta `python -m unittest discover -s tests -v`. En Windows también sirve `py -3 -m unittest discover -s tests -v`. Las pruebas crean bases temporales, levantan una API local y usan dobles para proveedores externos. Incluyen reglas, aislamiento entre usuarios, cuotas, evaluación de alertas, autorización, derivación, webhook y comisión.

Para respaldar una instalación local en marcha usa `python respaldar.py`. Si cambiaste la ubicación en .env, indica `--origen RUTA/yapu.sqlite`. Para restaurar, detén el servidor, conserva una copia del directorio anterior y coloca el respaldo como `yapu.sqlite` en un directorio de datos vacío.

Consulta **INTEGRACIONES.md** para conectar servicios externos y preparar el despliegue.
