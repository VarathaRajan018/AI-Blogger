# ADR-002: PostgreSQL Over MongoDB for Pipeline Data

**Date**: 2026-07-07  
**Status**: Accepted  
**Deciders**: Platform Architect

---

## Context

The platform stores structured pipeline metadata: blog configurations, pipeline run records, content drafts, keyword reports, and analytics snapshots. We considered both a document store (MongoDB) and a relational database (PostgreSQL).

## Decision

Use **PostgreSQL** as the primary data store, accessed via **SQLAlchemy 2.0** (async).

## Rationale

| Factor | Rationale |
|--------|----------|
| **Relational Integrity** | Pipeline runs → drafts → keyword reports are highly relational; foreign keys prevent orphaned data |
| **JSONB Support** | PostgreSQL's JSONB columns give us flexible schema for LLM outputs without sacrificing query power |
| **Analytics Queries** | Complex aggregations (e.g., posts published per week, top-performing niches) are natural in SQL |
| **Maturity** | PostgreSQL is battle-tested; SQLAlchemy 2.0 has excellent async support via `asyncpg` |
| **Cost** | Self-hosted PostgreSQL has zero licensing cost; managed (AWS RDS, Supabase) is affordable |
| **ACID Guarantees** | Critical for pipeline state management — a run must not be marked complete if it partially failed |

## Consequences

- **Positive**: Strong data integrity; powerful analytics queries; easy migration with Alembic
- **Negative**: Schema migrations required for structural changes (mitigated by JSONB for dynamic fields)
- **Mitigation**: Use JSONB columns for LLM outputs and API responses where schema flexibility is needed
