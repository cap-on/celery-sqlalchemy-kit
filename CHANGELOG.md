# Changelog


## [0.2.0] - 2025-11-11
### Added
- Resilience: scheduler survives transient DB outages and auto-recovers.
  - New `_safe_renew()` in `scheduler.py` to dispose/renew sessions safely.
  - Exponential backoff connect loop in `SessionWrapper._establish_session_with_retry()`.

### Changed
- SQLAlchemy support: compatibility with **2.0.44** tested.
- Celery dependency relaxed and tested up to **5.5.3**.
- `get_schedule()` and `sync()` now avoid recursion; return `{}` on DB outage to pause scheduling for the current tick.

### Fixed
- Avoid crashes when DB connection drops mid-query; beat continues ticking and retries.

### Notes
- Returning `{}` on outage prevents duplicate fires after recovery. Switch to cached schedule if you accept that risk.

## [0.1.3] - 2023-08-08
### Added
- Initial published version with DB-backed Celery Beat scheduler, CRUD helpers, and basic tests.