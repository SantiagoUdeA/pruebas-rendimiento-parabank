# ParaBank Rendimiento

Harness Gatling para medir login, transferencias, consulta de movimientos, solicitudes de préstamo y pago de servicios en una instancia ParaBank aislada. El repositorio contiene los scripts, la instancia local y los criterios. Hay resultados de smoke funcional de bajo volumen; las campañas de aceptación de carga alta siguen pendientes.


## Instancia local aislada de ParaBank

El repositorio incluye `compose.yaml`, que despliega la imagen oficial `parasoft/parabank` fijada por digest. La imagen ya fue descargada en esta máquina. Compose publica únicamente el puerto web en `127.0.0.1:8080`; los puertos internos de HSQLDB y JMS no se publican. La base vive dentro del contenedor y se descarta al recrearlo.

```sh
scripts/parabank-up.sh
scripts/reset-local-parabank-db.sh  # opcional: reinicia la base demo aislada
scripts/prepare-parabank-local-data.py
```

La API local quedó confirmada en `http://127.0.0.1:8080/parabank/services/bank`, con OpenAPI 3.0.0. La imagen inicia una base vacía; `initializeDB` se llama solo desde `scripts/reset-local-parabank-db.sh`, fuera de las simulaciones. El resumen de la corrida smoke local está en `evidence/local-smoke-summary.md`. Los feeders locales generados usan la cuenta demo ficticia `john`/`demo` y cuentas creadas por ParaBank; los CSV están ignorados por Git. Para detener la instancia use `docker compose down`; para empezar con base vacía, baje y recree el servicio y vuelva a ejecutar `initializeDB` antes de generar feeders.

`BASE_URL=http://127.0.0.1:8080/parabank/services/bank`, `ALLOWED_HOSTS=127.0.0.1` y `PROFILE=smoke` permiten ejecutar el smoke local. No ejecute perfiles `normal`, `peak` o `stress` contra otra dirección que no sea esta instancia desechable.

## Requisitos y configuración

Se requiere Java 21. El Maven Wrapper descarga Maven la primera vez. Copie `.env.example` como `.env` para su entorno local, configure `BASE_URL` con la ruta API `/parabank/services/bank` y limite `ALLOWED_HOSTS` a los nombres privados de su instancia. No apunte pruebas de carga a `parabank.parasoft.com` ni a otra instalación pública.

Copie el feeder correspondiente de `src/test/resources/data/*.example.csv` a su homónimo `.csv` y reemplace los datos con identidades ficticias y cuentas preparadas para pruebas. Los `.csv` privados están ignorados por Git. Los datos de login se manejan mediante `users.csv`; use secretos locales/Actions, nunca credenciales reales. Para el runner de GitHub Actions configure los secretos `USERS_CSV`, `TRANSFERS_CSV`, `STATEMENTS_CSV`, `LOANS_CSV` y `PAYMENTS_CSV` con el contenido CSV completo. Configure las variables `BASE_URL` y `ALLOWED_HOSTS` en el entorno protegido `parabank-isolated`.

Ejemplo de ejecución local (cargue las variables desde su `.env` sin imprimirlas):

```sh
set -a; . ./.env; set +a
./mvnw -B test-compile
./mvnw gatling:test -Dgatling.simulationClass=com.parabank.perf.simulations.LoginSimulation
```

Los perfiles admitidos son `smoke`, `normal`, `peak` y `stress`. Smoke queda limitado a 5 usuarios, 5 solicitudes/s y 60 segundos. La campaña normal mantiene los perfiles del plan; `peak` activa los picos en estado de cuenta y pagos. Ajuste las variables solo en el entorno aislado. Una simulación por ejecución evita mezclar resultados. El feeder de transferencias debe cubrir la rampa y los cinco minutos estables: al menos 54.450 filas a 165 llegadas/s, con margen adicional.

## Contrato de API de la imagen fijada

La instancia local publica OpenAPI 3.0.0 en `/parabank/services/bank/openapi.json`. Se confirmaron login por `GET /login/{username}/{password}`, transferencias, movimientos, préstamos y `billpay` con `Payee` JSON y `address` como objeto; el smoke local recorrió las cinco operaciones. Si actualiza el digest de la imagen, inspeccione el OpenAPI y vuelva a validar con uno a cinco usuarios. El endpoint coloca las credenciales en la ruta; los nombres de petición de Gatling están saneados, pero la aplicación bajo prueba puede registrar la URL. En entornos que registran rutas completas, desactive/anonimice esos logs antes de utilizar credenciales de prueba.

## GitHub Actions

Push y pull request compilan los scripts y revisan el verificador sin llamar a ParaBank. `workflow_dispatch` solo usa un runner propio con etiquetas `self-hosted, parabank-perf`, el entorno protegido `parabank-isolated`, una lista cerrada de simulaciones/perfiles y una comprobación de destino privado. Los reportes y metadatos se cargan aunque falle una corrida; no se cargan CSV privados. Mantenga campañas separadas y configure la protección/aprobación del entorno en GitHub.

## Conciliación

`scripts/evaluate-transfer-throughput.py` comprueba el promedio y cada bloque de 10 segundos de la ventana estable de H2, excluyendo la rampa de 60 segundos. La campaña normal usa una rampa de 60 segundos y luego 300 segundos a 165 llegadas/s. `scripts/reconcile-transactions.py` consume el registro local de intentos (incluye `caseId`, estado, monto, hora y cuentas) y una exportación de movimientos `entryType,accountId,amount`, con `caseId` opcional. Si la exportación no trae caseId, las combinaciones de cuenta, tipo e importe deben ser únicas para evitar correlaciones ambiguas. Para transferencias requiere un débito en origen y un crédito en destino; para pagos, un débito en la cuenta pagadora. No se afirma una conciliación exitosa hasta revisar esta exportación. Como ParaBank no define una clave idempotente para las operaciones financieras, no se reintentan pagos ni transferencias. Si no se pueden correlacionar los movimientos de forma inequívoca, el resultado debe registrarse como no concluyente.

## Estado de entrega

La instancia local está desplegada; las cinco simulaciones smoke pasaron y se conciliaron transferencias y pagos de esa corrida de bajo volumen. Los resultados están en `evidence/local-smoke-summary.md`. Falta preparar una población de datos elegible para concurrencia alta, ejecutar las campañas normales y de pico, capturar métricas completas y completar integrantes y enlace del video en el Word de entrega.
