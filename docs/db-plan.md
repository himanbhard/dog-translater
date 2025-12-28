# Database Architecture & Design Plan

This document outlines the production-ready database architecture for the Dog Translator application. It transitions from a lightweight prototype to a robust, scalable system capable of supporting mobile synchronization, user authentication, and seamless environment switching.

## 1. Architectural Strategy

We will use **SQLAlchemy (AsyncIO)** as the ORM to provide a unified data access layer. This allows us to use **SQLite** for local development and **PostgreSQL** for production with minimal code changes.

### Environment Switching
The application will detect the environment via `src/backend/config.py` and configure the database engine accordingly.

**Configuration Pattern:**

- **Development (`ENV=dev`)**: Uses SQLite.
  - URL: `sqlite+aiosqlite:///./data/app.db`
  - Benefits: Zero-setup, file-based, sufficient for local testing.
- **Production (`ENV=prod`)**: Uses PostgreSQL.
  - URL: `postgresql+asyncpg://user:pass@host:5432/dbname`
  - Benefits: JSONB support, row-level locking, high concurrency, scalable.

The `DatabaseSessionManager` class will handle connection pooling and session lifecycle management, ensuring that the rest of the application remains agnostic to the underlying database engine.

## 2. Data Model Schema

The schema is designed to support users, profiles, and a history of actions/translations. All primary entities include `updated_at` and `is_deleted` fields to support **Offline-First Mobile Synchronization**.

### Core Entities

#### 1. `users`
Represents the authenticated account.

| Column | Type (SQLAlchemy) | Type (Postgres) | Notes |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `UUID` | Primary Key, Default: `uuid4` |
| `email` | `String` | `VARCHAR(255)` | Unique, Indexed, Not Null |
| `password_hash` | `String` | `VARCHAR` | Not Null |
| `is_active` | `Boolean` | `BOOLEAN` | Default: `True` |
| `created_at` | `DateTime` | `TIMESTAMPTZ` | Default: `NOW()` |
| `updated_at` | `DateTime` | `TIMESTAMPTZ` | OnUpdate: `NOW()` |
| `is_deleted` | `Boolean` | `BOOLEAN` | Default: `False` (Soft Delete) |

#### 2. `profiles`
Extended user information. Separated to keep the `users` table lean for auth.

| Column | Type (SQLAlchemy) | Type (Postgres) | Notes |
| :--- | :--- | :--- | :--- |
| `user_id` | `UUID` | `UUID` | PK, FK -> `users.id` |
| `display_name` | `String` | `VARCHAR(100)` | Nullable |
| `avatar_url` | `String` | `TEXT` | Nullable |
| `preferences` | `JSON` | `JSONB` | UI/Voice prefs |
| `updated_at` | `DateTime` | `TIMESTAMPTZ` | OnUpdate: `NOW()` |

#### 3. `history`
A comprehensive log of user actions (e.g., translations, shares).

| Column | Type (SQLAlchemy) | Type (Postgres) | Notes |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `UUID` | Primary Key, Default: `uuid4` |
| `user_id` | `UUID` | `UUID` | FK -> `users.id`, Indexed |
| `action_type` | `String` | `VARCHAR(50)` | e.g., 'TRANSLATE_DOG', 'SHARE' |
| `payload` | `JSON` | `JSONB` | Flexible data (input text, output audio URL, etc.) |
| `created_at` | `DateTime` | `TIMESTAMPTZ` | Default: `NOW()`, Indexed |
| `updated_at` | `DateTime` | `TIMESTAMPTZ` | OnUpdate: `NOW()` |
| `is_deleted` | `Boolean` | `BOOLEAN` | Default: `False` (Soft Delete) |

### Mobile Sync Optimization
- **`updated_at`**: Allows mobile clients to request "changes since [last_sync_timestamp]".
- **`is_deleted`**: Ensures deletions are propagated to clients during sync instead of just disappearing from the feed.

## 3. Data Access Layer (Repository Pattern)

We will implement a Repository Pattern to encapsulate data logic, enabling cleaner API handlers and easier testing.

**Directory Structure:**
```
src/backend/db/
├── base.py          # SQLAlchemy Base and Session management
├── models.py        # SQLAlchemy ORM Models
├── repository.py    # CRUD logic and complex queries
└── migrations/      # Alembic migration scripts
```

**Repository Interface Structure:**

The repository will handle filtering and pagination logic, returning domain objects or Pydantic models.

```python
class HistoryRepository:
    async def get_records(
        self, 
        user_id: UUID, 
        start_date: Optional[datetime], 
        end_date: Optional[datetime],
        page: int = 1, 
        limit: int = 20
    ) -> List[History]:
        query = select(History).where(
            History.user_id == user_id,
            History.is_deleted == False
        )
        
        if start_date:
            query = query.where(History.created_at >= start_date)
        if end_date:
            query = query.where(History.created_at <= end_date)
            
        # Pagination
        query = query.order_by(History.created_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
```

## 4. Migration & Initialization Strategy

We will use **Alembic** for schema migrations. This provides a version-controlled history of database changes and works for both SQLite and Postgres.

### Initialization Scripts

Below are the raw SQL scripts that the Alembic migrations will effectively generate. These can be used for manual verification or seed scripts.

#### PostgreSQL Initialization (Production)

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    display_name VARCHAR(100),
    avatar_url TEXT,
    preferences JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_history_user_created ON history(user_id, created_at);
```

#### SQLite Initialization (Development)

```sql
-- SQLite doesn't have native UUID or JSONB types, but SQLAlchemy handles conversion.
-- Dates are stored as ISO8601 strings.

CREATE TABLE users (
    id CHAR(32) PRIMARY KEY, -- UUID stored as string
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    is_deleted BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE profiles (
    user_id CHAR(32) PRIMARY KEY REFERENCES users(id),
    display_name VARCHAR(100),
    avatar_url TEXT,
    preferences TEXT, -- JSON stored as TEXT
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE history (
    id CHAR(32) PRIMARY KEY,
    user_id CHAR(32) REFERENCES users(id),
    action_type VARCHAR(50) NOT NULL,
    payload TEXT NOT NULL, -- JSON stored as TEXT
    is_deleted BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_history_user_created ON history(user_id, created_at);
```

## 5. Next Steps

1.  **Install Dependencies**: Add `sqlalchemy`, `alembic`, `asyncpg`, `aiosqlite` to `requirements.txt`.
2.  **Scaffold Database Folder**: Create `src/backend/db/base.py` and `models.py`.
3.  **Initialize Alembic**: Run `alembic init` and configure `env.py` to use the app's config.
4.  **Refactor Endpoints**: Update existing API endpoints to use the new Repository instead of direct storage calls.
