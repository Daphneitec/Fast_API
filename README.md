# Abacus service

FastAPI running-sum microservice. Every node talks to one shared store so
`GET /abacus/sum` is strongly consistent no matter which instance you hit.

| Method | Path | Body | Effect |
| --- | --- | --- | --- |
| POST | `/abacus/number` | `{"number": N}` | Atomically add `N` |
| GET | `/abacus/sum` | | Current sum |
| DELETE | `/abacus/sum` | | Reset sum to `0` |

## Why the sum stays correct on N nodes

API processes are stateless. The sum lives in **one** store:

- **SQLite (default, local demo)** — `BEGIN IMMEDIATE` + WAL. Concurrent POSTs from many processes serialize on the DB lock; GET always reads the committed value.
- **Redis (multi-node / containers)** — `INCRBY` / `INCRBYFLOAT` / `GET` / `SET` on a single primary. Redis applies those commands atomically, so N replicas still see one linearizable sum.

Reads are never cached. That favors GET consistency over extra read throughput (GET is the low-QPS path).

1000 POSTs/minute is well within either backend. For tens of nodes, use Redis (`ABACUS_STORE=redis`).

## Local two-node demo (Windows terminals)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Terminal 1:

```powershell
.\scripts\start_node1.ps1
```

Terminal 2:

```powershell
.\scripts\start_node2.ps1
```

Terminal 3:

```powershell
py -3.12 scripts/demo_two_nodes.py
```

The demo resets the sum, fires concurrent POSTs at both ports, then GETs both nodes and checks they return the same expected total.

Manual checks:

```powershell
curl.exe -X DELETE http://127.0.0.1:8001/abacus/sum
curl.exe -X POST http://127.0.0.1:8001/abacus/number -H "Content-Type: application/json" -d "{\"number\": 10}"
curl.exe -X POST http://127.0.0.1:8002/abacus/number -H "Content-Type: application/json" -d "{\"number\": 5}"
curl.exe http://127.0.0.1:8001/abacus/sum
curl.exe http://127.0.0.1:8002/abacus/sum
```

## Docker (2 containers + Redis)

```powershell
docker compose up --build
py -3.12 scripts/demo_two_nodes.py
```

## Tests

```powershell
py -3.12 -m pytest
```
