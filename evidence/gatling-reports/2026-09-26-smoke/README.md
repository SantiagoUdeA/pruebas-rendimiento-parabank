# Smoke ParaBank — 2026-09-26

Pruebas de rendimiento (perfil `smoke`) ejecutadas contra instancia local aislada
`parasoft/parabank` en Docker (WSL2/Ubuntu). Base demo reiniciada antes de cada
simulación. Gatling 3.14.9, Java 21.

| Simulación | Reqs OK/KO | Mín–Media–Máx (ms) | Aserción | Resultado |
|---|---|---|---|---|
| H1 Login (`login/`) | 2 / 0 | 30–76–121 | máx ≤ 2000 | PASS |
| H2 Transfer (`transfer/`) | 50 / 0 | 10–13–32 | 0 fallos | PASS |
| H3 Statement (`statement/`) | 2 / 0 | 33–33–33 | máx ≤ 3000, fallos ≤ 1% | PASS |
| H4 Loan (`loan/`) | 1 / 0 | 228–228–228 | media ≤ 5000, éxito ≥ 98% | PASS |
| H5 BillPay (`billpay/`) | 2 / 0 | 13–14–14 | máx ≤ 3000, fallos ≤ 1% | PASS |

## Cómo ver los informes

Versiones en PDF listas para compartir en `pdf/` (`login.pdf`, `transfer.pdf`,
`statement.pdf`, `loan.pdf`, `billpay.pdf`).

GitHub muestra el HTML como código. Para ver el informe interactivo de Gatling,
clona el repo y abre en el navegador el `index.html` de cada carpeta
(`login/`, `transfer/`, `statement/`, `loan/`, `billpay/`).

Nota: son smoke de bajo volumen (chequeo funcional); no certifican los
criterios de carga alta (`normal`/`peak`/`stress`).
