# ADR 0001: Windows-First Monorepo Foundation

## Status

Accepted

## Context

The platform is a greenfield local AI agent and must support deep Windows automation first, while remaining extensible for future cross-platform support.

## Decision

- Use a monorepo with `apps`, `services`, `packages`, `infra`, `docs`, and `tests`.
- Use Python as the primary implementation language for the runtime and automation layers.
- Keep shared domain models in `packages/core`.
- Keep environment-aware configuration in `packages/config`.
- Treat safety and auditability as platform-level concerns rather than per-feature add-ons.

## Consequences

- Feature modules can be added without reworking the repository layout.
- Shared contracts are centralized early, which reduces drift.
- Windows-specific adapters can live behind stable interfaces.
