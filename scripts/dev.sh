#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=src:.
exec uvicorn omp_ref_server.main:app --reload --host 0.0.0.0 --port 8080
