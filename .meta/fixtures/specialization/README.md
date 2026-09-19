# Specialization Fixture

Reference documentation for the synthetic portfolio specialization fixture (solorepo's DR-026, solorepo's DR-239, solorepo's DR-244).

## Purpose

The files in this directory provide isolated, pre-judged substitution data for the Specialization Discipline test runner (`.meta/test_specialization.py`). In accordance with solorepo's DR-026, synthetic fixtures used for testing live outside `.meta/assertions/` to maintain strict boundary separation between operational assertions and synthetic test corpora.

## Files

| File | Purpose |
|---|---|
| [`tokens.json`](tokens.json) | Map of template substitution placeholder keys to synthetic portfolio values. |

## Token Map Contract

`tokens.json` defines literal string mappings replacing placeholders (formatted as `__<KEY>__` in template files) during automated specialization verification:

- `PORTFOLIO_SLUG`: `specialization-test-portfolio` (identifies the synthetic portfolio context `ddd:context/specialization-test-portfolio` and `work:portfolio/specialization-test-portfolio`).
- `PORTFOLIO_NAME`: `Specialization Test Portfolio` (display name for the specialized test portfolio).
- `PORTFOLIO_DESCRIPTION`: `Synthetic test portfolio for specialization end-to-end verification.` (human-readable portfolio description).
- `GITHUB_OWNER`: `solorepo-test` (synthetic repository owner namespace for CI workflows).
- `GITHUB_REPO`: `specialization-test-portfolio` (synthetic repository name).
- `WHY_THIS_PORTFOLIO_EXISTS`: `Demonstrating automated specialization end-to-end verification with synthetic fixtures.` (synthetic statement of portfolio purpose).
