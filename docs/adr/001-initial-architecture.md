# ADR-001: Initial Architecture and Technology Choices

## Status

Accepted

## Date

2026-02-11

## Context

`example-interactive-installation` is a Markdown-based project within ORGAN-II (Poiesis) of the organvm eight-organ creative-institutional system. The project needed a technology foundation that balances rapid prototyping with long-term maintainability, aligning with the organ system's emphasis on portfolio-quality engineering.

## Decision

We chose Markdown as the primary implementation language, leveraging its ecosystem for the specific domain requirements of this project. The project follows the organvm repository standards (documented in `docs/standards/10-repository-standards.md` of the planning corpus) and integrates with the cross-organ dependency graph maintained in `registry-v2.json`.

Key architectural choices:
- **Language**: Markdown — selected for ecosystem fit and team expertise
- **CI/CD**: GitHub Actions with graceful degradation (tests, linting, type checking)
- **Documentation**: Portfolio-quality README (4,500+ words) targeting grant reviewers and hiring managers
- **Governance**: Follows ORGAN-IV orchestration rules; no back-edges in dependency graph

## Consequences

### Positive

- Consistent with organvm system-wide conventions
- CI pipeline catches regressions early with continue-on-error for non-critical checks
- Documentation-first approach ensures discoverability and portfolio value

### Negative

- Minimal tooling support may require custom CI configuration
- Portfolio-quality documentation requires ongoing maintenance as the project evolves

## References

- Part of the [organvm eight-organ system](https://github.com/meta-organvm)
- Organ: ORGAN-II (Poiesis)
- Registry: `registry-v2.json` in [organvm-corpvs-testamentvm](https://github.com/meta-organvm/organvm-corpvs-testamentvm)
