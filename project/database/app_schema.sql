-- 业务库 schema（SQLAlchemy 启动时自动建表，本文件用于对照）
-- 文件：backend/data/app.db

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL,
  department TEXT,
  project TEXT,
  phone TEXT,
  is_active INTEGER DEFAULT 1,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS hazards (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  level TEXT,
  category TEXT,
  location TEXT,
  project TEXT,
  status TEXT,
  reporter_id TEXT,
  assignee_id TEXT
);

CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT,
  content TEXT,
  answer TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS exam_papers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT,
  status TEXT,
  question_ids_json TEXT
);

CREATE TABLE IF NOT EXISTS exam_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id INTEGER,
  user_id TEXT,
  score REAL,
  status TEXT
);