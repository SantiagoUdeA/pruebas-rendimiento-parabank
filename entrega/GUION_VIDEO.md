# Guion del video — Laboratorio 2 de pruebas de software

**Duración objetivo: 13 minutos** (rango permitido 10–15). El tiempo entre corchetes es la marca
sugerida; si se van de tiempo, lo que no se puede recortar es la demo de los cinco escenarios
(minutos 4:00 a 9:30) y la conciliación (9:30–10:30).

El video se graba **después** de lanzar la campaña real en GitHub Actions. Durante la grabación se
muestra la evidencia de esa campaña como artefacto y se ejecuta en vivo una corrida corta, no la
campaña completa de 40 minutos.

---

## 0. Antes de grabar

Lista de verificación. Todo debe estar listo 15 minutos antes.

- [ ] Docker corriendo: `docker info` no falla.
- [ ] Imagen de ParaBank ya descargada: `docker compose -f compose.yaml pull`.
- [ ] Dependencias de Maven descargadas: `./mvnw -B -ntp test-compile` (la primera descarga tarda).
- [ ] ParaBank arriba: `scripts/parabank-up.sh` y `curl` a `/customers/12212/accounts` responde.
- [ ] Terminal con fuente grande (14–16 px), tema claro, 80 columnas, sinEco del prompt limpio.
- [ ] Pestañas abiertas: repositorio en GitHub (rama `plan-pruebas-rendimiento` tras el merge),
      Actions con la corrida de la campaña, el archivo `PLAN_TECNICO.md`, un editor con el código.
- [ ] Grabador de pantalla configurado para capturar solo el monitor, sin notificaciones.
- [ ] Nadie tiene correo, Slack ni Teams abierto. Nada de contraseñas reales en pantalla.
- [ ] Los cinco nombres y apellidos completos anotados para el minuto 0:20.
- [ ] Enlace de la corrida de la campaña copiado en el portapapeles (se usa en el minuto 10:45).

Comprobación rápida de que todo responde, en una sola terminal:

```sh
cd pruebas-rendimiento-parabank
scripts/parabank-up.sh
export PROFILE=smoke RAMP_SECONDS=10 DURATION_SECONDS=10 USERS=2 RATE_PER_SECOND=5 DATA_DIR=data
export BASE_URL=http://127.0.0.1:8080/parabank/services/bank ALLOWED_HOSTS=127.0.0.1
./mvnw -B -ntp test-compile
scripts/run-scenario.sh TransferSimulation smoke
```

Si eso pasa, la grabación puede empezar.

---

## 1. Guion minuto a minuto

### [0:00–0:45] Apertura e integrantes

**En pantalla:** la portada del repositorio en GitHub.

**Narración:**

> Buenos días. Somos el grupo del laboratorio 2 de pruebas de software de la Universidad de
> Antioquia. Our integrantes son: nombre uno, nombre dos, nombre tres, nombre cuatro y nombre cinco.
>
> El laboratorio pide comprobar cinco historias no funcionales de la aplicación ParaBank usando
> Gatling, y no basta con decir que la prueba pasó: hay que mostrar la evidencia.

**Acción:** señalar con el cursor la lista de archivos del repositorio: `PLAN_TECNICO.md`,
`src/test/java`, `scripts/`, `evidence/`, `entrega/`.

---

### [0:45–1:30] Qué se prueba y qué no

**En pantalla:** `PLAN_TECNICO.md`, sección de criterios de aceptación.

**Narración:**

> La aplicación bajo prueba es ParaBank, un banco en línea. Probamos cinco historias: inicio de
> sesión, transferencias entre cuentas propias, consulta de movimientos, solicitud de préstamo y
> pago de servicios a un beneficiario.
>
> Importante: **no** probamos la página pública de Parasoft. El enunciado no autoriza generar
> carga contra un servicio de terceros, así que levantamos nuestra propia instancia en Docker, la
> inicializamos con datos de demostración y le hacemos todo el daño a ella.

**Acción:** abrir `compose.yaml` un segundo y mostrar el puerto 8080 atado a `127.0.0.1`.

---

### [1:30–2:30] El entorno aislado

**En pantalla:** la terminal.

**Narración:**

> Esta es nuestra instancia. `compose.yaml` levanta la imagen oficial de ParaBank fijada por digest,
>publicada en el puerto 8080 pero solo escuchando en el loopback de nuestra máquina. El script
> `parabank-up.sh` la levanta y espera a que responda; `reset-local-parabank-db.sh` reinicia la base
> de demostración antes de cada escenario, para que una corrida no herede los datos de la anterior.

**Acción:** ejecutar y mostrar en vivo:

```sh
scripts/parabank-up.sh
curl -s -H 'Accept: application/json' \
  http://127.0.0.1:8080/parabank/services/bank/customers/12212/accounts \
  | python3 -m json.tool | head -20
```

> La base de demostración trae un cliente y once cuentas. Guarden ese número, lo volveremos a usar.

---

### [2:30–3:20] Los datos de prueba

**En pantalla:** `scripts/prepare-parabank-local-data.py` y la salida del script.

**Narración:**

> Aquí está el punto donde se resuelven varios problemas de una vez. El generador de datos no
> inventa datos: primero **le pregunta a la API** qué clientes y qué cuentas existen de verdad, se
> queda solo con cuentas de tipo checking o savings, y para el escenario de estado de cuenta exige
> que la cuenta **ya tenga movimientos**. En la versión anterior metíamos cuentas sin movimientos y
> el propioParaBank respondía con un arreglo vacío, y como la aserción pedía un movimiento, el
> 18 por ciento de los errores que medíamos no eran de ParaBank: eran nuestros.

**Acción:** ejecutar y mostrar el resumen del script:

```sh
python3 scripts/prepare-parabank-local-data.py
```

> Genera tres archivos: 60.000 transferencias, 24.000 pagos de servicios y 12.000 préstamos. Todos
> los importes están en dólares, las cuentas origen tienen saldo porque la instancia es
> desechable, y cada operación lleva un `caseId` único que después nos permite cuadrar el dinero.

**Transición clave para el video:** los datos se generan, no se versionan; los CSV están en el
`.gitignore`.

---

### [3:20–4:00] Perfiles de inyección y el problema del feeder

**En pantalla:** `Environment.java`.

**Narración:**

> Los perfiles son smoke, normal, peak y stress. Smoke es cinco usuarios durante sesenta segundos y
> sirve para verificar que el código compila y que no hay errores de cableado. Normal es el perfil
> de aceptación: sesenta segundos de rampa y trescientos segundos de meseta estable, que es lo que
> pide el enunciado para poder hablar de límites.
>
> Ahora, el detalle técnico más importante de toda la entrega, y lowantedense en serio: los feeders
> deloan y de pago de servicios se estaban agotando. Usaban una cola de doscientas filas en lugar
> de una cola circular.

**Acción:** mostrar el `feeders("loanRequests").circular()` en la terminal o abrir el archivo y
señalar la línea.

> Con 150 o 200 usuarios durante seis minutos se piden del orden de 54.000 a 72.000 operaciones. Una
> cola de 200 filas se agota en el segundo número doscientos, la simulación se cae y el reporte
> miente. Con `.circular()` los datos se repiten y la prueba mide sostenimiento, no un archivo CSV.

---

### [4:00–5:00] Escenario 1 — Inicio de sesión (H1)

**En pantalla:** `LoginSimulation.java`.

**Narración:**

> Historia uno: inicio de sesión. Perfil abierto, cien usuarios entrando durante un minuto, después
> trescientos segundos a la misma tasa. Criterios: error cero y respuesta máxima menor a dos
> segundos.

**Acción:** señalar el `.pause(PAUSE)` y la aserción del `max`.

**Demostración en vivo** (es el escenario más rápido, 20 segundos):

```sh
export PROFILE=normal
scripts/run-scenario.sh LoginSimulation smoke
```

> En vivo dejo el perfil corto para que el video no se alargue; la campaña de cinco minutos está en
> el artefacto que vamos a ver más adelante. Lo que importa aquí es el reporte que se acaba de
> generar.

**Acción:** abrir `target/gatling/*/index.html` y señalar el gráfico de tiempos de respuesta, el
porcentaje de éxito y el número total de peticiones. Luego abrir la pestaña de la aserción.

> Cero errores y tiempos de respuesta en el orden de milisegundos. El tiempo de espera entre
> operaciones existe por una razón: en un escenario cerrado, doscientos usuarios con respuestas de
> milisegundos generan decenas de miles de peticiones por segundo. Estaríamos midiendo un sistema
> que ya se cayó, no uno que sostiene doscientos usuarios simultáneos.

---

### [5:00–6:30] Escenario 2 — Transferencias (H2)

**En pantalla:** `TransferSimulation.java`.

**Narración:**

> Historia dos: transferencias entre cuentas propias. Es la historia más exigente del laboratorio.
> El criterio no es solo que responda: es que el sistema sostenga al menos 150 transferencias por
> segundo, y que **no se pierda ni se duplique ni un centavo**.

**Acción:** señalar el `atOnceUsers(165)` o la tasa de inyección, y el `.circular()`.

> Este escenario es de modelo abierto: 165 usuarios por segundo, porque el objetivo es
> precisamente saturar la vía de transferencias. 165 y no 150 a propósito, para tener margen: si el
> sistema se queda en 150 clavados, el margen de error se come el criterio.

**Acción:** mostrar el reporte de la corrida corta, luego el verificador de caudal:

```sh
python3 scripts/evaluate-transfer-throughput.py target/gatling/*/js/stats.json \
  --ramp-seconds 10 --duration-seconds 10 --target 150
```

> El verificador no se queda con el promedio: parte la ventana estable en bloques de diez segundos y
> exige que **cada** bloque llegue al objetivo, porque un promedio alto puede esconder diez segundos
> de parálisis. En nuestra corrida local de verificación saggio 164,1 transferencias confirmadas por
> segundo, y el bloque más bajo hizo 163,4. Pasa.

**Acción:** abrir la salida de la conciliación, donde aparece el cuadre de 4.125 confirmadas contra
8.250 asientos, y explicarlo: cada transferencia deja un débito en la cuenta origen y un crédito en
la cuenta destino, y todo tiene que cuadrar sin filas repetidas.

---

### [6:30–7:15] Escenario 3 — Consulta de movimientos (H3)

**En pantalla:** `StatementSimulation.java`.

**Narración:**

> Historia tres: consulta de movimientos. Doscientos usuarios simultáneos, respuesta máxima menor a
> tres segundos y menos del uno por ciento de errores.
>
> Este escenario es el ejemplo de por qué los datos de prueba importan tanto. En la primera versión
> el feeder usaba cuentas sin movimientos, ParaBank devolvía un arreglo vacío y nuestra aserción lo
> contaba como error: 18,2 por ciento de errores falsos. Con el generador nuevo, que exige cuentas
> con al menos un movimiento real, el resultado es cero errores en trescientos segundos con dos
>cientos usuarios y una respuesta máxima de 29 milisegundos.

**Acción:** mostrar el reporte con el 100 por ciento de éxito.

---

### [7:15–8:30] Escenario 4 — Solicitud de préstamo (H4) — el hallazgo

**En pantalla:** `LoanSimulation.java` y el gráfico de «Ko/total» de la corrida real.

**Narración:**

> Historia cuatro: solicitud de préstamo. Ciento cincuenta usuarios, respuesta media menor a cinco
> segundos y por lo menos 98 por ciento de éxito. Este es el escenario **donde encontramos un
> defecto real**, y lo vamos a reportar tal cual.
>
> La primera versión daba 94,39 por ciento de éxito, y la causa no eran nuestros datos: los 46
> rechazos son errores 400 de ParaBank con el cuerpo «Could not find account», sobre cuentas que sí
> existen. Lo reproducimos con veinte llamadas simultáneas fuera de Gatling y desaparece al bajar
> el ritmo: es una condición de carrera interna de ParaBank contra su base HSQLDB.

**Acción:** mostrar la tabla de sensibilidad, que está en `evidence/local-campaign-summary.md`:

| Pausa entre solicitudes | Ritmo efectivo | Éxito |
|---|---:|---:|
| 5 s | ~27 req/s | 94,39 % |
| 15 s | ~10 req/s | 99,67 % |

> Con cinco segundos de espera, que es el valor por defecto del escenario, se cumple el criterio de
> latencia pero no el de éxito, y el hallazgo queda abierto. Con quince segundos el criterio de
> éxito se cumple, pero el de latencia deja de ser el que se está midiendo con la carga que pedía el
> enunciado. **No ajustamos la pausa para que la tabla saliera verde**: lo que hicimos fue medir
> ambas configuraciones y documentar el comportamiento del sistema. Este tipo de hallazgos es
> justamente lo que un banco necesita saber antes de poner ParaBank en producción.

**Acción:** señalar en el reporte que la media de respuesta estuvo en 55 milisegundos, muy por
debajo del límite de 5 segundos, y que el incumplimiento es del criterio de éxito.

---

### [8:30–9:30] Escenario 5 — Pago de servicios (H5)

**En pantalla:** `BillPaySimulation.java`.

**Narración:**

> Historia cinco: pago de servicios a un beneficiario. Doscientos usuarios, respuesta máxima menor a
> tres segundos y menos del uno por ciento de errores, más un criterio extra: cada pago debe quedar
> registrado una sola vez en el historial del banco.
>
> Este es el escenario donde se nota que el sistema bajo prueba no tiene clave idempotente, es
> decir, no existe forma de pedirle «si ya hiciste este pago, no lo repitas». Por eso el harness
> **no reintenta pagos ni transferencias**: un reintento ciego con ParaBank es capaz de cobrar dos
> veces. La garantía la da la conciliación, no un reintento.

**Acción:** mostrar el reporte con 1.753 pagos, cero errores y máximo de 122 milisegundos, y la
salida de la conciliación con el mismo número de débitos y sin duplicados.

> El criterio de unicidad se verifica contra el historial, no contra un número que nos diga la
> propia respuesta de la API.

---

### [9:30–10:30] La conciliación de extremo a extremo

**En pantalla:** `scripts/parabank-ledger.py` y la salida de `run-scenario.sh`.

**Narración:**

> Aquí está la parte del trabajo que más nos enorgullece, porque sin esto los criterios de
> dinero serían afirmaciones. El procedimiento tiene tres pasos:
>
> Primero, antes de la simulación, el script toma una foto del historial de movimientos de todas las
> cuentas. Segundo, se ejecuta la carga. Tercero, se vuelve a leer el historial y se calcula la
> diferencia, y esa diferencia se cuadra contra los intentos que Gatling registró: mismo `caseId`,
> mismo importe, misma cuenta, ninguna fila repetida.
>
> ParaBank le pone identificador único a cada movimiento del historial, y gracias a eso el
> cuadre detecta duplicados reales, no solo diferencias de conteo.

**Acción:** mostrar en pantalla la salida del driver con los pasos y el veredicto `PASS`:

```
== Snapshotting ParaBank ledger before the run
== Running com.parabank.perf.simulations.TransferSimulation
== Reconciling transfer operations against the ParaBank ledger
  "verdict": "PASS"
== TransferSimulation finished with status 0
```

> Para transferencias exigimos un débito en el origen y un crédito en el destino por cada operación;
> para pagos, un débito en la cuenta pagadora. Si algo no cuadra, el proceso sale con código de
> error y la ejecución queda en rojo.

---

### [10:30–11:45] GitHub Actions

**En pantalla:** la pestaña Actions del repositorio en GitHub, con la corrida de la campaña.

**Narración:**

> Todo lo anterior corre automáticamente en GitHub Actions. No hay secretos ni servidor propio.
> Cada push levanta la imagen de ParaBank en el runner, prepara los datos y ejecuta los cinco
> escenarios.

**Acción:** mostrar la pantalla de **Run workflow** con las tres entradas: el escenario, el perfil y
la etiqueta de la corrida. Explicar que la campaña de aceptación se lanza con escenario *all* y
perfil *normal*.

**Acción:** abrir la corrida y mostrar los pasos del job: levantar ParaBank, validar el destino,
preparar datos, ejecutar, resumir, validar criterios, capturar logs.

> El paso que nos importa es este: si un criterio de aceptación o una conciliación falla, el job
> termina en rojo aunque Gatling haya pasado. El código de salida del job es el veredicto.

**Acción:** mostrar la sección **Artifacts** y descargar el reporte de HTML de Gatling; abrirlo en
otra pestaña.

> De cada ejecución guardamos el HTML de Gatling, los metadatos, la salida de consola, el cuadre de
> la conciliación y la tabla de cumplimiento. Esta corrida es la que usamos para el Word de
> entrega y su enlace va en la tabla de la diapositiva final.

**Nota de producción:** si la campaña real ya terminó, este es el momento de abrir el artefacto de
la corrida `normal` y mostrar el reporte de H2 con los 165 por segundo y el resumen de la
conciliación de los cinco minutos.

---

### [11:45–12:30] La tabla de cumplimiento

**En pantalla:** `evidence/runs/summary.md` generado por `scripts/build-summary.py`.

**Narración:**

> Esta tabla se genera sola a partir de la salida real de cada ejecución, no se escribe a mano. Cada
> fila tiene el criterio, el objetivo, el valor medido y el veredicto, y el resumen de la parte
> inferior cuenta cuántos criterios se incumplieron.
>
> En nuestras corridas de verificación los incumplimientos están concentrados en el criterio de
> éxito del préstamo, y son consistentes con el hallazgo que acabamos de explicar. Cuando la
> campaña completa termine, esta misma tabla será la evidencia final de la entrega.

**Acción:** señalar la columna de veredictos y el contador de incumplimientos.

---

### [12:30–13:00] Cierre

**En pantalla:** portada del repositorio otra vez.

**Narración:**

> Para cerrar: los cinco escenarios quedaron verificados de extremo a extremo. Los datos de prueba
> salen de la propia API del sistema, los feeders no se agotan, los criterios de dinero se comprueban
> contra el historial del banco y no se ocultan, y donde encontramos un defecto lo reportamos con la
> evidencia de su reproducción en lugar de ajustar los parámetros hasta que la tabla saliera verde.
>
> Las limitaciones que asumimos: el runner de GitHub Actions es una máquina compartida, así que
> nuestras cifras sirven para repetir las pruebas pero no para certificar límites de rendimiento
> con control total del hardware; y la campaña de cinco minutos es la que formaliza la evidencia.
>
> Muchas gracias por su atención.

---

## 2. Tabla resumen de la demo por escenario

Para no perderse en la grabación, esta es la secuencia de pantallas de cada escenario:

| # | Historia | Modelo | Usuarios | Duración | Criterios que se muestran | Evidencia que se abre |
|---|---|---|---|---|---|---|
| H1 | Login | Cerrado | 100 | 60 rampa + 300 | max < 2000 ms, 0 errores | Reporte: max y % éxito |
| H2 | Transferencias | Abierto | 165/s | 60 rampa + 300 | 150/s por bloque, 0 errores, cuadre | Reporte, `evaluate-transfer-throughput.py`, `reconcile-*.json` |
| H3 | Estado de cuenta | Cerrado | 200 | 60 rampa + 300 | max < 3000 ms, 0 errores | Reporte: 0 errores, caso de los feeders sin movimientos |
| H4 | Préstamo | Cerrado | 150 | 60 rampa + 300 | media < 5000 ms, éxito ≥ 98 % | Reporte: 94,39 % y la tabla de sensibilidad |
| H5 | Pago de servicios | Cerrado | 200 | 60 rampa + 300 | max < 3000 ms, 0 errores, unicidad | Reporte y cuadre sin duplicados |

## 3. Si algo falla durante la grabación

- **ParaBank no levanta:** `docker compose -f compose.yaml logs --tail 20`. El puerto 8080 puede
  estar ocupado; se corrige liberando el puerto y relanzando. Tener la terminal con el `docker info`
  ya verificado evita esto.
- **Gatling falla al compilar:** casi siempre es la primera descarga de dependencias. Adelantado en
  la lista de verificación, no debería pasar en vivo.
- **El reporte HTML no aparece:** la ruta es `target/gatling/<SimulationName>/index.html`. Se abre
  con doble clic; no hace falta servidor.
- **La pantalla se congela:** no correr en vivo la campaña de `normal`. La demo en vivo es con
  `smoke`, y la campaña de cinco minutos se muestra como artefacto ya generado.
- **Se acaba el tiempo:** recortar los minutos 1:30 a 3:20 (entorno y datos) a la mitad. No tocar
  las demos de los cinco escenarios ni la conciliación.

## 4. Después de grabar

- [ ] Revisar audio y legibilidad de las cifras; las cifras deben leerse en pantalla.
- [ ] Verificar que la duración quedó entre 10 y 15 minutos.
- [ ] Subir a Drive con permiso de lectura para cualquiera que tenga el enlace.
- [ ] Copiar el enlace en la sección de video de `entrega/Resumen_actividad_Parabank.docx`, con la
      duración y los nombres completos de los cinco integrantes.
- [ ] Subir el Word a Ingenia.
- [ ] El video no se sube al repositorio: solo su enlace.
