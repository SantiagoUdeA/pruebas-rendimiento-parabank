# Campaña de aceptación en GitHub Actions — los cinco escenarios

Corrida `all` / `normal` de la rama `plan-pruebas-rendimiento` (merge del PR #1).
Ejecutada el 26 de septiembre de 2026, commit `46b8acf`, runner hospedado de GitHub
(`GitHub Actions 1000000231`, Ubuntu 24.04, 4 vCPU).

- Corrida: <https://github.com/SantiagoUdeA/pruebas-rendimiento-parabank/actions/runs/36258632384>
- Duración total: 38 minutos (17:19:44 a 17:57:51 UTC)
- Perfil: 60 s de rampa + 300 s de meseta estable en los cinco escenarios
- Banco bajo prueba: instancia propia en Docker, `127.0.0.1:8080`, base reiniciada antes de cada escenario
- Artefacto: `gatling-all-normal-36258632384` (17 MB, retención 30 días)
- Estado del job: **fallido**, por el criterio de éxito de H4, no por un error de la automatización

## Criterios evaluados

| Historia | Criterio | Valor medido | Resultado |
|---|---|---|---|
| H1 Login | max response time ≤ 2000 ms | 118 ms | CUMPLE |
| H2 Transferencias | failed events = 0 | 0 | CUMPLE |
| H2 Transferencias | ≥ 150 confirmadas/s en cada bloque de 10 s | 162,7 (mínimo) | CUMPLE |
| H2 Transferencias | Ninguna transferenda perdida o duplicada | 54.450 confirmadas / 108.900 asientos | CUMPLE |
| H3 Estado de cuenta | max response time ≤ 3000 ms | 111 ms | CUMPLE |
| H3 Estado de cuenta | failed events ≤ 1 % | 0 % | CUMPLE |
| H4 Préstamo | mean response time ≤ 5000 ms | 22 ms | CUMPLE |
| H4 Préstamo | ≥ 98 % de solicitudes exitosas | **88,37 %** | **NO CUMPLE** |
| H5 Pago de servicios | max response time ≤ 3000 ms | 111 ms | CUMPLE |
| H5 Pago de servicios | failed events ≤ 1 % | 0 % | CUMPLE |
| H5 Pago de servicios | Cada pago registrado una sola vez | 22.079 confirmadas / 22.079 asientos | CUMPLE |

**16 criterios evaluados, 1 incumplido.** Los cinco escenarios se ejecutaron completos: el job
termina en rojo por el veredicto del criterio, no porque una simulación se haya caído.

## Métricas por escenario

| Historia | Peticiones | Fallos | Media | p95 | Máx |
|---|---:|---:|---:|---:|---:|
| H1 Login | 11.041 | 0 | 4 ms | 6 ms | 118 ms |
| H2 Transferencias | 54.450 | 0 | 3 ms | 4 ms | 64 ms |
| H3 Estado de cuenta | 22.060 | 0 | 5 ms | 6 ms | 111 ms |
| H4 Préstamo | 9.940 | 1.156 | 22 ms | 121 ms | 721 ms |
| H5 Pago de servicios | 22.079 | 0 | 4 ms | 5 ms | 111 ms |

H2: 60.000 filas de feeder y 54.450 transferencias, o sea el feeder circular cubrió la rampa y
los cinco minutos de meseta sin agotarse. En la versión anterior de los scripts, el feeder de
transferencias era una cola de 200 filas y la simulación se caía en el segundo 200.

## Caudal de H2 por bloques de 10 segundos

Los 30 bloques de la ventana estable, en transferencias confirmadas por segundo:

```
165,0  165,1  165,0  165,0  165,0  164,9  165,1  164,9  165,1  164,9
165,0  165,1  165,0  165,0  164,9  165,0  165,0  165,1  165,0  164,9
165,1  165,0  164,9  165,0  165,0  165,1  164,9  165,1  165,0  162,7
```

Promedio 164,9/s. El bloque más bajo fue el último, con 162,7/s, igual por encima del objetivo de
150/s. Ningún bloque presenta la caída de diez segundos que sí se había observado en corridas
anteriores con el feeder agotándose.

## Conciliación

| Operación | Intentos | Confirmadas | Asientos en el historial | Veredicto |
|---|---:|---:|---:|---|
| Transferencias | 54.450 | 54.450 | 108.900 | PASS |
| Pagos de servicios | 22.079 | 22.079 | 22.079 | PASS |

Los 108.900 asientos de las transferencias son exactamente el doble de las 54.450 operaciones: un
débito en la cuenta de origen y un crédito en la cuenta de destino por transferencia, sin filas
repetidas. No hay cobros duplicados en los 22.079 pagos.

## H4: por qué falló y por qué el job quedó rojo

1.156 de 9.940 solicitudes de préstamo fueron rechazadas: 88,37 % de éxito contra el 98 % exigido.
La latencia, en cambio, quedó muy por debajo del límite: media de 22 ms contra los 5.000 ms del
criterio. Lo que falla no es la velocidad, es la disponibilidad bajo concurrencia.

Las causas se documentaron antes de esta corrida, en `local-campaign-summary.md`: ParaBank responde
HTTP 400 con el cuerpo `Could not find account #<id>` sobre cuentas que sí existen, y el error se
reproduce con llamadas simultáneas hechas por fuera de Gatling. Es una condición de carrera interna
de ParaBank contra su base HSQLDB.

El resultado en el runner hospedado es peor que en la máquina local (88,37 % frente a 94,39 % con la
misma pausa de 5 s) y el motivo es coherente: el runner tiene 4 vCPU y en ellos conviven el Tomcat de
ParaBank, el motor de Gatling, 150 usuarios virtuales y el propio sistema operativo. A menor
disponibilidad de CPU, más veces coinciden dos lecturas concurrentes sobre la misma fila de cuenta y
más veces se repite la carrera.

En esta corrida el cuerpo de la respuesta de los rechazos no quedó registrado: Gatling solo guarda
el código de estado en la consola, que es 400. El texto literal del error se comprobó y se documentó
en la máquina local.

## Qué hacer con esta corrida

- Es la evidencia de la campaña de aceptación. De ella se captura la tabla, los reportes HTML y
  los veredictos de conciliación para el documento de entrega y el video.
- Los 15 criterios cumplidos se reportan como cumplidos y el de H4 se reporta como no cumplido, con
  la explicación de la causa. La pausa del escenario se dejó en 5 s a propósito: subirla a 15 s
  hace pasar el criterio de éxito, pero midiendo 10 peticiones por segundo en lugar de las ~27 que
  genera el perfil, es decir, midiendo otra carga.
- Si el docente requiere que las cinco historias pasen, la palanca no es el dato de prueba sino el
  ritmo: H4 pasa a ~10 req/s. Eso se documenta como el límite de ParaBank bajo este modelo de
  ejecución, no como un ajuste para maquillar la tabla.

## Cambio posterior del perfil de H4

Esta corrida se ejecutó con `LOAN_PAUSE_SECONDS=5`. El docente pidió subir la espera a 15 s, y el
valor por defecto del escenario pasó a 15 s en el commit `6c1d0b8`. Los datos de esta corrida se
dejan sin modificar: son la medición con la que se detectó el defecto y no deben reescribirse.

Lo que cambia con 15 s de espera, dicho de forma explícita para que el documento de entrega no
amague:

| Escenario | Pausa | Ritmo efectivo | Éxito de H4 |
|---|---:|---:|---:|
| H4 en esta campaña (corrida 36258632384) | 5 s | ~27 req/s | 88,37 % → NO CUMPLE |
| H4 en la máquina local | 15 s | ~10 req/s | 99,67 % → CUMPLE |
| H4 con el valor por defecto nuevo | 15 s | ~10 req/s | pendiente de la corrida de confirmación |

Con 150 usuarios y 15 s de espera, cada usuario sostiene una operación cada 15 segundos, así que el
escenario genera unas 10 peticiones por segundo en lugar de 27. Sigue siendo un modelo cerrado de
150 usuarios simultáneos, que es lo que pide el enunciado, pero la presión sobre ParaBank es
menor. El criterio de latencia se cumple con holgura en las dos configuraciones.
