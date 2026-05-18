# FATFD -- Feedback, Audit, Test & Fix, Deploy

The quality harness for the AgStack Pest & Disease Models platform.

## What is FATFD?

FATFD is a structured development lifecycle that ensures every change is audited, tested, verified, and documented before shipping. Adapted from the Full Harvest platform harness for agricultural modeling.

## Lifecycle Phases

```
Phase F -> Phase 1 -> Phase 2 -> Phase 2.5 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6 -> Phase 7 -> Phase 8 -> Phase 9
Feedback   Audit      Test&Fix   Adversarial  Docs       Re-Audit   Version    Git        Deploy     Learn      Write State
```

## Directory Structure

```
.audit/
    README.md                  <- You are here
    GUARDRAILS.md              <- Domain guardrails (NEVER auto-modified)
    fatfd_state.json           <- Harness state
    knowledge.json             <- All findings
    validate_fatfd.py          <- Integrity validator
    generate_manifest.py       <- Manifest builder
    config.json                <- Configuration
    hooks/                     <- Git hooks
    reports/                   <- Audit reports
```

## Quick Start

```bash
python3 .audit/validate_fatfd.py
```
