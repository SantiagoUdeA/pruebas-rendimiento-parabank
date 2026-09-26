# Campaña local de verificación (2026-09-26)

Ejecutes de los pasos 1 a 3 sobre la instancia aislada `parasoft/parabank@sha256:8c08664c...` en
`127.0.0.1:8080`. Son corridas cortas de 20 s de meseta (rampa de 10 s), no la campaña de 5 minutos
definida en el plan; sirven para verificar que los feeders, la carga y los verificadores funcionan de
principio a fin. Los umbrales de aceptación se miden sobre la meseta de 300 s en la campaña final.

| Historia | Perfil | Peticiones | Fallos | Media | p95 | Max | Criterio | Resultado |
|---|---|---:|---:|---:|---:|---:|---|---|
| H1 Login | 100 usuarios, pausa 3 s | 880 | 0 | 6 ms | 11 ms | 22 ms | max <= 2000 ms | CUMPLE |
| H2 Transferencias | 165 usuarios/s | 4.125 | 0 | 15 ms | 43 ms | 208 ms | 0 fallos | CUMPLE |
| H2 Transferencias | 165 usuarios/s | 4.125 | 0 | - | - | - | >= 150 confirmadas/s | CUMPLE (164,1/s promedio; 163,4/s el bloque de 10 s más bajo) |
| H2 Transferencias | 165 usuarios/s | 4.125 | 0 | - | - | - | sin perdidas ni duplicados | CUMPLE (4.125 confirmadas = 8.250 asientos) |
| H3 Estado de cuenta | 200 usuarios, pausa 3 s | 1.757 | 0 | 8 ms | 13 ms | 29 ms | max <= 3000 ms y errores <= 1 % | CUMPLE |
| H4 Prestamo | 150 usuarios, pausa 5 s (~27 req/s) | 820 | 46 | 55 ms | 159 ms | 250 ms | media <= 5000 ms | CUMPLE |
| H4 Prestamo | 150 usuarios, pausa 5 s (~27 req/s) | 820 | 46 | - | - | - | exito >= 98 % | **NO CUMPLE (94,39 %)** |
| H4 Prestamo | 150 usuarios, pausa 15 s (~10 req/s) | 300 | 1 | 21 ms | - | 47 ms | exito >= 98 % | CUMPLE (99,67 %) |
| H5 Pago de servicios | 200 usuarios, pausa 3 s | 1.753 | 0 | 12 ms | 21 ms | 122 ms | max <= 3000 ms y errores <= 1 % | CUMPLE |
| H5 Pago de servicios | 200 usuarios, pausa 3 s | 1.753 | 0 | - | - | - | sin duplicados en el historial | CUMPLE (1.753 debitos, uno por pago) |

## Causa de los fallos de H4

Los 46 rechazos son HTTP 400 con el cuerpo `Could not find account #<id>` sobre cuentas que si
existen. Se reproducen con 20 llamadas `curl` simultaneas a `requestLoan` y desaparecen al bajar el
ritmo, asi que son una condicion de carrera interna de ParaBank (HSQLDB) y no un error de los datos
de prueba. La sensibilidad al ritmo quedo medida:

| Pausa entre solicitudes | Ritmo aproximado | Exito |
|---|---:|---:|
| 5 s | ~27 req/s | 94,39 % |
| 15 s | ~10 req/s | 99,67 % |

El criterio de la historia 4 no fija un ritmo de peticiones, solo 150 usuarios concurrentes. La
campana debe declarar que perfil uso y reportar ambas cifras en lugar de ajustar la pausa hasta que
el criterio pase.

## Otros hallazgos

- Los rechazos de la version anterior en la prueba de estado de cuenta no venian del sistema: el
  feeder usaba cuentas sin movimientos y el check `jsonPath("$[0].id")` las contaba como error
  funcional. Ahora `prepare-parabank-local-data.py` solo usa para estados de cuenta cuentas con al
  menos un movimiento real.
- ParaBank no valida saldo: una transferencia de 5.000 desde una cuenta con 10,45 deja el saldo en
  negativo y responde 200. Por eso los feeders usan monto fijo y pequeno y una campaña larga no se
  queda sin fondos.
- `createCustomer` no existe en el OpenAPI 3.0.0 de la imagen fijada, y la base de ejemplo trae un
  solo cliente (12212) con 11 cuentas CHECKING/SAVINGS. Los 150 usuarios virtuales de H4 se
  reparten sobre esas cuentas verificadas por API.
