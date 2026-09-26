# ParaBank Rendimiento

Harness Gatling para medir login, transferencias, consulta de movimientos, solicitudes de préstamo y pago de servicios en una instancia ParaBank aislada. El repositorio contiene los scripts, la instancia local y los criterios. Los cinco escenarios tienen verificación de extremo a extremo (aserciones de Gatling, cuadre de las operaciones financieras contra el historial del banco y tabla de cumplimiento); las campañas de aceptación de carga alta siguen pendientes.


## Instancia local aislada de ParaBank

El repositorio incluye `compose.yaml`, que despliega la imagen oficial `parasoft/parabank` fijada por digest. La imagen ya fue descargada en esta máquina. Compose publica únicamente el puerto web en `127.0.0.1:8080`; los puertos internos de HSQLDB y JMS no se publican. La base vive dentro del contenedor y se descarta al recrearlo.

```sh
scripts/parabank-up.sh
scripts/reset-local-parabank-db.sh  # opcional: reinicia la base demo aislada
scripts/prepare-parabank-local-data.py
```

La API local quedó confirmada en `http://127.0.0.1:8080/parabank/services/bank`, con OpenAPI 3.0.0. La imagen inicia una base vacía; `initializeDB` se llama solo desde `scripts/reset-local-parabank-db.sh`, fuera de las simulaciones. El resumen de la corrida smoke local está en `evidence/local-smoke-summary.md` y la verificación de los pasos de carga está en `evidence/local-campaign-summary.md`. Para detener la instancia use `docker compose down`; para empezar con base vacía, baje y recree el servicio y vuelva a ejecutar `initializeDB` antes de generar feeders.

`scripts/prepare-parabank-local-data.py` no inventa datos: primero pregunta a la API qué clientes y cuentas existen (`/customers/{id}/accounts`), se queda solo con cuentas CHECKING/SAVINGS y, para el feeder de estados de cuenta, solo con cuentas que ya tienen movimientos. Los CSV se escriben ignorados por Git. `BASE_URL=http://127.0.0.1:8080/parabank/services/bank`, `ALLOWED_HOSTS=127.0.0.1` y `PROFILE=smoke` permiten ejecutar el smoke local. No ejecute perfiles `normal`, `peak` o `stress` contra otra dirección que no sea esta instancia desechable.

## Requisitos y configuración

Se requiere Java 21. El Maven Wrapper descarga Maven la primera vez. Copie `.env.example` como `.env` para su entorno local, configure `BASE_URL` con la ruta API `/parabank/services/bank` y limite `ALLOWED_HOSTS` a los nombres privados de su instancia. No apunte pruebas de carga a `parabank.parasoft.com` ni a otra instalación pública.

Los `.csv` de `src/test/resources/data/*.example.csv` solo muestran el formato; los archivos que usan las simulaciones se generan con `scripts/prepare-parabank-local-data.py` a partir de las cuentas que la instancia local expone de verdad, y están ignorados por Git. Si prefiere rellenar los CSV a mano, copie el ejemplo a su homónimo `.csv` y use siempre identidades ficticias y cuentas de la instancia desechable, nunca credenciales reales. El flujo de GitHub Actions no necesita secretos: solo las variables `BASE_URL` y `ALLOWED_HOSTS`, que apuntan al ParaBank del propio runner.

Ejemplo de ejecución local (cargue las variables desde su `.env` sin imprimirlas):

```sh
set -a; . ./.env; set +a
./mvnw -B test-compile
./mvnw gatling:test -Dgatling.simulationClass=com.parabank.perf.simulations.LoginSimulation
```

Los perfiles admitidos son `smoke`, `normal`, `peak` y `stress`. Smoke queda limitado a 5 usuarios, 5 solicitudes/s y 60 segundos. La campaña normal mantiene los perfiles del plan; `peak` activa los picos en estado de cuenta y pagos. Ajuste las variables solo en el entorno aislado. Una simulación por ejecución evita mezclar resultados.

`scripts/run-scenario.sh <Clase> <perfil>` es el driver que usan GitHub Actions y las corridas locales: reinicia la base, prepara los feeders, toma una foto del historial, ejecuta la simulación, exporta el historial nuevo y cuadra las operaciones. Los feeders usan `.circular()`, así que la corrida no se rompe al repetirse el CSV; el tamaño de `TRANSFER_ROWS`, `PAYMENT_ROWS` y `LOAN_ROWS` se ajusta con variables de entorno.

Los escenarios de modelo cerrado (H1, H3, H4, H5) tienen tiempo de espera entre operaciones, `PAUSE_SECONDS` y `LOAN_PAUSE_SECONDS`. Sin esa espera, 200 usuarios con respuestas de milisegundos generarían decenas de miles de peticiones por segundo y medirían un sistema ya colapsado en lugar del que el servicio sostiene con 200 usuarios simultáneos.

## Contrato de API de la imagen fijada

La instancia local publica OpenAPI 3.0.0 en `/parabank/services/bank/openapi.json`. Se confirmaron login por `GET /login/{username}/{password}`, transferencias, movimientos, préstamos y `billpay` con `Payee` JSON y `address` como objeto; el smoke local recorrió las cinco operaciones. Si actualiza el digest de la imagen, inspeccione el OpenAPI y vuelva a validar con uno a cinco usuarios. El endpoint coloca las credenciales en la ruta; los nombres de petición de Gatling están saneados, pero la aplicación bajo prueba puede registrar la URL. En entornos que registran rutas completas, desactive/anonimice esos logs antes de utilizar credenciales de prueba.

## GitHub Actions

Push y pull request levantan la imagen oficial fijada por digest en el runner hospedado por GitHub, inicializan una base desechable, preparan datos ficticios y ejecutan los cinco smoke tests de Gatling. El flujo manual permite elegir un servicio o todos y el perfil `smoke`, `normal`, `peak` o `stress`; los perfiles de carga alta usan la misma instancia ParaBank local del runner y reinician su base antes de cada servicio. No requiere secretos ni un ejecutor propio. Cada escenario se ejecuta con `scripts/run-scenario.sh`, que además valida el destino, exporta el historial del banco y cuadra las operaciones; `scripts/build-summary.py` arma `evidence/runs/summary.md` con el objetivo, el valor medido y el veredicto de cada criterio, y el job termina en rojo si un criterio o una conciliación fallan. Gatling HTML, la salida de consola, el cuadre, los metadatos y los logs del contenedor se guardan como artefactos incluso si una aserción falla. Los resultados de los runners hospedados son útiles para repetir pruebas, pero su capacidad compartida no sustituye una medición controlada para certificar límites de rendimiento.

## Conciliación

`scripts/evaluate-transfer-throughput.py` comprueba el promedio y cada bloque de 10 segundos de la ventana estable de H2, excluyendo la rampa de 60 segundos. La campaña normal usa una rampa de 60 segundos y luego 300 segundos a 165 llegadas/s. `scripts/reconcile-transactions.py` consume el registro local de intentos (incluye `caseId`, estado, monto, hora y cuentas) y una exportación de movimientos `entryType,accountId,amount`, con `caseId` opcional. Si la exportación trae `caseId`, se valida cada intento individualmente. Sin esa columna, el verificador compara los conteos por cuenta, tipo e importe como multiconjunto: detecta filas faltantes o duplicadas, aunque no permite atribuir una diferencia a un intento específico cuando varias operaciones comparten esos valores. Para transferencias requiere un débito en origen y un crédito en destino; para pagos, un débito en la cuenta pagadora. No se afirma una conciliación exitosa hasta revisar esta exportación. Como ParaBank no define una clave idempotente para las operaciones financieras, no se reintentan pagos ni transferencias. Si no se pueden correlacionar los movimientos de forma inequívoca, el resultado debe registrarse como no concluyente.

## Estado de entrega

Los cinco escenarios quedaron verificados de extremo a extremo: feeders derivados de las cuentas que la API realmente expone, sin agotamiento en las campañas de carga, conciliación automática de transferencias y pagos, y tabla de cumplimiento generada desde las mediciones. Las corridas locales de verificación están en `evidence/local-campaign-summary.md` y la de humo en `evidence/local-smoke-summary.md`. H4 queda con un hallazgo abierto: ParaBank rechaza entre el 1 % y el 6 % de las solicitudes de préstamo concurrentes con HTTP 400 `Could not find account`, y el criterio de 98 % de éxito se cumple a ~10 req/s pero no a ~27 req/s. Falta ejecutar la campaña formal de 5 minutos por historia, capturar los reportes de las ejecuciones en Actions y completar integrantes y enlace del video en el Word de entrega.
