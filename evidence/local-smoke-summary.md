# ParaBank local smoke run

Date: 2026-09-24 (America/Bogota)

Instance: official Parasoft image `parasoft/parabank@sha256:8c08664c7b4be5dc3b1dcf5bbc75f57bbcc1b363ea063fae873409a0883a8e44`, ParaBank OpenAPI 3.0.0, Tomcat 11.0.26 / Java 25.0.4. The API was reachable only through `127.0.0.1:8080`; database and JMS ports were not published.

These are low-volume functional smoke checks against the initialized demo database. They do not establish the plan's concurrency or throughput criteria.

| Story | Smoke profile | Requests | Successful | Mean | Maximum | Result |
|---|---:|---:|---:|---:|---:|---|
| H1 Login | 2 one-shot users | 2 | 2 | 4 ms | 4 ms | Functional smoke passed |
| H2 Transfer | 5 requests/s for 10 s | 50 | 50 | 3 ms | 6 ms | Functional smoke passed; target 150 confirmed/s not evaluated |
| H3 Statement | 2 one-shot users | 2 | 2 | 5 ms | 5 ms | Functional smoke passed |
| H4 Loan | 1 one-shot user | 1 | 1 | 26 ms | 26 ms | Functional smoke passed; one seeded customer cannot establish 150-user acceptance |
| H5 Bill pay | 2 one-shot users | 2 | 2 | 5 ms | 5 ms | Functional smoke passed |

Financial reconciliation: H2's 50 confirmed transfers matched 100 new ledger rows (one debit and one credit per transfer); H5's two confirmed payments matched two new debit rows. Both local reconciliation summaries reported `PASS`. This validates the smoke data only, not campaign-scale integrity.

Gatling HTML reports are under the ignored `target/gatling/` directory. The successful report directories are `loginsimulation-20260924234646155`, `transfersimulation-20260924235506943`, `statementsimulation-20260924234715065`, `loansimulation-20260924234939461`, and `billpaysimulation-20260924235625606`.

The first login attempt exposed an overly repetitive smoke profile: it ran 28,586 requests and began receiving premature connection closes. That run was discarded, the smoke profile was changed to one-shot users for closed-model scenarios, and the isolated database was reinitialized. A two-user loan smoke also produced one rejection because the stock dataset contains one customer; the final one-user smoke passed. No high-load campaign was run, no acceptance story is declared passed.
