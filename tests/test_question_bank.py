import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from study_tool.question_bank import append_questions


def question(text="First question?"):
    return dict(id="model-id", type="mcq", question=text,
                options=dict(A="One", B="Two", C="Three", D="Four"),
                correct_answer="A", explanation="Demo açıklama.",
                topic="Demo", source_pages=[1])


class QuestionBankTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "chapter_questions.json"

    def test_append_preserves_old_records_and_skips_duplicates_and_invalid(self):
        append_questions(self.path, [question()], {1})
        original = json.loads(self.path.read_text())
        invalid = dict(question("Invalid?"), source_pages=[2])
        report = append_questions(self.path, [
            question(" FIRST   QUESTION? "), question("Second?"),
            question("second?"), invalid, None,
        ], {1})
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved[:1], original)
        self.assertEqual(report, dict(existing=1, added=1, invalid=2, duplicate=2, total=2))
        self.assertNotEqual(saved[0]["id"], saved[1]["id"])

    def test_corrupt_bank_is_not_overwritten(self):
        self.path.write_text("broken json")
        with self.assertRaises(ValueError):
            append_questions(self.path, [question()], {1})
        self.assertEqual(self.path.read_text(), "broken json")

    def test_failed_replace_preserves_bank(self):
        append_questions(self.path, [question()], {1})
        original = self.path.read_bytes()
        with patch("study_tool.question_bank.os.replace", side_effect=OSError("Demo failure")):
            with self.assertRaises(OSError):
                append_questions(self.path, [question("New?")], {1})
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_no_accepted_questions_leaves_file_unchanged(self):
        append_questions(self.path, [question()], {1})
        original = self.path.read_bytes()
        append_questions(self.path, [question()], {1})
        self.assertEqual(self.path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
