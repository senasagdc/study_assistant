-- Eski questions / attempts prototip tablolarına dokunulmaz.
-- documents.course_id ve answer_attempts.user_id sütunları storage.py içindeki
-- migration ile eklenir (mevcut database'ler de aynı yoldan güncellensin diye).
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(name)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(name)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    content_hash TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    course TEXT,
    week INTEGER CHECK (week > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    chapter_no INTEGER NOT NULL CHECK (chapter_no > 0),
    start_page INTEGER NOT NULL CHECK (start_page > 0),
    end_page INTEGER NOT NULL CHECK (end_page >= start_page),
    UNIQUE (document_id, chapter_no)
);

CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    kind TEXT NOT NULL CHECK (kind IN ('llm', 'import')),
    model TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (id, chapter_id)
);

CREATE TABLE IF NOT EXISTS bank_questions (
    id INTEGER PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    original_id TEXT NOT NULL CHECK (length(trim(original_id)) > 0),
    generation_id INTEGER NOT NULL,
    FOREIGN KEY (generation_id, chapter_id) REFERENCES generations(id, chapter_id),
    UNIQUE (chapter_id, original_id)
);

CREATE TABLE IF NOT EXISTS question_versions (
    id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES bank_questions(id),
    version_no INTEGER NOT NULL CHECK (version_no > 0),
    question_json TEXT NOT NULL,
    change_reason TEXT NOT NULL CHECK (length(trim(change_reason)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (question_id, version_no)
);

CREATE TABLE IF NOT EXISTS answer_attempts (
    id INTEGER PRIMARY KEY,
    question_version_id INTEGER NOT NULL REFERENCES question_versions(id),
    selected_answer TEXT NOT NULL CHECK (selected_answer IN ('A', 'B', 'C', 'D')),
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    answered_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
