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
`alembic upgrade head` and seeds fixture data before starting the server.

Once running, verify with:

```
curl http://localhost:8000/health
```

## Running the tests

```
docker compose exec app pytest
```

## Test fixtures

`scripts/generate_fixtures.py` generates and seeds sample data for two
credit unions:

- `generate` (re)writes `scripts/fixtures/catalog.json` (products +
  eligibility rules) and `scripts/fixtures/members.json` (sample member
  profiles, deliberately sparse — many are missing fields the catalog's
  rules check against). Both files are checked into the repo; re-run
  this only when the fixture data itself needs to change.
- `seed` reads those two files and inserts `credit_unions`, `products`,
  `rulesets` (version 1, `is_latest`), and `member_profiles` (version
  `"1.0"`, `is_latest`) rows. It never creates `decisions` rows — those
  only come from `/evaluate`, which doesn't exist yet.

`seed` is idempotent (matches existing rows via unique constraints, so
re-running never creates duplicates) and runs automatically on every
app container startup, right after migrations. To run it by hand:

```
docker compose exec app python scripts/generate_fixtures.py seed
```

## Guarantees

DB-level partial unique indexes guarantee at most one `is_latest` row per
credit union (rulesets) and per member (member_profiles), and RESTRICT
FKs keep decisions from ever pointing at a ruleset/profile version that
gets deleted. They don't guarantee rows are actually append-only 
that's an app-role grant, not yet applied here.