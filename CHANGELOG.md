# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-07-11

### Added
- **Phase 2 Orchestrator Release** — initial release of the Phase 2 orchestration layer.
- Core orchestrator engine for managing multi-step workflow execution.
- Support for parallel and sequential task scheduling.
- Built-in retry logic and error-handling policies for orchestrated tasks.
- Observability hooks: structured logging and trace context propagation.
- Configuration-driven pipeline definitions via YAML manifests.

### Changed
- Project structure updated to support orchestrator module layout.

### Notes
- This is the first stable release of the Phase 2 orchestrator. Earlier Phase 1 work
  is captured in the project history but not reflected in this changelog.
