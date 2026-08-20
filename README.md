# Eligibility Audit Engine

An HTTP service for credit union product eligibility and audit decisions,
backed by Postgres.

## Running the system

Prerequisites: Docker and Docker Compose.

```
docker compose up
```

This brings up Postgres and the FastAPI app with no other manual steps.
The app container waits for Postgres to report healthy, then runs
`alembic upgrade head` before starting the server.

Once running, verify with:

```
curl http://localhost:8000/health
```

## Running the tests

```
docker compose exec app pytest
```

## Guarantees