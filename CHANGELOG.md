# Changelog

All notable changes to the OPC200 project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.5.0] - 2026-04-13

### Changed (Breaking)
- **LLM-first architecture for `opc-journal`**: removed all hardcoded local interpretation layers. The skill now acts as a pure data layer, returning raw signals and context for the caller (LLM) to interpret dynamically.
  - `analyze` — returns `raw_text`, `signal_summary`, and file metadata instead of pre-baked emotional/work/decision interpretations.
  - `insights` — returns raw memory context and recent file metadata instead of fixed theme/recommendation pairs.
  - `milestones` — returns a raw `candidate` object instead of keyword-based milestone detection.
  - `record` — removes auto-emotion analysis (`_analyze_emotion`); defers emotional interpretation to the caller.
  - `init` — generates a minimal charter without hardcoded motivational quotes or bilingual blocks.
  - `status` — returns raw statistics (`total_entries`, `latest_entry_date`, `journal_active`) and defers message generation to the caller.

### Fixed
- Aligned `VERSION` file, `SKILL.md`, `config.yml`, and generated charter metadata to the correct release version (2.5.0).

---

## [2.4.0] - 2026-04-11

### Changed
- **Skill restructure**: collapsed `opc-journal-suite` (5 sub-skills + coordinator) into a single CLI skill `opc-journal`.
- **Localization**: added Chinese language support across all commands and retroactive document translation via `update-meta`.
- **Deployment**: added `Dockerfile.allinone`, cloud multi-tenant compose, and on-premise compose configurations.
- **Operations**: added `docs/SLA.md`, Prometheus/Grafana monitoring dashboards, and enhanced health-check/backup scripts.

### Added
- `update-meta` command with retroactive translation support when switching languages.
- Daily `.bak` backup mechanism for journal entries with structured frontmatter.
- Dynamic language-aware i18n layer with language persistence in customer meta.
- Improved Day 1 onboarding experience with charter generation.

### Fixed
- 5 failing integration tests fixed; full test suite green (227 passed).
- Removed all remaining references from `opc-journal-suite` to `opc-journal`.
- Standardized `SKILL.md` frontmatter YAML format for ClawHub compatibility.

---

## [2.3.0] - 2026-04-01

### Added
- **Cron Scheduler** — Autonomous scheduled task execution for journal operations
  - Pre-configured schedules: daily summary (8:00 AM), weekly pattern analysis (Sunday 9:00 AM), milestone check (9:00 PM), memory compaction reminder (11:00 PM)
  - Intent-based routing with natural language triggers
  - 9 comprehensive unit tests

- **Learning Tracker** — Three-confirmation learning mechanism
  - 1st occurrence → daily memory
  - 3rd occurrence → project memory
  - 10th occurrence → permanent memory
  - 9 comprehensive unit tests

- **Deployment Templates**
  - Cloud deployment template (Kubernetes configuration)
  - Edge deployment template (Docker Compose configuration)

- **Operations Scripts Test Suite**
  - Full validation test suite for ops scripts
  - 34 test cases covering `health-check.sh`, `backup-manager.sh`, `emergency-recovery.sh`
  - Performance benchmarks (< 1s startup time)

- **Enhanced API Documentation**
  - Complete Python library API reference
  - Module documentation: Journal, Tasks, Insights, Patterns, Security
  - Data models and error handling guides
  - Comprehensive usage examples

### Fixed
- ClawHub review issues: removed unimplemented notification configurations
- Import error in milestone tracker (removed non-existent notify module)
- Documentation consistency across all skill modules
- Script executable permissions (`backup-manager.sh`, `emergency-recovery.sh`)
- `detect-secrets` CI failures with proper baseline configuration
- Invalid qdrant health checks in docker-compose files

### Changed
- **Version unification**: All project documents and skills aligned to v2.3.0
- Skills refactored to pure Python using only the standard library (removed `src.*` dependencies)
- Documentation structure improved with a single source of truth
- Updated OpenClaw Gateway image reference to `ghcr.io/openclaw/openclaw`

---

## [2.2.0] - 2024-03-24

### Added
- TDD infrastructure with comprehensive test suite
  - Unit tests for all core modules
  - Integration tests for database and security flows
  - End-to-end tests for user journeys
- CI/CD pipeline with GitHub Actions
  - Continuous integration workflow
  - Security audit workflow
  - Staging and production deployment workflows
- Docker support
  - `Dockerfile.test` for testing environment
  - `Dockerfile.prod` for production environment
  - `docker-compose` configurations
- Code quality tools
  - Black code formatting
  - isort import sorting
  - flake8 linting
  - mypy type checking
  - pylint static analysis
  - pre-commit hooks
- Core Python modules
  - `journal.core`: JournalEntry class and JournalManager
  - `journal.storage`: SQLite storage backend with migrations
  - `journal.vector_store`: Qdrant integration for semantic search
  - `security.vault`: Data vault with access control
  - `security.encryption`: AES-256-GCM encryption
  - `patterns.analyzer`: Behavior pattern detection
  - `tasks.scheduler`: Async task scheduling
  - `insights.generator`: Insight and recommendation generation

### Security
- Data vault architecture for sensitive information
- Encryption at rest using AES-256-GCM
- Key management with rotation support
- Access control with time-based restrictions
- Audit logging for all vault access
- Password hashing using PBKDF2

---

## [2.1.0] - 2024-03-21

### Added
- Initial project structure
- OPC Journal Suite skill definitions
- Documentation structure
- Deployment scripts

---

## [2.0.0] - 2024-03-15

### Added
- Project initialization
- Architecture documentation
- Tailscale VPN integration design

---

## Unreleased

### Changed
- Aligned project status documents for a single source of truth:
  - Updated `EXECUTIVE_SUMMARY.md` to match latest audit conclusions (A- / 94.5 / ~90%)
  - Updated `DEVELOPMENT_PLAN.md` progress and acceptance checklist statuses
  - Updated `PROJECT_STATUS.md` metadata and action priorities
s
rities
