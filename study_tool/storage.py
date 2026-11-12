import hashlib
import json
import sqlite3
from pathlib import Path

from study_tool.schema import OPTION_KEYS, validate_question

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "study.db"
SCHEMA_PATH = Path(__file__).with_name("database_schema.sql")


def connect_db(path=DEFAULT_DB_PATH):
    """Database bağlantısını açar ve gerekli tabloları oluşturur."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            source_file TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            question_json TEXT NOT NULL,
            UNIQUE(source_file, content_hash)
        );
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY,
            question_id INTEGER NOT NULL REFERENCES questions(id),
            selected_answer TEXT NOT NULL CHECK(selected_answer IN ('A', 'B', 'C', 'D')),
            is_correct INTEGER NOT NULL CHECK(is_correct IN (0, 1)),
            answered_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );
    """)
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    migrate(connection)
    return connection


# Her migration bir kez çalışır; hangisine kadar gelindiği PRAGMA user_version'da tutulur.
MIGRATIONS = [
    # 1: dersler ve kullanıcılar
    """
    ALTER TABLE documents ADD COLUMN course_id INTEGER REFERENCES courses(id);
    ALTER TABLE answer_attempts ADD COLUMN user_id INTEGER REFERENCES users(id);
    """,
]


def migrate(connection):
    """Eksik migration'ları sırayla ve her birini tek transaction içinde uygular."""
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
        try:
            connection.execute("BEGIN IMMEDIATE")
            for statement in filter(str.strip, script.split(";")):
                connection.execute(statement)
            connection.execute(f"PRAGMA user_version = {number}")
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise


def save_question(connection, question, source_file):
    """Soruyu kaydeder; aynı kaynak ve içerik varsa mevcut database id'sini döndürür."""
    errors = validate_question(question)
    if errors:
        raise ValueError("; ".join(errors))
    content = json.dumps(question, ensure_ascii=False, sort_keys=True)
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    source = str(Path(source_file).resolve())
    with connection:
        connection.execute(
            "INSERT INTO questions (source_file, content_hash, question_json) "
            "VALUES (?, ?, ?) ON CONFLICT(source_file, content_hash) DO NOTHING",
            (source, content_hash, content),
        )
        row = connection.execute(
            "SELECT id FROM questions WHERE source_file = ? AND content_hash = ?",
            (source, content_hash),
        ).fetchone()
    return row[0]


def save_attempt(connection, question_id, selected_answer):
    """Cevabı kaydeder; doğruluğu database'deki soru anahtarından hesaplar."""
    if selected_answer not in OPTION_KEYS:
        raise ValueError("Cevap A, B, C veya D olmalı.")
    row = connection.execute(
        "SELECT question_json FROM questions WHERE id = ?", (question_id,)
    ).fetchone()
    if row is None:
        raise ValueError("Soru database'de bulunamadı.")
    is_correct = selected_answer == json.loads(row[0])["correct_answer"]
    with connection:
        cursor = connection.execute(
            "INSERT INTO attempts (question_id, selected_answer, is_correct) VALUES (?, ?, ?)",
            (question_id, selected_answer, int(is_correct)),
        )
    return cursor.lastrowid
