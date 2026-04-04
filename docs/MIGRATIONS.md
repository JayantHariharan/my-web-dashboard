# Migration Philosophy

## Principle

Prefer forward-only, non-destructive migrations.

That means migrations should usually:

- create tables
- add columns
- add indexes
- add constraints

Avoid destructive operations in normal automated runs.

## Current PlayNexus Context

The repo is in an auth-first phase. Keep the schema aligned with that reality.

Right now the important database concerns are:

- account creation
- account login support
- account deletion support
- profile storage
- migration tracking

## Practical Rules

1. Do not add speculative schema for future apps.
2. Do not keep stale migration examples that imply active game or app backends.
3. Add one migration per logical change.
4. Never rewrite history for a migration that has already been applied.
5. Document why each new migration exists.

## Good Examples

- add a profile field
- add an index on username lookups
- add session tables once auth actually needs them

## Bad Examples

- creating app-registry tables before the feature exists
- dropping tables automatically in routine deploys
- mixing unrelated changes into one migration

## Safe Workflow

1. Create the next `V<number>__description.sql` file.
2. Run `python scripts/migrate.py --dry-run`.
3. Apply locally.
4. Validate the app behavior.
5. Ship the migration with matching code and docs.

## Last Updated

2026-04-04
