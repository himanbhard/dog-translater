# Cloud Run Production Readiness - Implementation Plan

## 1. Structured Logging
Use `python-json-logger` or standard library formatting to output logs as JSON.
This allows Google Cloud Logging to parse severity and metadata.

**Goal:** Provide structured logs with `severity`, `message`, `timestamp`, and traceback (if exception).

## 2. Cold Start Optimization
Currently, `vertexai.init()` and `GenerativeModel()` run at `import` time. This significantly delays container startup.
**Plan:**
- Wrap `vertexai.init()` and model loading in a helper function or `@lru_cache` so it runs only on first request (lazy) or during the dedicated `on_startup` event.
- For Cloud Run, lazy loading is preferred to minimize startup time unless latency critical on first request. We will use a dedicated function call on first request.

## 3. Firebase Auth Resilience
Refactor `verify_id_token` in `src/backend/auth.py`:
- Explicitly catch `ExpiredIdTokenError`.
- Explicitly catch `RevokedIdTokenError`.
- Ensure fallback to generic `ValueError` or `AuthorizationError` returns strict 401.

## 4. Health Check Standardization
- Alias `/health` -> `/healthz` (standard Kubernetes/GCP convention).
- Keep existing lightweight DB probe.
- Add basic connectivity check for critical dependencies if possible (optional).

## 5. Scaling Strategy
- Currently using SQLite (`data/app.db`). This is **stateful** and not scalable on Cloud Run (only 1 instance writable or data loss).
- **Recommendation:** Use Cloud SQL (PostgreSQL/MySQL) for production.
- **Action:** Update `src/backend/config.py` and `db/deps.py` to allow switching to `postgres://` or `mysql://` via environment variable `DB_BACKEND=postgres`. (Since we don't have a PG instance, we'll implement the configuration path but default to SQLite for dev/demo).
