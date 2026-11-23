# Entrega técnica por módulo

Todos los módulos se ejecutan en el mismo proceso Python 3.10+ mediante app.py. SQLite persiste los cambios. Los cinco componentes se conectan por llamadas transaccionales internas y exponen las operaciones web enumeradas en API.md. El código fuente está en la carpeta raíz junto a web, catalogo, tests y docs. Para evaluar una parte individual se puede ejecutar su prueba con el comando indicado desde la raíz.

| Integrante | Código y recursos entregados | Evidencia reproducible |
|---|---|---|
| 1 · Interfaz | web/atlas.html, atlas.css, atlas.js. Navegación por siete módulos, tarjetas y tablas reutilizables, formularios, mapas Leaflet locales, impresión, CSV y adaptación móvil. web/app.js y ops.js conservan el cuaderno y el monitor de equipo. | Abrir la aplicación. Navegar a cada vista. Pasar de ancho escritorio a 390 px. En el dashboard seleccionar un marcador y comparar su nombre con la selección meteorológica. |
| 2 · Catastro | atlas.py administra productores, asociación uno a varios, validaciones, eventos y desactivación. core.py y operaciones.py implementan acceso transaccional, propiedad de sesión, perfil y migraciones aditivas. | python -m unittest discover -s tests -p test_atlas.py -v. Casos de aislamiento, registro, superficie inválida, cambios y desactivación asociada. |
| 3 · Clima | agro.py consulta por coordenadas y valida las variables. operaciones.sample actualiza la última lectura. atlas.readings conserva la serie. catalogo/actualizar.py descarga las respuestas de referencia y cataloga su procedencia. | Pruebas de proveedor, caché, falla y conservación de captura en test_sistema.py y test_operaciones.py. En Meteorología se puede exportar el historial. |
| 4 · Riesgos | agro.risks evalúa heladas, calor, aire seco, granizo, viento, lluvia intensa, déficit semanal y cambio brusco. atlas.simulate aplica perturbaciones graduables. atlas.detail expone la evidencia e historial. | En test_atlas.py se prueban las seis perturbaciones. La notificación del ensayo se registra por separado de los avisos de campo. |
| 5 · Alertas e integración | core.evaluate vincula umbral, parcela, contexto, fecha y aviso. operaciones.py gestiona acuse y actualización de paneles. canal.py implementa planificador, webhook firmado, plantillas, vinculación con consentimiento, estados y reintentos. | test_operaciones.py y test_atlas.py cubren publicación, cambio de estado, recepción, deduplicación, consumo del código de vínculo y clima → riesgo → notificación. Simulación verificable en Laboratorio. |

## Fuentes y frecuencia

- **Open-Meteo Forecast** suministra condiciones actuales de modelo y horizonte diario para coordenadas de Bolivia. La captura incluida conserva la URL de consulta, unidades, fechas de validez del modelo y fecha de obtención. Se solicitan siete días anteriores por hora y siete días de pronóstico. La consulta ordinaria refresca el valor actual y los siete días futuros. https://open-meteo.com/en/docs
- **GFS mediante Open-Meteo** es el respaldo de modelo ante un error de conexión con el primer endpoint. Comparte infraestructura con el proveedor principal. Frente a una caída del proveedor completo se conserva la captura local fechada. https://open-meteo.com/en/docs/gfs-api
- **MET Norway Locationforecast** es una alternativa de proveedor independiente con interfaz y variables diferentes; requiere identificación del cliente y adaptación de agregaciones. Se investigó como opción de expansión. https://api.met.no/weatherapi/locationforecast/2.0/documentation
- El planificador revisa cada diez minutos aproximadamente mientras el proceso esté activo. La malla, la frecuencia de emisión del modelo y el relieve condicionan la representatividad del dato. Registros históricos horarios procedentes de modelos no equivalen a mediciones de una estación física.
- El catálogo de predios y las fuentes de cada coordenada/cultivo están en catalogo/predios.json y en Parcelas → Fuentes. La altitud publicada de un predio puede diferir de la altitud de la celda meteorológica. La superficie de Patacamaya corresponde a toda la estación.
- El usuario puede ejecutar python catalogo/actualizar.py con internet para regenerar el conjunto distribuible de capturas. El script reemplaza el JSON solo cuando terminan todas las consultas. Espacios existentes se mantienen mediante el planificador y la actualización manual.

## Criterios del piloto

La mínima de referencia de helada en °C es 1 para papa/haba, −1 para quinua, 0 para cebada y 2 para maíz. Para los demás cultivos se aplica el umbral general de 1. Emergencia y floración añaden 1 °C. El umbral de calor varía entre 29 y 36 °C según cultivo (32 °C general). Los umbrales de lluvia ≥25 mm/día, ráfagas ≥45 km/h, humedad del aire <25 %, salto de mínima ≥8 °C y total previsto <3 mm en siete días son parámetros experimentales. El granizo depende de códigos 96/99. Aire seco, déficit semanal y salto térmico se clasifican como medios; los restantes avisos, como altos. Se informa riesgo bajo al contar con datos vigentes sin disparadores. Sin datos vigentes se identifica el último registro o la ausencia de lectura.

La humedad del aire se interpreta de manera distinta de la humedad del suelo. La bibliografía de referencia sobre sensibilidad de papa al agua está indicada en LEEME.md. Para estudiar las reglas en campo hacen falta observaciones, revisión técnica y calibración local. La misma precaución se aplica al predio de Cota Cota donde la producción documentada incluye invernaderos.

## Datos y esquema

docs/schema_postgresql_original.sql conserva el esquema del equipo, con UUID, roles y extensiones PostgreSQL. El prototipo ejecutable utiliza SQLite. El espacio web se identifica por una cookie; el equipo tiene acceso mediante su clave. El índice de búsqueda de fichas se implementa en Python con TF-IDF.

| Entidad del SQL | Implementación operativa |
|---|---|
| productores / parcelas | productores guarda titular, contacto y zona; parcelas enlaza al productor con el perfil de terreno en users y añade superficie, altitud, características y estado. |
| registros_clima | registros_clima contiene fuente, fecha, temperatura, humedad, precipitación, viento y dirección. meteo conserva además probabilidades y pronósticos diarios. |
| evaluaciones_riesgo | evaluaciones conserva resultado por parcela, validez y contexto. ensayos y envios_prueba guardan experimentos y acuses de prueba. |
| alertas / bitacora_mensajes | alerts, timeline, receipts y envios_fallidos conservan aviso, publicación, solicitud y confirmación del proveedor. enlaces vincula un número dado de alta mediante código de un solo uso y vencimiento. |
| contenidos, métricas y eventos | knowledge, auditoria, chats y consultas agregadas de panel. |

Las tablas se crean automáticamente. Las relaciones con claves foráneas se aplican en cada conexión. Un identificador numérico público de parcela se comprueba contra su propietario antes de autorizar la operación. Para una instalación existente se recomienda respaldar primero; ver LEEME.md. El entorno Docker incluye código y catálogo.
