# Demostración integrada

1. Extrae el ZIP y ejecuta INICIAR_WINDOWS.bat. En Resumen identifica los cinco centros y dos entidades de referencia. Selecciona un marcador. En Parcelas abre Fuentes para mostrar la procedencia.
2. En Productores registra un titular autorizado con su comunidad. El teléfono es opcional. Abre la ficha para revisar su historial.
3. En Parcelas registra un terreno asociado a ese titular. Indica superficie real en hectáreas, coordenadas, cultivo, etapa y, si la conoces, altitud. El servidor conserva el alta antes de consultar el clima. Para un ensayo utiliza un nombre de prueba reconocible.
4. Abre Meteorología. Compara hora del dato, temperatura, humedad, dirección e intensidad del viento y precipitación. Actualiza la lectura y exporta el CSV. Una parcela nueva necesita su primera respuesta del proveedor; si la red está caída, continúa el recorrido con un predio precargado.
5. Revisa Riesgos. Cada regla que se cumple aporta variable, umbral, fecha y orientación. Si no se cumple ninguna regla, el resultado puede ser bajo. Las retrospectivas diarias corresponden a valores modelados anteriores, no acreditan que el sistema estuviera desplegado en esas fechas.
6. En Laboratorio selecciona una parcela con clima guardado. Elige Helada e intensidad 2. Compara mínima inicial y perturbada. El ensayo usa las mismas reglas del monitor.
7. Lee la notificación de prueba y pulsa Confirmar recepción de prueba. Reabre el ensayo guardado y muestra emisor lógico, destinatario identificado, hora de recepción en el buzón de prueba y acuse. El laboratorio mantiene su propia bitácora.
8. En Alertas observa los avisos calculados con datos del proveedor. Abre uno y acusa recibo. Las notificaciones del panel se deduplican por parcela, contexto, fenómeno y día. Los filtros del monitor de equipo permiten ver el cambio sin recargar.
9. Para WhatsApp, configura primero las credenciales y HTTPS según INTEGRACIONES.md. En una parcela propia, pulsa Vincular WhatsApp. El productor debe enviar ALTA y luego VINCULAR con el código desde su teléfono. La libreta de contactos por sí sola no autoriza el envío. Las referencias públicas no reciben mensajes en teléfonos.
10. Entra en Cuaderno, equipo y mercado para mostrar la comunicación entre productor y equipo. El login del equipo usa la clave de la consola. Puedes imprimir el resumen desde el dashboard.

La instalación no incluye teléfonos, contraseñas, conversaciones ni confirmaciones de productores reales. Los acuses de prueba aparecen únicamente después de ejecutar y confirmar un ensayo.

## Vista del productor en WhatsApp

En el menú principal pulsa **WhatsApp del productor**. Puedes abrir esta vista en una segunda pestaña del mismo navegador. Selecciona «Registrar papa en Viacha» y pulsa enviar. Consulta el pronóstico y observa la conversación persistente. Esta vista usa el perfil independiente de prueba y el procesador de mensajes que comparte con el webhook.

En el laboratorio de la primera pestaña evalúa una helada con intensidad 2. El aviso de prueba aparece en la conversación del productor. Pulsa **Confirmar recepción** y abre el ensayo guardado en el laboratorio para ver su acuse. Puedes repetirlo sin credenciales ni conexión externa.

Para abrir el cliente auténtico desde esta pantalla configura el número público del negocio en WA_PUBLIC_NUMBER además de las credenciales de Meta y el webhook HTTPS. El botón enlaza a ese número. Los mensajes escritos en la vista de prueba permanecen en el servidor del piloto.
