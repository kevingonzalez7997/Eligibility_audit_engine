"""Generate and seed fixture test data for the eligibility audit engine.

Two subcommands:

    python scripts/generate_fixtures.py generate
        (Re)writes scripts/fixtures/catalog.json and
        scripts/fixtures/members.json from the data defined below.
        Run this locally whenever the fixture data itself needs to
        change; the output is checked into the repo.

    python scripts/generate_fixtures.py seed
        Reads those two JSON files and inserts credit_unions,
        products, rulesets, and member_profiles rows into the
        database pointed to by DATABASE_URL. Idempotent: safe to run
        on every container startup.

This script intentionally talks to Postgres with raw asyncpg rather
than importing the `app` package, so it has no dependency on the
FastAPI app's module layout and no business logic of its own.
"""

import argparse
import json
import os
import uuid
from pathlib import Path

import asyncpg

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CATALOG_PATH = FIXTURES_DIR / "catalog.json"
MEMBERS_PATH = FIXTURES_DIR / "members.json"


def build_catalog() -> dict:
    return {
        "credit_unions": [
            {
                "name": "Northstar Community Credit Union",
                "products": [
                    {
                        "id": "ncu_auto_loan_standard",
                        "name": "Standard Auto Loan",
                        "rules": [
                            {"field": "credit_score", "operator": "gte", "value": 620},
                            {"field": "annual_income", "operator": "gte", "value": 24000},
                            {"field": "state", "operator": "eq", "value": "CA"},
                        ],
                    },
                    {
                        "id": "ncu_credit_card_rewards",
                        "name": "Premium Rewards Credit Card",
                        "rules": [
                            {"field": "credit_score", "operator": "gte", "value": 700},
                            {"field": "annual_income", "operator": "gte", "value": 45000},
                            {"field": "employment_status", "operator": "eq", "value": "employed"},
                        ],
                    },
                    {
                        "id": "ncu_heloc_standard",
                        "name": "Home Equity Line of Credit",
                        "rules": [
                            {"field": "credit_score", "operator": "gte", "value": 680},
                            {"field": "account_age_months", "operator": "gte", "value": 12},
                            {"field": "state", "operator": "eq", "value": "CA"},
                        ],
                    },
                    {
                        "id": "ncu_savings_starter",
                        "name": "Starter Savings Account",
                        "rules": [
                            {"field": "account_age_months", "operator": "gte", "value": 0},
                            {"field": "state", "operator": "eq", "value": "CA"},
                        ],
                    },
                ],
            },
            {
                "name": "Harborview Credit Union",
                "products": [
                    {
                        "id": "hcu_auto_loan_new_used",
                        "name": "New/Used Auto Loan",
                        "rules": [
                            {"field": "credit_score", "operator": "gte", "value": 640},
                            {"field": "annual_income", "operator": "gte", "value": 28000},
                            {"field": "state", "operator": "eq", "value": "TX"},
                        ],
                    },
                    {
                        "id": "hcu_credit_card_cashback",
                        "name": "Cash Back Credit Card",
                        "rules": [
                            {"field": "credit_score", "operator": "gte", "value": 660},
                            {"field": "employment_status", "operator": "eq", "value": "employed"},
                        ],
                    },
                    {
                        "id": "hcu_heloc_standard",
                        "name": "Home Equity Line of Credit",
                        "rules": [
                            {"field": "credit_score", "operator": "gte", "value": 700},
                            {"field": "annual_income", "operator": "gte", "value": 60000},
                            {"field": "account_age_months", "operator": "gte", "value": 24},
                        ],
                    },
                    {
                        "id": "hcu_savings_starter",
                        "name": "Starter Savings Account",
                        "rules": [
                            {"field": "account_age_months", "operator": "gte", "value": 0},
                            {"field": "state", "operator": "eq", "value": "TX"},
                        ],
                    },
                ],
            },
        ]
    }


# Sample member profiles, deliberately sparse: most are missing one or
# more fields that the catalog's rules above check against
# (credit_score, annual_income, state, employment_status,
# account_age_months). member_id is generated fresh each time
# `generate` runs and then stays fixed in the checked-in JSON file.
MEMBERS = [
    {"credit_score": 810, "annual_income": 132000, "state": "CA", "employment_status": "employed", "account_age_months": 96},
    {"credit_score": 590, "state": "TX", "employment_status": "unemployed", "account_age_months": 4},
    {"credit_score": 705, "annual_income": 61000, "state": "NY", "employment_status": "employed", "account_age_months": 30},
    {"annual_income": 27000, "state": "CA", "employment_status": "self_employed", "account_age_months": 8},
    {"credit_score": 745, "annual_income": 88000, "employment_status": "employed", "account_age_months": 60},
    {"credit_score": 512, "annual_income": 16500, "state": "FL", "account_age_months": 1},
    {"credit_score": 690, "annual_income": 47000, "state": "CA", "employment_status": "employed"},
    {"credit_score": 800, "annual_income": 145000, "state": "WA", "employment_status": "self_employed", "account_age_months": 120},
    {"annual_income": 33000, "state": "TX", "employment_status": "employed", "account_age_months": 14},
    {"credit_score": 575, "state": "CA", "employment_status": "student", "account_age_months": 2},
    {"credit_score": 720, "annual_income": 54000, "state": "TX", "account_age_months": 42},
    {"credit_score": 615, "annual_income": 25500, "employment_status": "retired", "account_age_months": 216},
    {"credit_score": 780, "annual_income": 97000, "state": "CA", "employment_status": "employed", "account_age_months": 72},
    {"credit_score": 648, "state": "FL", "employment_status": "self_employed", "account_age_months": 6},
    {"annual_income": 15000, "state": "TX", "account_age_months": 0},
    {"credit_score": 715, "annual_income": 63000, "state": "WA", "employment_status": "employed", "account_age_months": 36},
    {"credit_score": 683, "state": "CA", "employment_status": "employed", "account_age_months": 20},
    {"credit_score": 830, "annual_income": 120000, "state": "TX", "employment_status": "employed"},
    {"annual_income": 22500, "employment_status": "student", "account_age_months": 3},
    {"credit_score": 670, "annual_income": 38000, "state": "TX", "employment_status": "employed"},
]


def build_members() -> dict:
    return {
        "members": [
            {"member_id": str(uuid.uuid4()), "profile": profile} for profile in MEMBERS
        ]
    }


def cmd_generate(_args: argparse.Namespace) -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    catalog = build_catalog()
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")

    members = build_members()
    MEMBERS_PATH.write_text(json.dumps(members, indent=2) + "\n")

    n_products = sum(len(cu["products"]) for cu in catalog["credit_unions"])
    print(
        f"Wrote {CATALOG_PATH} "
        f"({len(catalog['credit_unions'])} credit unions, {n_products} products)"
    )
    print(f"Wrote {MEMBERS_PATH} ({len(members['members'])} members)")


def _dsn() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/eligibility",
    )
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _seed(conn: asyncpg.Connection) -> dict:
    catalog = json.loads(CATALOG_PATH.read_text())
    members = json.loads(MEMBERS_PATH.read_text())

    counts = {"credit_unions": 0, "products": 0, "rulesets": 0, "member_profiles": 0}

    for cu in catalog["credit_unions"]:
        credit_union_id = await conn.fetchval(
            """
            INSERT INTO credit_unions (name) VALUES ($1)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            cu["name"],
        )
        counts["credit_unions"] += 1

        ruleset_rules = []
        for product in cu["products"]:
            product_id = await conn.fetchval(
                """
                INSERT INTO products (credit_union_id, name) VALUES ($1, $2)
                ON CONFLICT (credit_union_id, name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                credit_union_id,
                product["name"],
            )
            counts["products"] += 1
            for rule in product["rules"]:
                ruleset_rules.append(
                    {
                        "product_id": product_id,
                        "field": rule["field"],
                        "operator": rule["operator"],
                        "value": rule["value"],
                    }
                )

        result = await conn.execute(
            """
            INSERT INTO rulesets (credit_union_id, version, rules, is_latest)
            VALUES ($1, 1, $2::jsonb, true)
            ON CONFLICT (credit_union_id, version) DO NOTHING
            """,
            credit_union_id,
            json.dumps(ruleset_rules),
        )
        if result == "INSERT 0 1":
            counts["rulesets"] += 1

    for member in members["members"]:
        result = await conn.execute(
            """
            INSERT INTO member_profiles (id, member_id, version, profile_data, is_latest)
            VALUES ($1, $2, '1.0', $3::jsonb, true)
            ON CONFLICT (member_id, version) DO NOTHING
            """,
            uuid.uuid4(),
            uuid.UUID(member["member_id"]),
            json.dumps(member["profile"]),
        )
        if result == "INSERT 0 1":
            counts["member_profiles"] += 1

    return counts


async def cmd_seed(_args: argparse.Namespace) -> None:
    if not CATALOG_PATH.exists() or not MEMBERS_PATH.exists():
        raise SystemExit(
            f"Fixture files not found under {FIXTURES_DIR}. "
            "Run `python scripts/generate_fixtures.py generate` first."
        )

    conn = await asyncpg.connect(_dsn())
    try:
        async with conn.transaction():
            counts = await _seed(conn)
    finally:
        await conn.close()

    print(
        f"Seed complete. Processed {counts['credit_unions']} credit union(s), "
        f"{counts['products']} product(s) (matched on their unique constraints and "
        "reused if present). New rows this run: "
        f"{counts['rulesets']} ruleset(s), {counts['member_profiles']} member_profile(s)."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("generate", help="Write catalog.json and members.json")
    subparsers.add_parser("seed", help="Seed the database from the fixture JSON files")
    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "seed":
        import asyncio

        asyncio.run(cmd_seed(args))


if __name__ == "__main__":
    main()
