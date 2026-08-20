# Decisions memo

## Three decisions I made

**1. Ledger points at versioned rows instead of copying them.**
`decisions` stores `ruleset_version_id` and `profile_version_id`, not
the full ruleset/profile. Since both tables are append-only (new row
per change, `is_latest` flag, DB constraint blocking two "latest" rows
per entity), a row that never changes is just as immutable to point at
as it would be to copy. Saves the duplication without losing the
guarantee.

**2. One database, not three.** Auditor lookups and backtest replays
are the same underlying reads, just different filters, that's an
indexing problem, not a reason to split databases. Splitting would
mean either duplicating every decision into two stores (risking drift,
which breaks the whole point of exact reconstruction) or a sync layer.

**3. Member profiles get versioned too, not just snapshotted per
decision.** `/evaluate` gets the full profile inline each call, so
technically I could've just dropped it straight into the decision row
and called it done. I versioned it in its own table instead so profile
history is queryable on its own, and so rulesets and profiles follow
the same pattern instead of two different ways of handling "things
that change over time."

## Where I overrode the AI agent

The agent's first instinct on the schema was to skip a member_profiles
table entirely and just snapshot the profile straight onto the
decision row, since /evaluate never looks anything up, there's no
"current profile" to version in the first place. I overrode that and
built the versioned table anyway (see #3), because I cared more about
being able to query a member's profile history on its own than about
keeping the schema minimal.

## What I didn't build

Locking `decisions` down at the database role level so nothing can
UPDATE/DELETE it, even by accident. Right now that's enforced by
convention (the app just never does it), not by grants. The right fix
is a least-privilege DB role for the app. Skipped it because it doesn't 
change any decision logic, it's hardening.

## Build plan

I broke the build into one Claude Code session per component, each
with a clear input/output boundary so state carries forward cleanly:

1. Repo scaffolding: FastAPI + Postgres skeleton, docker-compose,
   `/health`, no schema/logic yet.
2. Database schema: Alembic migrations + models for all 5 tables,
   append-only/versioning constraints.
3. Fixture generator: `catalog.json` / `members.json`, seeded into
   the versioned tables.
4. Rules API: `PUT`/`GET /credit-unions/{cu_id}/rules`.
5. Evaluate engine: `POST /evaluate`, rule matching, missing-field
   handling, ledger write.
6. Decision ledger read: `GET /decisions/{decision_id}`.
7. Backtest engine: `POST /backtest`, reusing the evaluate logic
   against a proposed ruleset.
8. Integration tests: full flow end to end, specifically trying to
   break the immutability guarantee (edit a profile after a decision,
   confirm the old decision and any backtest against it don't change).

## With more time I would...

Test the spec's two hard requirements: never show a product a member isn't
confirmed eligible for, and make every decision fully reconstructable
after the fact, even once rules or profiles have changed. Priorities
below follow from those two.

- **A test proving no product ever leaks into `eligible` unless every
  rule affirmatively passed.** For every product in the catalog, walk
  its rules and assert: any single failed or missing-field rule keeps
  it out of `eligible`, and it only appears there when all rules
  return "passed." 
- **Tests on the missing-field path.** One of the worst possible
  bug here is missing data silently counting as a pass. I'd test
  empty string vs. missing key vs. null vs. wrong type directly.
- **An end-to-end reconstruction test.** Run a decision, mutate the
  member fixture, replace the ruleset, then re-fetch the original
  decision and backtest against it, and assert nothing shifted. I have
  the schema for this; I don't yet have the test proving it.
- **Concurrency specific to those guarantees**
 `/evaluate` racing `PUT /rules` for the same credit union,
  or two `/evaluate` calls for the same member producing two "latest"
  profile versions.
- **DB role restriction on `decisions`** Makes "immutable" true
  against more than just my own application code.