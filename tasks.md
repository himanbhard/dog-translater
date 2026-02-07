# Production Readiness Tasks

## 1. Structured Logging
- [ ] Install `python-json-logger` (or use standard library with custom formatter).
- [ ] Configure `src/backend/server.py` to output logs in JSON format instead of plain text.
- [ ] Ensure fields like `severity`, `message`, and `component` are present for Cloud Logging compatibility.

## 2. Cold Start Optimization
- [ ] Refactor `src/backend/gemini_client.py` to lazy-load Vertex AI and GenerativeModel.
    - [ ] Remove top-level `vertexai.init` and model instantiation.
    - [ ] specific initialization function or usage of `startup_event`.
- [ ] Refactor `src/backend/server.py` startup to avoid heavy synchronous blocking calls if possible.

## 3. Firebase Auth & Security audits
- [ ] Update `src/backend/auth.py` to explicitly catch `firebase_admin.auth.ExpiredIdTokenError` and `RevokedIdTokenError`.
- [ ] Ensure 401 Unauthorized is returned with specific detail vs generic 500.
- [ ] Validate middleware allows/blocks correctly.

## 4. Health Checks & Production Standard
- [ ] Add `/healthz` alias to existing `/health` endpoint in `src/backend/server.py`.
- [ ] Ensure health check verifies DB connectivity (already initiated, verify robustness).

## 5. cloud Run Configuration & Scaling
- [ ] Dockerfile: Ensure `gunicorn` or `uvicorn` with workers is configured if heavily loaded (though `uvicorn` single process is default for basic containers, standard is usually Gunicorn+Uvicorn for managing workers, but generally for Cloud Run single-process concurrency is preferred if using async). We will stick to `uvicorn` async.
- [ ] Database: Document the migration path from SQLite (current) to Cloud SQL (PostgreSQL) for stateless scaling.
