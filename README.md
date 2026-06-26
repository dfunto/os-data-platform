# Open Source Data Platform

Open source data platform built on Kubernetes.

# Tech Stack

- Metadata Storage: Postgres
- Container Deployment: Kubernetes / Helm
- Orchestration: Dagster
- File Storage: SeaweedFS
- Ingestion: Airbyte
- Resource/State Management: Pulumi
- Warehouse: Clickhouse

# Roadmap

- Deploy Metadata Database (Postgres) ✅
- Deploy File Storage (SeaweedFS) ✅
- Deploy Ingestion Engine (Airbyte) ✅
- S3 Ingestion Capability
  - Configuration Interface (YAML) ✅
  - 


# Source Ingestion

Files
RDBMS
REST API

# Design Decisions

## Ingestion Strategy: Airbyte for Connectors, Direct Copy for Files

**Decision:** Use Airbyte for API/SaaS/CDC sources. Use `aws s3 sync` + ClickHouse S3 engine for file-based sources (S3 parquet).

**Context:** Airbyte deserializes all source data into JSON records (Airbyte protocol) then re-serializes to the destination format. There is no passthrough/raw-file mode. For file-based sources this means parquet files get deserialized and re-serialized, which is unnecessary overhead and can introduce schema inference noise or precision loss.

**Rationale:**
- **Raw layer preservation:** The raw layer should keep source files as close to original as possible. Byte-for-byte copy via `aws s3 sync` achieves this; Airbyte deserialization works against it.
- **Failure isolation:** If source S3 has short retention (e.g. 3 days), data must land in our raw bucket before any transformation. A direct copy has fewer failure points than Airbyte's deserialize-serialize pipeline.
- **Schema validation at the right layer:** Schema checks are better done as an explicit Dagster asset (controlled, observable) rather than implicitly inside the ingestion tool.
- **Right tool for the job:** Airbyte excels at sources that need connectors, auth, pagination, rate limiting. S3 files are already accessible — no connector needed.

**Consequences:**
- Two ingestion paths to orchestrate (Dagster handles both).
- Airbyte manages API/SaaS/CDC ingestion.
- `aws s3 sync` (via Dagster op) copies file-based sources to raw S3 bucket.
- ClickHouse reads raw parquet directly via S3 table function.

## Raw Layer as Safety Net

**Decision:** All ingestion (file-based or connector-based) lands in a raw S3 bucket with indefinite retention before loading to ClickHouse.

**Context:** Source systems may have short data retention. Schema changes or pipeline failures can prevent data from loading into the warehouse. Without a raw layer, data loss is permanent.

**Rationale:**
- Decouples ingestion from transformation — if ClickHouse load fails, raw data is safe.
- Engineers have time to investigate and fix schema issues without data loss pressure.
- Enables replay and backfill from raw at any time.
- Provides audit trail of what arrived and when.

**Consequences:**
- Additional S3 storage cost (acceptable trade-off for data safety).
- Pipeline pattern: `source → raw S3 → validate/transform → ClickHouse`.
