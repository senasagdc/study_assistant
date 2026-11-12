import json
import tempfile
import unittest
from pathlib import Path

import pymupdf

from study_tool.export_bank import export_questions, write_new_json
from study_tool.import_bank import import_questions, prepare_import
from study_tool.storage import connect_db


def sample_question(identifier, text):
    return dict(id=identifier, type="mcq", question=text,
                options=dict(A="One", B="Two", C="Three", D="Four"),
                correct_answer="B", explanation="Açıklama $x^2$.", topic="Demo", source_pages=[1])


class ExportBankTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.pdf = self.root / "demo.pdf"
        self.extracted = self.root / "demo.json"
        self.bank = self.root / "bank.json"
        with pymupdf.open() as document:
            document.new_page().insert_text((72, 72), "Demo chapter")
            document.save(self.pdf)
        self.extracted.write_text(json.dumps(dict(chapters=[dict(
            chapter=1, pages=[dict(page=1, text="Demo chapter")])])), encoding="utf-8")
        self.questions = [sample_question("q1", "First?"), sample_question("q2", "Second?")]
        self.bank.write_text(json.dumps(self.questions), encoding="utf-8")

    def open_db(self, name):
        connection = connect_db(self.root / name)
        self.addCleanup(connection.close)
        return connection

    def test_export_then_import_into_empty_db_round_trips(self):
        first = self.open_db("first.db")
        chapter_id = import_questions(first, prepare_import(self.pdf, self.extracted, 1, self.bank))["chapter_id"]
        exported = self.root / "export.json"
        write_new_json(exported, export_questions(first, chapter_id))
        self.assertEqual(json.loads(exported.read_text(encoding="utf-8")), self.questions)

        second = self.open_db("second.db")
        report = import_questions(second, prepare_import(self.pdf, self.extracted, 1, exported))
        self.assertEqual(report["added"], 2)
        self.assertEqual(export_questions(second, report["chapter_id"]), self.questions)

    def test_export_uses_latest_version(self):
        db = self.open_db("study.db")
        chapter_id = import_questions(db, prepare_import(self.pdf, self.extracted, 1, self.bank))["chapter_id"]
        fixed = dict(self.questions[0], correct_answer="C")
        with db:
            db.execute(
                "INSERT INTO question_versions (question_id, version_no, question_json, change_reason) "
                "SELECT id, 2, ?, 'Fix' FROM bank_questions WHERE original_id = 'q1'",
                (json.dumps(fixed),),
            )
        self.assertEqual(export_questions(db, chapter_id), [fixed, self.questions[1]])

    def test_existing_file_is_not_overwritten(self):
        self.bank.write_text("ORIGINAL", encoding="utf-8")
        with self.assertRaises(ValueError):
            write_new_json(self.bank, [])
        self.assertEqual(self.bank.read_text(encoding="utf-8"), "ORIGINAL")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         ["bank.json", "demo.json", "demo.pdf"])


if __name__ == "__main__":
    unittest.main()
