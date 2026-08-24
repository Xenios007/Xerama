# MODULE-005 — Repository Architecture

**Status:** AUDIT/EXTEND
**Depends on:** 004

## Objective
Keep domain/application services independent of SQLAlchemy and future database choice.

## Requirements
- Audit repository Protocols and SQLAlchemy implementations.
- Add repositories for every persisted aggregate introduced by modules 001–080.
- Define transaction/unit-of-work behavior.
- Avoid leaking ORM models outside persistence layer.
- Support deterministic test repositories/fakes when useful.

## Verification
Contract tests against repository implementations and transaction rollback tests.

## Done when
Application code can be tested without direct ORM coupling and PostgreSQL replacement remains feasible; commit/push.