# Plan técnico para ejecutar Gatling en GitHub Actions

## 1. Resultado esperado

El grupo ejecutará desde la pestaña **Actions** cinco simulaciones de Gatling contra una instancia aislada de ParaBank. Cada ejecución conservará el reporte HTML, las métricas de aceptación, el resultado de conciliación de transferencias y pagos, y un veredicto por historia. El flujo fallará si se incumple un criterio o si falta evidencia para evaluarlo. Este documento describe la implementación pendiente; no contiene resultados de pruebas ya realizadas.

## 2. Decisión de arquitectura

Se crearán dos archivos de flujo en el repositorio de la actividad:

| Archivo | Activador | Ejecutor | Función |
|---|---|---|---|
| `.github/workflows/validacion.yml` | `push` y `pull_request` | GitHub hospedado | Compilar los scripts, comprobar el formato de datos de ejemplo y ejecutar pruebas sin carga alta. No se conecta a cuentas reales ni inicia campañas. |
| `.github/workflows/rendimiento.yml` | `workflow_dispatch` | Ejecutor propio con etiqueta `parabank-perf` | Lanzar una simulación de carga por vez, verificar resultados y publicar evidencia. Solo acepta parámetros enumerados. |

El repositorio de trabajo será privado y el ejecutor propio estará dedicado a esta actividad. La máquina del ejecutor y la instancia de ParaBank pueden ser distintas; se debe comprobar conectividad entre ambas y registrar la latencia de red. El ejecutor debe disponer de Java, conectividad saliente a GitHub, capacidad suficiente para generar la carga y acceso a la URL interna de ParaBank. Las campañas de 150 transferencias por segundo o 200 usuarios no se dirigen al sitio público de demostración.

## 3. Preparación antes de escribir el flujo

1. Crear la instancia aislada de ParaBank y anotar la URL REST interna, versión, CPU, memoria y base de datos. Cargar usuarios y cuentas de prueba con saldos suficientes.
2. Crear el proyecto Gatling Java con `pom.xml`, Maven Wrapper, cinco clases de simulación y feeders de ejemplo. Fijar las versiones del JDK, Gatling, complemento Maven y acciones usadas por el flujo.
3. Configurar cada simulación para leer `BASE_URL`, `PROFILE` y los datos necesarios desde variables de entorno o archivos privados. Usar nombres de petición fijos para que los reportes no muestren contraseñas incluidas en la ruta de login.
4. Añadir scripts de preparación, validación de datos y conciliación. El verificador debe comparar intentos, respuestas, movimientos y saldos antes de emitir el veredicto.
5. Probar localmente cada clase con pocos usuarios mediante `./mvnw gatling:test -Dgatling.simulationClass=<clase_completa>`. Confirmar que el reporte aparece en `target/gatling/`.
6. Registrar el ejecutor propio en el repositorio o en un grupo restringido; asignarle la etiqueta `parabank-perf`. No permitir que ejecute código de solicitudes de cambio no confiables. Comprobar Java, Maven Wrapper, espacio libre, reloj y conectividad antes de una campaña.

## 4. Configuración del repositorio en GitHub

En **Settings → Secrets and variables → Actions**, configurar la URL y las credenciales de prueba sin versionarlas. Usar una variable `PARABANK_BASE_URL` para la URL interna y secretos para credenciales. Si el plan de GitHub permite entornos en el repositorio privado, crear `parabank-perf` y restringir las ramas autorizadas; una revisión requerida puede añadirse cuando esté disponible. La protección del entorno no reemplaza el aislamiento del ejecutor.

Configurar `GITHUB_TOKEN` con permiso mínimo `contents: read`. El flujo no necesita permiso de escritura para publicar artefactos de la propia ejecución. Limitar quién puede editar los flujos y lanzar pruebas de carga. No imprimir contraseñas, URL de login completa, CSV privados ni cuerpos de respuesta con datos sensibles. Antes de publicar artefactos, revisar que los logs y reportes no los incluyan.

El archivo `rendimiento.yml` debe estar en la rama predeterminada para que aparezca el botón **Run workflow**. El equipo seleccionará una referencia aprobada y registrará el SHA exacto ejecutado. No se ejecutará automáticamente con `push`, cron ni solicitudes de cambio.

## 5. Entradas y validación del flujo manual

| Entrada | Valores permitidos | Uso |
|---|---|---|
| `scenario` | `login`, `transfer`, `statement`, `loan`, `billpay`, `all` | Selecciona una clase o las cinco en orden. |
| `profile` | `normal`, `peak`, `stress` | Selecciona la carga definida en código; no acepta cantidades arbitrarias. |
| `run_label` | Texto corto sin datos sensibles | Identifica la campaña en el artefacto y en el video. |

El primer paso del job validará que la combinación sea aplicable: login tiene `normal` y `peak`; transferencias usa `stress`; las demás usan el perfil que corresponda a su historia. `all` ejecutará los cinco casos uno tras otro, con preparación y conciliación separadas. Si una combinación no aplica, el flujo terminará antes de contactar ParaBank. Se añadirá `concurrency` con un grupo fijo para la instancia de prueba y `cancel-in-progress: false` y `queue: max`, de modo que no se solapen campañas, no se corte una prueba financiera y las nuevas solicitudes esperen turno. También se fijará un tiempo máximo por job.

## 6. Secuencia del job de carga

1. **Obtener código:** usar `checkout` en la referencia seleccionada y registrar SHA, número de ejecución, fecha y entradas.
2. **Preparar Java:** usar la versión fijada y caché Maven; comprobar que `./mvnw` y las dependencias funcionen en modo no interactivo.
3. **Verificar destino:** validar que `PARABANK_BASE_URL` coincide con el host interno permitido, comprobar conectividad y rechazar explícitamente el dominio público de ParaBank.
4. **Preparar datos:** restaurar o recrear el estado de la instancia aislada mediante un procedimiento controlado, fuera de la ventana medida. Confirmar número suficiente de usuarios, cuentas, saldo y filas del feeder. Guardar un resumen sin credenciales.
5. **Calentamiento:** ejecutar una simulación breve y separada. Si falla la salud del servicio o el generador, no continuar con la prueba principal.
6. **Carga principal:** ejecutar una clase concreta con `./mvnw -B gatling:test -Dgatling.simulationClass=<clase_completa>` y `PROFILE` definido. En el caso `all`, repetir secuencialmente con un directorio de resultados independiente por escenario. No ejecutar los cinco escenarios a la vez.
7. **Validar:** leer los resultados de Gatling y calcular los umbrales sobre la ventana estable de cinco minutos. Para transferencias, comprobar al menos 150 operaciones confirmadas por segundo en promedio y en cada bloque de diez segundos. Conciliar transferencias y pagos con movimientos y saldos.
8. **Publicar evidencia:** generar `summary.json`, `summary.md` y una tabla con objetivo, valor medido y veredicto para cada criterio. Ejecutar este paso con `if: always()` para conservar reportes HTML, metadatos de entorno y conciliación aunque Gatling falle; si no hay archivos, registrar el motivo.
9. **Cerrar:** combinar el resultado de Gatling con la evaluación posterior y devolver código de salida distinto de cero ante fallos reales. Marcar “no concluyente” cuando falten datos, se agote el feeder o el generador esté saturado. Guardar el enlace de la ejecución para el Word y el video.

## 7. Correspondencia entre escenario y evidencia

| Escenario | Perfil de inyección | Validación que decide el job |
|---|---|---|
| Login normal y pico | `rampConcurrentUsers` seguido de `constantConcurrentUsers` | 100 usuarios con máximo ≤ 2 s; 200 usuarios con máximo ≤ 5 s. |
| Transferencias | Calentamiento con `rampUsersPerSec`; medición con `constantUsersPerSec` | ≥ 150 transferencias confirmadas/s; cero fallos y cero operaciones faltantes; feeder CSV. |
| Estado de cuenta | `constantConcurrentUsers(200)`; exploración adicional con `atOnceUsers(200)` | Máximo ≤ 3 s y errores ≤ 1 % en la prueba de concurrencia. |
| Préstamos | `rampConcurrentUsers` hasta 150 y meseta de concurrencia | Promedio ≤ 5 s, éxito ≥ 98 %, sin validaciones inesperadas ni caída del servicio. |
| Pago de servicios | `constantConcurrentUsers(200)`; pico exploratorio con `stressPeakUsers` | Máximo ≤ 3 s, errores funcionales ≤ 1 % y exactamente un movimiento por pago confirmado. |

Las aserciones de Gatling cubrirán latencia y errores por petición. La comprobación de rendimiento sostenido, las reglas de ventana estable y la integridad de las operaciones se ejecutarán en un paso posterior; el reporte HTML por sí solo no prueba que no haya pérdidas o duplicaciones.

## 8. Artefactos y criterios de finalización

El artefacto de cada ejecución tendrá un nombre del tipo `parabank-<run_id>-<scenario>-<profile>` y contendrá:

```text
metadata.json              # SHA, fecha, runner, versión, URL anonimizada y perfil
summary.md                 # tabla de aceptación y veredicto
summary.json               # métricas legibles por herramientas
reports/<scenario>/...     # reportes HTML de Gatling
reconciliation/...         # conteos, diferencias y saldos sin datos sensibles
```

Configurar un período de retención explícito para los artefactos y subirlos con un paso condicionado a ejecución previa, aunque Gatling falle. El job se considera **aprobado** solo si sus umbrales, comprobaciones funcionales y conciliación pasan. Se considera **fallido** si uno de esos controles falla. Se considera **no concluyente** si no hubo carga válida o la medición quedó afectada por el entorno; el flujo terminará en estado de fallo para impedir que se interprete como cumplimiento.

Para demostrar la actividad, el grupo debe conservar cinco ejecuciones válidas como mínimo, una por servicio, y mostrar en el video la pantalla de Actions, los parámetros elegidos, el estado de cada job, los reportes y la tabla de veredictos. El enlace de Drive y los nombres de los cinco integrantes se incorporarán después al Word de entrega. El video durará entre 10 y 15 minutos.

## 9. Cómo lanzar y revisar una ejecución

Una vez publicados los flujos y verificada la instancia, entrar en **Actions → Rendimiento ParaBank → Run workflow**. Elegir la rama aprobada, `scenario`, `profile` y una etiqueta breve. Para la demostración, iniciar `all` o lanzar los cinco escenarios por separado. Esperar la finalización del job; una ejecución en cola o a la espera de aprobación todavía no constituye una prueba realizada. Abrir el job, revisar la etapa de validación y descargar el artefacto. Abrir `summary.md` y el reporte `index.html` de cada escenario; contrastar el veredicto con la conciliación. Copiar la URL de la ejecución y anotar el SHA mostrado por Actions.

Si el job queda pendiente, comprobar que el ejecutor `parabank-perf` esté en línea, que la etiqueta coincida y que no haya otra campaña usando el grupo de concurrencia. Si falla la conectividad, corregir la URL interna o la red del ejecutor. Si Gatling falla antes de medir, revisar datos y logs sanitizados; no convertir esa corrida en resultado de rendimiento. Si falla una aserción, conservar el artefacto y registrar el criterio incumplido sin editar los valores observados.

## 10. Orden de implementación y comprobación

| Paso | Entregable | Comprobación antes de avanzar |
|---|---|---|
| 1 | Instancia aislada y ejecutor propio | Host permitido, conectividad y capacidad del generador. |
| 2 | Scripts Gatling y datos | Cinco smoke tests locales y feeder CSV suficiente. |
| 3 | `validacion.yml` | Compilación correcta en `push` y solicitud de cambio sin carga alta. |
| 4 | `rendimiento.yml` | Botón **Run workflow**, entradas enumeradas, serialización y publicación de artefactos. |
| 5 | Campaña piloto | Una ejecución pequeña con reporte, resumen y conciliación. |
| 6 | Campaña completa | Cinco ejecuciones válidas, veredictos y evidencia revisada. |
| 7 | Entrega | Video de 10 a 15 minutos, enlace funcional en Word y nombres completos. |
