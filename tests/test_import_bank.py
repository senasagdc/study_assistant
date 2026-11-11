import json
import tempfile
import unittest
from pathlib import Path

import pymupdf

from study_tool.import_bank import import_questions, prepare_import
from study_tool.storage import connect_db


def sample_question(identifier="q1", text="Which option?"):
    return dict(id=identifier, type="mcq", question=text,
                options=dict(A="One", B="Two", C="Three", D="Four"),
                correct_answer="A", explanation="Demo.", topic="Demo", source_pages=[1])


class ImportBankTests(unittest.TestCase):
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
        self.write_bank([sample_question()])
        self.db = connect_db(root / "test.db")
        self.addCleanup(self.db.close)

    def write_bank(self, questions):
        self.bank.write_text(json.dumps(questions), encoding="utf-8")

    def prepare(self):
        return prepare_import(self.pdf, self.extracted, 1, self.bank)

    def test_repeat_import_and_renamed_pdf_preserve_ids_and_sources(self):
        sources = [p.read_bytes() for p in (self.pdf, self.extracted, self.bank)]
        first = import_questions(self.db, self.prepare())
        renamed = self.pdf.with_name("renamed.pdf")
        renamed.write_bytes(self.pdf.read_bytes())
        second = import_questions(self.db, prepare_import(renamed, self.extracted, 1, self.bank))
        self.assertEqual(first["added"], 1)
        self.assertEqual(second["added"], 0)
        self.assertEqual(second["unchanged"], 1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM generations").fetchone()[0], 1)
        content = self.db.execute("SELECT question_json FROM question_versions").fetchone()[0]
        self.assertEqual(json.loads(content), sample_question())
        self.assertEqual([p.read_bytes() for p in (self.pdf, self.extracted, self.bank)], sources)

    def test_later_import_adds_only_new_questions(self):
        import_questions(self.db, self.prepare())
        self.write_bank([sample_question(), sample_question("q2", "Second?"),
                         sample_question("q3", " WHICH   OPTION? ")])
        report = import_questions(self.db, self.prepare())
        self.assertEqual((report["added"], report["unchanged"], report["duplicate"], report["total"]), (1, 1, 1, 2))

    def test_conflict_rolls_back_even_preceding_insert(self):
        import_questions(self.db, self.prepare())
        self.write_bank([sample_question("q2", "Second?"),
                         dict(sample_question(), correct_answer="B")])
        with self.assertRaisesRegex(ValueError, "kayıtlı içerik farklı"):
            import_questions(self.db, self.prepare())
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM bank_questions").fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM generations").fetchone()[0], 1)

    def test_mismatched_pdf_and_invalid_bank_rejected(self):
        original = self.extracted.read_text()
        self.extracted.write_text(original.replace("Demo chapter", "Wrong content"))
        with self.assertRaisesRegex(ValueError, "eşleşmiyor"):
            self.prepare()
        self.extracted.write_text(original)
        self.write_bank([dict(sample_question(), source_pages=[99])])
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 0)

    def test_changed_chapter_range_rolls_back(self):
        prepared = self.prepare()
        import_questions(self.db, prepared)
        with self.assertRaisesRegex(ValueError, "sayfa aralığı farklı"):
            import_questions(self.db, dict(prepared, end_page=2))
        self.assertEqual(self.db.execute("SELECT end_page FROM chapters").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
