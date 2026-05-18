# Domain Guardrails -- AgStack PND

These are human-owned rules. The system may NEVER modify this file without explicit human approval.

## Data Provenance

- **G-DATA-001**: All model calculations must be reproducible given the same weather input.
- **G-DATA-002**: Weather data provenance must be traceable (provider, fetch timestamp, cache status).
- **G-DATA-003**: No proprietary datasets or API keys may be committed to the repository.

## Model Integrity

- **G-MODEL-001**: Every disease model must cite its academic/institutional source.
- **G-MODEL-002**: Model parameter changes require peer review from a domain expert.
- **G-MODEL-003**: Threat catalog biological parameters must reference published literature.
- **G-MODEL-004**: Model accuracy claims must be backed by validated test cases.

## API Stability

- **G-API-001**: Breaking API changes require a deprecation cycle (minimum 1 minor version).
- **G-API-002**: MCP tool schemas must remain backward-compatible within a major version.

## Community

- **G-COMMUNITY-001**: Community-contributed models must include tests and citations.
- **G-COMMUNITY-002**: UUID assignments are permanent; revocation requires TSC approval.
- **G-COMMUNITY-003**: All contributions must be Apache-2.0 compatible.
