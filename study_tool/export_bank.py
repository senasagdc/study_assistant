"""Bir PDF/chapter'ın sorularını SQLite'tan import'un okuduğu JSON biçiminde dışa aktarır."""

import argparse
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from study_tool.quiz import find_chapter
from study_tool.schema import validate_question
from study_tool.storage import DEFAULT_DB_PATH, connect_db


def export_questions(connection, chapter_id):
    """Chapter'daki her sorunun son sürümünü, eklenme sırasıyla liste olarak döndürür."""
    start, end = connection.execute(
        "SELECT start_page, end_page FROM chapters WHERE id = ?", (chapter_id,)
    ).fetchone()
    allowed = set(range(start, end + 1))
    rows = connection.execute(
        "SELECT q.original_id, v.question_json FROM bank_questions q "
        "JOIN question_versions v ON v.question_id = q.id WHERE q.chapter_id = ? "
        "AND v.version_no = (SELECT MAX(version_no) FROM question_versions WHERE question_id = q.id) "
        "ORDER BY q.id",
        (chapter_id,),
    ).fetchall()
    questions = []
    for original_id, content in rows:
        question = json.loads(content)
        if question.get("id") != original_id:
            raise ValueError(f"Soru {original_id}: JSON içindeki id kayıtla eşleşmiyor.")
        errors = validate_question(question, allowed)
        if errors:
            raise ValueError(f"Soru {original_id}: {'; '.join(errors)}")
        questions.append(question)
    return questions


def write_new_json(path, data):
    """Dosya yoksa atomik olarak yazar; varsa üzerine yazmaz."""
    path = Path(path)
    if path.exists():
        raise ValueError(f"{path} zaten var; üzerine yazılmadı. Başka bir dosya adı ver.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        # os.link hedef varsa hata verir; böylece arada oluşan bir dosya da ezilmez.
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="PDF/chapter sorularını SQLite'tan JSON'a aktar.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("chapter", type=int)
    parser.add_argument("output_json", type=Path, help="Yeni dosya; var olan dosyanın üzerine yazılmaz")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    if not args.db.is_file():
        parser.exit(1, f"Database bulunamadı: {args.db}\n")
    connection = None
    try:
        connection = connect_db(args.db)
        chapter_id = find_chapter(connection, args.pdf, args.chapter)
        questions = export_questions(connection, chapter_id)
        write_new_json(args.output_json, questions)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        parser.exit(1, f"Export başarısız: {error}\n")
    finally:
        if connection is not None:
            connection.close()
    print(f"{len(questions)} soru yazıldı: {args.output_json.resolve()}")
    print("Database değiştirilmedi. API kullanılmadı.")


if __name__ == "__main__":
    main()
