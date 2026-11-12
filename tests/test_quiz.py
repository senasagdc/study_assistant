import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pymupdf

from study_tool.import_bank import import_questions, prepare_import
from study_tool.manage import add_user
from study_tool.quiz import find_chapter, load_chapter_questions, record_answer, run_quiz
from study_tool.storage import connect_db


def sample_question(identifier="q1", text="Which option?"):
    return dict(id=identifier, type="mcq", question=text,
                options=dict(A="One", B="Two", C="Three", D="Four"),
                correct_answer="A", explanation="Demo.", topic="Demo", source_pages=[1])


class QuizTests(unittest.TestCase):
    """input() sahte cevaplarla değiştirilir; geçici database kullanılır."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        self.pdf = root / "demo.pdf"
        extracted = root / "demo.json"
        bank = root / "demo_ch1_questions.json"
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((72, 72), "Demo chapter")
            document.save(self.pdf)
        extracted.write_text(json.dumps(dict(source="demo.pdf", chapters=[dict(
            chapter=1, pages=[dict(page=1, text="Demo chapter")])])), encoding="utf-8")
        bank.write_text(json.dumps([sample_question(), sample_question("q2", "Second?")]),
                        encoding="utf-8")
        self.db = connect_db(root / "test.db")
        self.addCleanup(self.db.close)
        import_questions(self.db, prepare_import(self.pdf, extracted, 1, bank))
        self.user_id = add_user(self.db, "Sena")

    def play(self, answers):
        items = load_chapter_questions(self.db, find_chapter(self.db, self.pdf, 1))
        with patch("builtins.input", side_effect=answers), redirect_stdout(io.StringIO()):
            return run_quiz(self.db, items, self.user_id)

    def attempts(self):
        return self.db.execute(
            "SELECT question_version_id, selected_answer, is_correct "
            "FROM answer_attempts WHERE user_id = ? ORDER BY id", (self.user_id,)).fetchall()

    def test_each_answer_saved_with_version_and_correctness(self):
        result = self.play(["a", "B"])
        self.assertEqual(result, dict(answered=2, correct=1))
        self.assertEqual(self.attempts(), [(1, "A", 1), (2, "B", 0)])

    def test_invalid_input_ignored_and_quit_keeps_earlier_answers(self):
        result = self.play(["x", "A", "q"])
        self.assertEqual(result["answered"], 1)
        self.assertEqual(self.attempts(), [(1, "A", 1)])

    def test_latest_version_is_asked_and_graded(self):
        changed = dict(sample_question(), correct_answer="B")
        with self.db:
            self.db.execute(
                "INSERT INTO question_versions (question_id, version_no, question_json, change_reason) "
                "VALUES (1, 2, ?, 'Answer key fixed')", (json.dumps(changed),))
        self.play(["B", "Q"])
        self.assertEqual(self.attempts(), [(3, "B", 1)])

    def test_answer_requires_user(self):
        with self.assertRaisesRegex(ValueError, "kullanıcı"):
            record_answer(self.db, 1, "A", None)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM answer_attempts").fetchone()[0], 0)

    def test_unknown_pdf_rejected(self):
        other = self.pdf.with_name("other.pdf")
        other.write_bytes(b"different content")
        with self.assertRaisesRegex(ValueError, "database'de yok"):
            find_chapter(self.db, other, 1)
        with self.assertRaisesRegex(ValueError, "database'de yok"):
            find_chapter(self.db, self.pdf, 2)


if __name__ == "__main__":
    unittest.main()
