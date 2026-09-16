$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$env:ABACUS_STORE = "sqlite"
$env:ABACUS_SQLITE_PATH = (Join-Path (Get-Location) "abacus.db")
$env:ABACUS_NODE_NAME = "node-2"
py -3.12 -m uvicorn abacus.main:app --host 127.0.0.1 --port 8002
