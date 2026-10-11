# Operations Runbook

## Start
1. Start Docker Desktop.
2. Open PowerShell in the project directory.
3. Run: docker compose up -d --build
4. Verify: docker compose ps

## Health Checks
- API: http://localhost:8000/health
- API documentation: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics
- Prometheus targets: http://localhost:9090/targets

## Troubleshooting
### API is unavailable
Run docker compose ps and docker compose logs api.

### Jobs remain queued
Check Redis and worker logs:
docker compose logs redis worker

### Prometheus target is down
Check that prometheus.yml exists as a file and that the API
service is running. Inspect logs with:
docker compose logs prometheus

### Validation returns HTTP 422
Check the request body against the LabelRequest schema at /docs.
The ingredients field must be an array of strings.

## Shutdown
Run: docker compose down

## Important Limitation
The compliance worker currently uses placeholder processing.
Do not use its output as an actual regulatory compliance determination.
