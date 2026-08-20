# Eligibility Audit Engine

An HTTP service for credit union product eligibility and audit decisions,
backed by Postgres.

## Running the system

Prerequisites: Docker and Docker Compose.

```
docker compose up
```

This brings up Postgres and the FastAPI app with no other manual steps.
On startup the app container waits for Postgres to report healthy, runs
`alembic upgrade head`, then seeds fixture data (`scripts/generate_fixtures.py seed`)
before starting the server. Seeding is idempotent — safe to restart the
stack without creating duplicate rows.

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

This would be complete once /evaluate, /backtest, and the Rules API actually exist.
Right now there's only a database, so these are database-level guarantees, not full-system ones.

What is guaranteed:

A credit union can never have two "active" rulesets at once, and a member can never have two "active" profile versions at once, the database itself rejects it, not just the application code.
A decision can never point at a ruleset or profile version that gets deleted, the database blocks that deletion.
Re-running the seed script is safe, it won't create duplicate data.

What is not guaranteed, because it isn't built yet:

Nothing prevents someone from editing or deleting an existing row by hand. This would be locked down at the database-permission level, but haven't yet.
There is no /evaluate, /backtest, or rules-update endpoint yet, so there are no guarantees about what happens under concurrent requests or partial failures. Those sections would be added once that code exists and has been tested.