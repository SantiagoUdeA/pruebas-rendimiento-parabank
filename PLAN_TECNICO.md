# Plan técnico de pruebas de rendimiento de ParaBank

## 1. Propósito y alcance

El equipo implementará y ejecutará cinco simulaciones HTTP con Gatling para comprobar las historias no funcionales de inicio de sesión, transferencias, consulta de movimientos, solicitud de préstamo y pago de servicios. GitHub Actions ejecutará una comprobación ligera de los scripts en cada cambio y permitirá lanzar manualmente las pruebas de carga completas. La entrega académica incluirá evidencia de las ejecuciones y un video grupal de entre 10 y 15 minutos alojado en Drive, enlazado desde el Word.

Este documento es un plan. **No registra ejecuciones ni declara que los criterios se hayan cumplido.** Los valores de aceptación son los proporcionados en la actividad; los datos medidos se incorporarán después de ejecutar las simulaciones.

## 2. Entorno, límites y datos

- **Sistema bajo prueba:** una instancia aislada de ParaBank, con versión, capacidad de la máquina y configuración registrados. La API REST se configura mediante `BASE_URL`, por ejemplo `http://localhost:8080/parabank/services/bank`. Confirmar la ruta real con el contrato OpenAPI de la instancia antes de programar las llamadas.
- **No ejecutar la carga alta contra el sitio público.** Los escenarios de 150 transferencias por segundo y 200 usuarios requieren una instancia controlada. GitHub Actions utilizará un ejecutor propio conectado a esa instancia; el ejecutor hospedado por GitHub se limitará a compilar y a pruebas muy pequeñas.
- **Datos preparados:** usuarios de prueba, identificadores de cliente, cuentas de origen y destino distintas, saldo suficiente, beneficiarios y montos válidos. Separar conjuntos de datos por simulación y por ejecución para evitar interferencias. No subir contraseñas ni datos personales reales al repositorio; usar secretos de Actions o archivos locales ignorados por Git.
- **Estado inicial:** respaldar o recrear la base de datos de la instancia aislada antes de cada campaña. Registrar fecha, versión, tamaño de datos, número de cuentas y saldos de referencia. No usar endpoints administrativos de reinicio desde las simulaciones de carga.
- **Calibración:** ejecutar un smoke test de 1 a 5 usuarios por servicio, validar contrato y respuesta funcional; luego una prueba piloto breve para comprobar que el generador no satura CPU, memoria, red o puertos. Registrar uso del generador y del servidor.

## 3. Estructura propuesta del proyecto ejecutable

```text
parabank-rendimiento/
  pom.xml
  .github/workflows/performance.yml
  src/test/java/.../simulations/
    LoginSimulation.java
    TransferSimulation.java
    StatementSimulation.java
    LoanSimulation.java
    BillPaySimulation.java
  src/test/java/.../support/
    Environment.java
    Checks.java
  src/test/resources/data/
    users.example.csv
    transfers.example.csv
    payments.example.csv
  scripts/
    prepare-test-data.sh
    reconcile-transactions.py
  evidence/                 # metadatos y resúmenes sin datos sensibles
  entrega/
    Resumen_actividad_Parabank.docx
```

Usar Gatling Java con Maven Wrapper y fijar las versiones de Java, Gatling y del complemento Maven en `pom.xml`. Los archivos `.example.csv` contendrán datos ficticios; los CSV reales y los reportes HTML extensos quedarán fuera de Git y se conservarán como artefactos de cada ejecución. Agregar `.gitignore` para `target/`, resultados, CSV privados y credenciales.

## 4. Diseño de los cinco escenarios

Para las historias con *usuarios simultáneos* se usa un modelo cerrado, que mantiene una cantidad de usuarios virtuales activos. Para la historia con *transacciones por segundo* se usa un modelo abierto, que fija la tasa de llegada. Un usuario virtual puede realizar más de una operación; por ello se reportarán por separado usuarios activos, solicitudes emitidas y operaciones confirmadas. Los intervalos de medición serán de 5 minutos estables después de un calentamiento independiente de 1 minuto. Las pruebas de pico se ejecutarán aparte de las pruebas normales para que sus métricas no se mezclen.

| Historia | Servicio y operación HTTP | Inyección principal | Comprobación funcional y umbral |
|---|---|---|---|
| H1 Login | `GET /login/{username}/{password}` | `rampConcurrentUsers(0).to(100).during(60)` y `constantConcurrentUsers(100).during(300)`; una segunda corrida con 200 usuarios | Comprobar cliente autenticado y ausencia de errores. Tiempo máximo de la llamada ≤ 2.000 ms a 100 usuarios y ≤ 5.000 ms a 200 usuarios. Informar también media, p95 y p99. Evitar que usuario y contraseña aparezcan en nombres de petición, reportes o logs. |
| H2 Transferencias | `POST /transfer?fromAccountId=...&toAccountId=...&amount=...` | `constantUsersPerSec(165).during(300)` tras una corrida separada de calentamiento con `rampUsersPerSec`; un intento de transferencia por usuario virtual, ajustando la tasa si la capacidad del generador lo exige | Feeder CSV obligatorio. Alcanzar al menos 150 transferencias **confirmadas** por segundo durante la ventana estable, tanto en el promedio total como en cada bloque consecutivo de 10 segundos. Cero fallos y cero operaciones faltantes. Conciliar transacciones de origen y destino con el registro de intentos. |
| H3 Estado de cuenta | `GET /accounts/{accountId}/transactions` | `constantConcurrentUsers(200).during(300)`; ejecutar también un arranque brusco con `atOnceUsers(200)` como exploración de pico | Validar cuenta y lista de movimientos. Tiempo máximo ≤ 3.000 ms en la corrida de 200 usuarios; errores HTTP, de contrato y funcionales ≤ 1 %. |
| H4 Préstamo | `POST /requestLoan?customerId=...&amount=...&downPayment=...&fromAccountId=...` | `rampConcurrentUsers(0).to(150).during(60)` y `constantConcurrentUsers(150).during(300)` | Tiempo medio ≤ 5.000 ms; éxito funcional ≥ 98 %. Validar respuesta con estado de solicitud esperado; separar denegaciones bancarias previstas de errores de validación inesperados. Cero caídas del servicio. |
| H5 Pago de servicios | `POST /billpay?accountId=...&amount=...` con cuerpo `Payee` JSON | `constantConcurrentUsers(200).during(300)` tras rampa; usar `stressPeakUsers(200).during(60)` en una corrida exploratoria distinta | Tiempo máximo por pago ≤ 3.000 ms; errores funcionales ≤ 1 %. Conciliar cada pago con su movimiento en el historial y comprobar que no haya duplicados. |

**Lectura de los tiempos:** donde el criterio dice que el tiempo “debe ser” o “por transacción” ≤ un límite, se aplica al máximo medido en la ventana estable. H4 pide explícitamente un promedio y se evalúa con la media. Esta regla es estricta y puede fallar por un único valor atípico; el informe conservará también p95, p99 y contexto para explicar el resultado. Gatling permite aserciones por petición, pero la evaluación de la ventana estable y la conciliación de operaciones deben hacerse también con un verificador posterior sobre los resultados exportados.

## 5. Feeder y consistencia de transacciones

El CSV de transferencias tendrá, como mínimo, `caseId,customerId,fromAccountId,toAccountId,amount`. `caseId` identifica el intento en el registro del generador; ParaBank no ofrece en este contrato un identificador de idempotencia para `transfer`, por lo que no se hará reintento automático de operaciones financieras. Los pares de cuentas, montos y datos de referencia se prepararán de modo que la conciliación pueda distinguir cada intento. El feeder se barajará y se particionará por ejecutor si se usan varios generadores. Su tamaño debe cubrir todos los intentos de la corrida; si se agota, la prueba falla y no se interpreta como fallo de ParaBank.

Antes de la prueba se guardarán saldos y movimientos de referencia. Después, se contrastarán: número de intentos, número de respuestas satisfactorias, nuevos movimientos de débito y crédito, importes y saldos finales. Para pagos, se verificará exactamente un movimiento de pago por intento confirmado. Cuando el servicio no devuelva un identificador inequívoco, se usarán cuentas o importes exclusivos por caso y se documentará esa limitación de trazabilidad. Las consultas de conciliación se harán fuera de la ventana medida para no distorsionar el rendimiento.

## 6. Métricas, reglas y diagnóstico

- **Latencia:** tiempo de respuesta de la operación principal, en milisegundos, con media, máximo, p95 y p99. Separar la carga útil de preparación (login, consulta de cuentas) de la petición que evalúa cada historia.
- **Concurrencia y rendimiento:** usuarios activos reales, solicitudes por segundo, respuestas satisfactorias por segundo y transacciones confirmadas por segundo. La tasa de inyección de 165 usuarios/s no demuestra por sí misma 150 transacciones/s exitosas.
- **Errores:** respuestas HTTP inesperadas, comprobaciones de cuerpo fallidas, tiempo de espera, fallos de red y discrepancias de conciliación. Presentar numerador y denominador de cada porcentaje. La tasa de éxito de H4 se calcula como solicitudes funcionalmente aceptadas / solicitudes realizadas × 100; las denegaciones esperadas se reportan por separado y el conjunto de prueba debe diseñarse para solicitudes elegibles.
- **Estabilidad:** CPU, memoria, pausas de JVM, conexiones, uso de base de datos y saturación del generador. Si el generador es el cuello de botella, repetir la corrida con capacidad suficiente antes de emitir un veredicto.
- **Veredicto:** cada historia se aprueba solo si se cumplen **todos** sus criterios y las comprobaciones de integridad correspondientes. Una prueba sin datos suficientes, con feeder agotado o con entorno inestable se marca “no concluyente”, no “aprobada”.

## 7. Automatización en GitHub Actions

1. **En cada `push` y solicitud de cambio:** preparar Java y Maven, compilar los scripts, ejecutar validación estática y un smoke test pequeño contra la instancia aislada si el entorno está disponible. Publicar logs y reporte de Gatling como artefactos.
2. **Bajo `workflow_dispatch`:** elegir escenario (`login`, `transfer`, `statement`, `loan`, `billpay`, `all`) y perfil (`normal`, `peak`, `stress`). Ejecutar carga alta únicamente en `runs-on: [self-hosted, parabank-perf]`, con `concurrency` para impedir campañas simultáneas. Establecer límites de tiempo y valores de entrada permitidos.
3. **Configuración segura:** pasar `BASE_URL` y credenciales mediante variables y secretos del entorno; no imprimirlos. El flujo debe comprobar que el destino pertenece a la instancia aislada permitida antes de iniciar cualquier campaña.
4. **Resultado:** ejecutar una simulación por job o en secuencia para evitar interferencia; guardar `target/gatling`, metadatos de ambiente, conciliación y tabla de cumplimiento. Hacer que el job falle si fallan las aserciones o la conciliación. Subir artefactos incluso cuando la prueba falle, con período de retención definido.
5. **Trazabilidad:** asociar en cada ejecución el commit, el ID de Actions, el escenario, el perfil, la hora, los parámetros, los datos de prueba usados y el veredicto. No subir el video a Git.

## 8. Orden de trabajo y responsables del grupo

| Etapa | Trabajo | Evidencia de salida | Responsable sugerido |
|---|---|---|---|
| 1 | Confirmar contrato de la instancia, preparar entorno aislado y datos | Inventario de versión, URL, cuentas y estado inicial | Integrante 1 |
| 2 | Implementar login y estados de cuenta con perfiles cerrados | Scripts y smoke tests | Integrante 2 |
| 3 | Implementar transferencias, CSV y conciliación | Script, feeder de ejemplo y verificador | Integrante 3 |
| 4 | Implementar préstamos y pagos con comprobación funcional | Scripts, casos válidos y conciliación | Integrante 4 |
| 5 | Configurar GitHub Actions, ejecutar campañas y consolidar reportes | Corridas, artefactos, tabla de resultados y video | Integrante 5 |

Todos revisarán los cinco resultados y participarán en el video. Los responsables son una propuesta de reparto; se sustituyen por los nombres reales antes de entregar. Los cambios se guardarán en commits locales identificables, con el plan, la automatización, los scripts y el Word en el mismo repositorio. Se publicará el repositorio en GitHub cuando el grupo lo autorice y disponga de la instancia de prueba.

## 9. Evidencia y presentación en video

Para cada historia, conservar captura del perfil de inyección, enlace o ID de la ejecución, reporte de Gatling, métricas de la ventana estable, errores, resultado de conciliación y decisión de aprobación. La tabla final tendrá una fila por criterio, valor objetivo, valor medido, resultado y evidencia. No completar valores medidos antes de correr la prueba.

**Guion de 12 minutos:** 0:00–1:00 integrantes y objetivo; 1:00–2:00 entorno y datos; 2:00–4:00 perfiles de inyección y feeder CSV; 4:00–8:00 ejecución y reportes de los cinco servicios; 8:00–10:00 conciliación de transferencias y pagos; 10:00–11:30 GitHub Actions y artefactos; 11:30–12:00 tabla de cumplimiento y entrega. Ajustar la grabación para quedar entre 10 y 15 minutos. Verificar audio, legibilidad de cifras, participación del grupo y permisos de lectura del enlace de Drive. Pegar ese enlace en el Word y subir el Word a Ingenia cuando el video esté disponible.
