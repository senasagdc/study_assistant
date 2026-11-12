import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import pymupdf

from study_tool.import_bank import import_questions, prepare_import
from study_tool.manage import (add_course, add_user, claim_attempts, get_user_id,
                               overview, set_course)
from study_tool.storage import MIGRATIONS, connect_db


def sample_question(identifier="q1", text="Which option?"):
    return dict(id=identifier, type="mcq", question=text,
                options=dict(A="One", B="Two", C="Three", D="Four"),
                correct_answer="A", explanation="Demo.", topic="Demo", source_pages=[1])


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "study.db"

    def columns(self, connection, table):
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}

    def test_old_database_gets_new_columns_and_keeps_data(self):
        # 12 Kasım öncesi yapı: course_id ve user_id sütunları yok, user_version 0.
        with closing(sqlite3.connect(self.path)) as old:
            old.executescript("""
                CREATE TABLE documents (id INTEGER PRIMARY KEY, content_hash TEXT NOT NULL UNIQUE,
                    filename TEXT NOT NULL, course TEXT, week INTEGER,
                    created_at TEXT NOT NULL DEFAULT 'x');
                CREATE TABLE answer_attempts (id INTEGER PRIMARY KEY,
                    question_version_id INTEGER NOT NULL, selected_answer TEXT NOT NULL,
                    is_correct INTEGER NOT NULL, answered_at TEXT NOT NULL DEFAULT 'x');
                INSERT INTO documents (content_hash, filename) VALUES ('h', 'week5.pdf');
                INSERT INTO answer_attempts (question_version_id, selected_answer, is_correct)
                    VALUES (1, 'A', 1);
            """)
        db = connect_db(self.path)
        try:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], len(MIGRATIONS))
            self.assertIn("course_id", self.columns(db, "documents"))
            self.assertIn("user_id", self.columns(db, "answer_attempts"))
            self.assertEqual(db.execute("SELECT filename, course_id FROM documents").fetchall(),
                             [("week5.pdf", None)])
            self.assertEqual(db.execute("SELECT selected_answer, user_id FROM answer_attempts").fetchall(),
                             [("A", None)])
        finally:
            db.close()
        connect_db(self.path).close()  # ikinci açılış migration'ı tekrar çalıştırmaz

    def test_new_database_is_at_latest_version(self):
        db = connect_db(self.path)
        try:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], len(MIGRATIONS))
            self.assertIn("course_id", self.columns(db, "documents"))
        finally:
            db.close()


class CourseAndUserTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        self.pdf = root / "demo.pdf"
        self.extracted = root / "demo.json"
        self.bank = root / "demo_ch1_questions.json"
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((72, 72), "Demo chapter")
            document.save(self.pdf)
        self.extracted.write_text(json.dumps(dict(chapters=[dict(
            chapter=1, pages=[dict(page=1, text="Demo chapter")])])), encoding="utf-8")
        self.bank.write_text(json.dumps([sample_question()]), encoding="utf-8")
        self.db = connect_db(root / "test.db")
        self.addCleanup(self.db.close)

    def prepare(self):
        return prepare_import(self.pdf, self.extracted, 1, self.bank)

    def course_of_document(self):
        return self.db.execute(
            "SELECT c.name FROM documents d LEFT JOIN courses c ON c.id = d.course_id").fetchone()[0]

    def test_names_are_unique_ignoring_case(self):
        add_course(self.db, "Quality Management")
        with self.assertRaisesRegex(ValueError, "zaten kayıtlı"):
            add_course(self.db, "quality management")
        add_user(self.db, "Sena")
        self.assertEqual(get_user_id(self.db, "SENA"), 1)
        with self.assertRaisesRegex(ValueError, "add-user"):
            get_user_id(self.db, "Ali")

    def test_import_links_course_and_refuses_moving_it(self):
        add_course(self.db, "Quality Management")
        add_course(self.db, "Operations Research")
        report = import_questions(self.db, self.prepare(), course="Quality Management")
        self.assertEqual(report["course"], "Quality Management")

        self.bank.write_text(json.dumps([sample_question(), sample_question("q2", "Second?")]),
                             encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "başka bir derse"):
            import_questions(self.db, self.prepare(), course="Operations Research")
        self.assertEqual(self.course_of_document(), "Quality Management")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM bank_questions").fetchone()[0], 1)

    def test_unknown_course_rolls_back_import(self):
        with self.assertRaisesRegex(ValueError, "add-course"):
            import_questions(self.db, self.prepare(), course="Typo Course")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 0)

    def test_existing_document_and_old_answers_can_be_assigned(self):
        import_questions(self.db, self.prepare())
        self.assertIsNone(self.course_of_document())
        add_course(self.db, "Quality Management")
        set_course(self.db, self.pdf, "Quality Management")
        self.assertEqual(self.course_of_document(), "Quality Management")

        with self.db:
            self.db.execute("INSERT INTO answer_attempts (question_version_id, selected_answer, "
                            "is_correct) VALUES (1, 'A', 1)")
        add_user(self.db, "Sena")
        self.assertEqual(claim_attempts(self.db, "Sena"), 1)
        self.assertEqual(claim_attempts(self.db, "Sena"), 0)
        self.assertIn("  Sena: 1 cevap", overview(self.db))
        self.assertIn("  Quality Management: 1 PDF, 1 soru", overview(self.db))


if __name__ == "__main__":
    unittest.main()
