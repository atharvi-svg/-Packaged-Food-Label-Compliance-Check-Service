# Food Label Compliance Check Service

## Overview
A FastAPI-based backend prototype for submitting packaged-food label
compliance requests asynchronously, tracking job status, and exposing
metrics for monitoring.

## Architecture
- FastAPI: request validation and REST API
- Redis: run-status storage and task queue backend
- RQ worker: asynchronous job processing
- HTML/JavaScript frontend: label submission and status polling
- Prometheus: metrics collection
- Locust: load testing

## API Endpoints
- GET /health — health check
- POST /labels/check — submit a label for processing (HTTP 202)
- GET /runs/{run_id} — retrieve processing status
- GET /metrics — Prometheus metrics
- GET /docs — interactive API documentation

## Run with Docker Compose
Ensure Docker Desktop is running, then execute:
docker compose up -d --build

Check services:
docker compose ps

View logs:
docker compose logs -f api worker

Stop services:
docker compose down

## Monitoring
Open http://localhost:9090/targets to inspect Prometheus scraping.
Open http://localhost:8000/metrics to inspect application metrics.

## Performance Test
Install Locust in the project virtual environment:
python -m pip install locust

Run:
python -m locust -f locustfile.py --host http://127.0.0.1:8000

Open http://localhost:8089 and configure the desired users and spawn rate.

## Current Limitations
The worker currently returns placeholder findings. The actual FSSAI
retrieval, multi-agent reasoning, regulatory citation, and verification
pipeline must be integrated before real compliance decisions can be made.
