# Data Sources Evaluation Matrix

This document records feasibility testing for crypto market data providers used in the Capstone project.

## Evaluation Table

| Provider | Endpoint tested | Symbols tested | Granularity | Fields returned | History coverage | Rate limit | Pagination | Missing values behaviour | Auth needed | Notes | Decision |
|----------|---------------|---------------|-------------|----------------|-----------------|-----------|-----------|------------------------|-------------|-------|----------|
|          |               |               |             |                |                 |           |           |                        |             |       |          |

---

## Target minimum dataset for our pipeline

The ingestion pipeline must at minimum provide:

- date (UTC, ISO 8601)
- open
- high
- low
- close
- volume

Preferred additional fields:

- market_cap
- circulating_supply

Raw data will be stored in:

- data/raw/

Processed and cleaned datasets will be stored in:

- data/processed/

All ingestion logic should live in:

- core/pipelines/
