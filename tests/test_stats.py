import json
import tempfile
import unittest
from pathlib import Path

import pymupdf

from study_tool.import_bank import import_questions, prepare_import
from study_tool.manage import add_course, add_user
from study_tool.quiz import find_chapter, load_chapter_questions, record_answer
from study_tool.stats import due_items, last_results, topic_report
from study_tool.storage import connect_db


def sample_question(identifier, text, topic):
    return dict(id=identifier, type="mcq", question=text,
                options=dict(A="One", B="Two", C="Three", D="Four"),
                correct_answer="A", explanation="Demo.", topic=topic, source_pages=[1])


class StatsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        self.pdf = root / "demo.pdf"
        extracted = root / "demo.json"
        bank = root / "bank.json"
        with pymupdf.open() as document:
            document.new_page().insert_text((72, 72), "Demo chapter")
            document.save(self.pdf)
        extracted.write_text(json.dumps(dict(chapters=[dict(
            chapter=1, pages=[dict(page=1, text="Demo chapter")])])), encoding="utf-8")
        bank.write_text(json.dumps([
            sample_question("q1", "First?", "Control charts"),
            sample_question("q2", "Second?", "control  CHARTS"),
            sample_question("q3", "Third?", "Reliability"),
        ]), encoding="utf-8")
        self.db = connect_db(root / "test.db")
        self.addCleanup(self.db.close)
        add_course(self.db, "Quality")
        import_questions(self.db, prepare_import(self.pdf, extracted, 1, bank), course="Quality")
        self.sena = add_user(self.db, "Sena")
        self.ali = add_user(self.db, "Ali")
        self.chapter_id = find_chapter(self.db, self.pdf, 1)
        self.items = load_chapter_questions(self.db, self.chapter_id)
        self.version = {q["id"]: v for v, q in self.items}

    def answer(self, user_id, question, letter):
        record_answer(self.db, self.version[question], letter, user_id)

    def due_ids(self, user_id):
        return [q["id"] for _, q in due_items(self.db, self.items, user_id)]

    def test_due_uses_latest_answer_per_user(self):
        self.assertEqual(self.due_ids(self.sena), ["q1", "q2", "q3"])
        self.answer(self.sena, "q1", "B")
        self.answer(self.sena, "q1", "A")
        self.answer(self.sena, "q2", "A")
        self.answer(self.sena, "q2", "C")
        self.answer(self.sena, "q3", "A")
        self.assertEqual(self.due_ids(self.sena), ["q2"])
        self.assertEqual(self.due_ids(self.ali), ["q1", "q2", "q3"])

    def test_new_version_keeps_answer_history(self):
        self.answer(self.sena, "q1", "A")
        with self.db:
            self.db.execute(
                "INSERT INTO question_versions (question_id, version_no, question_json, change_reason) "
                "SELECT question_id, 2, question_json, 'Fix' FROM question_versions WHERE id = ?",
                (self.version["q1"],),
            )
        items = load_chapter_questions(self.db, self.chapter_id)
        self.assertNotIn("q1", [q["id"] for _, q in due_items(self.db, items, self.sena)])
        self.assertEqual(list(last_results(self.db, self.sena).values()), [True])

    def test_topic_report_groups_and_orders_weakest_first(self):
        self.answer(self.sena, "q1", "B")
        self.answer(self.sena, "q1", "A")
        self.answer(self.sena, "q2", "B")
        self.answer(self.sena, "q3", "A")
        self.answer(self.ali, "q3", "B")
        rows = topic_report(self.db, self.sena)
        self.assertEqual([r["topic"] for r in rows], ["Control charts", "Reliability"])
        charts, reliability = rows
        self.assertEqual((charts["questions"], charts["attempts"], charts["correct"]), (2, 3, 1))
        self.assertAlmostEqual(charts["accuracy"], 1 / 3)
        self.assertEqual((charts["wrong_now"], charts["unanswered"], charts["answered"]), (1, 0, 2))
        self.assertEqual((reliability["accuracy"], reliability["wrong_now"]), (1.0, 0))

    def test_topic_report_filters_and_unanswered_topics_last(self):
        self.answer(self.sena, "q3", "B")
        rows = topic_report(self.db, self.sena, course_id=1, chapter_id=self.chapter_id)
        self.assertEqual([r["topic"] for r in rows], ["Reliability", "Control charts"])
        self.assertIsNone(rows[1]["accuracy"])
        self.assertEqual(rows[1]["unanswered"], 2)
        self.assertEqual(topic_report(self.db, self.sena, course_id=999), [])


if __name__ == "__main__":
    unittest.main()
