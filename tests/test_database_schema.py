import sqlite3
import tempfile
import unittest
from pathlib import Path

from study_tool.storage import connect_db


class DatabaseSchemaTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "study.db"
        self.db = connect_db(self.path)
        self.addCleanup(self.db.close)
        self.db.execute("INSERT INTO documents (content_hash, filename) VALUES ('hash-1', 'week5.pdf')")
        self.db.execute("INSERT INTO chapters (document_id, chapter_no, start_page, end_page) VALUES (1, 1, 1, 30)")
        self.db.execute("INSERT INTO generations (chapter_id, kind) VALUES (1, 'import')")
        self.db.execute("INSERT INTO bank_questions (chapter_id, original_id, generation_id) VALUES (1, 'q1', 1)")
        self.db.execute("INSERT INTO question_versions (question_id, version_no, question_json, change_reason) VALUES (1, 1, '{}', 'Initial import')")
        self.db.commit()

    def test_reopening_preserves_data_and_legacy_tables(self):
        self.db.execute("INSERT INTO questions (source_file, content_hash, question_json) VALUES ('old.json', 'old-hash', '{}')")
        self.db.commit()
        other = connect_db(self.path)
        try:
            self.assertEqual(other.execute("SELECT original_id FROM bank_questions").fetchall(), [('q1',)])
            self.assertEqual(other.execute("SELECT content_hash FROM questions").fetchall(), [('old-hash',)])
        finally:
            other.close()

    def test_unique_pdf_and_valid_page_ranges(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO documents (content_hash, filename) VALUES ('hash-1', 'renamed.pdf')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO chapters (document_id, chapter_no, start_page, end_page) VALUES (1, 2, 20, 10)")

    def test_foreign_key_and_generation_chapter_match(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO answer_attempts (question_version_id, selected_answer, is_correct) VALUES (999, 'A', 1)")
        self.db.execute("INSERT INTO chapters (document_id, chapter_no, start_page, end_page) VALUES (1, 2, 31, 60)")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO bank_questions (chapter_id, original_id, generation_id) VALUES (2, 'q2', 1)")

    def test_answer_stays_attached_to_original_version(self):
        self.db.execute("INSERT INTO answer_attempts (question_version_id, selected_answer, is_correct) VALUES (1, 'A', 0)")
        self.db.execute("INSERT INTO question_versions (question_id, version_no, question_json, change_reason) VALUES (1, 2, '{}', 'Correction')")
        result = self.db.execute("SELECT v.version_no, a.is_correct FROM answer_attempts a JOIN question_versions v ON v.id = a.question_version_id").fetchall()
        self.assertEqual(result, [(1, 0)])

    def test_duplicate_versions_and_invalid_answers_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO question_versions (question_id, version_no, question_json, change_reason) VALUES (1, 1, '{}', 'Duplicate')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO answer_attempts (question_version_id, selected_answer, is_correct) VALUES (1, 'X', 1)")


if __name__ == '__main__':
    unittest.main()
