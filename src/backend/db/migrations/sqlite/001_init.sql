-- schema_migrations to track applied migrations
CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- users table (optional for anonymous use)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- interpretations (existing feature)
CREATE TABLE IF NOT EXISTS interpretations (
  id TEXT PRIMARY KEY,
  user_id TEXT NULL,
  explanation TEXT NOT NULL,
  confidence REAL NOT NULL,
  image_path TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_interpretations_user_created ON interpretations(user_id, created_at);

-- quotas (future)
CREATE TABLE IF NOT EXISTS quotas (
  user_id TEXT PRIMARY KEY,
  period_start TIMESTAMP NOT NULL,
  count INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- voice settings (future)
CREATE TABLE IF NOT EXISTS voice_settings (
  user_id TEXT PRIMARY KEY,
  voice_id TEXT,
  rate REAL,
  pitch REAL,
  volume REAL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
