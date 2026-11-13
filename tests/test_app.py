"""Streamlit arayüzü, tarayıcı açmadan AppTest ile test edilir; geçici database kullanılır."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from streamlit.testing.v1 import AppTest

from study_tool.import_bank import import_questions, prepare_import
from study_tool.manage import add_course, add_user
from study_tool.storage import connect_db

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def sample_question(identifier, text):
    return dict(id=identifier, type="mcq", question=text,
                options=dict(A="One", B="Two", C="Three", D="Four"),
                correct_answer="A", explanation="Çünkü $x^2$.", topic="Demo", source_pages=[1])


class AppTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        self.db_path = root / "test.db"
        pdf, extracted, bank = root / "demo.pdf", root / "demo.json", root / "bank.json"
        with pymupdf.open() as document:
            document.new_page().insert_text((72, 72), "Demo chapter")
            document.save(pdf)
        extracted.write_text(json.dumps(dict(chapters=[dict(
            chapter=1, pages=[dict(page=1, text="Demo chapter")])])), encoding="utf-8")
        bank.write_text(json.dumps([sample_question("q1", "First?"),
                                    sample_question("q2", "Second?")]), encoding="utf-8")
        with connect_db(self.db_path) as db:
            add_course(db, "Quality")
            import_questions(db, prepare_import(pdf, extracted, 1, bank), course="Quality")
            add_user(db, "Sena")
        db.close()
        env = patch.dict(os.environ, {"STUDY_DB_PATH": str(self.db_path)})
        env.start()
        self.addCleanup(env.stop)

    def attempts(self):
        db = connect_db(self.db_path)
        try:
            return db.execute(
                "SELECT selected_answer, is_correct, user_id FROM answer_attempts ORDER BY id"
            ).fetchall()
        finally:
            db.close()

    def run_app(self):
        app = AppTest.from_file(APP, default_timeout=30)
        app.run()
        self.assertFalse(app.exception, app.exception)
        return app

    def answer(self, app, letter):
        app.radio(key=[r.key for r in app.radio if r.key.startswith("choice_")][0]).set_value(letter).run()
        app.button[0].click().run()   # Cevapla
        return app

    def test_answer_is_saved_and_due_mode_skips_correct_questions(self):
        app = self.run_app()
        self.assertIn("First?", [m.value for m in app.markdown])
        self.answer(app, "A")
        self.assertEqual(app.success[0].value, "Doğru! Cevabın: A")
        self.assertEqual(self.attempts(), [("A", 1, 1)])
        app.button[0].click().run()   # Sonraki soru
        self.answer(app, "C")
        self.assertTrue(app.error[0].value.startswith("Yanlış"))
        app.button[0].click().run()
        self.assertEqual(app.subheader[0].value, "Quiz bitti")

        fresh = self.run_app()   # yeni oturum: yalnızca yanlış cevaplanan soru kalır
        self.assertIn("Second?", [m.value for m in fresh.markdown])
        self.assertNotIn("First?", [m.value for m in fresh.markdown])

    def test_all_correct_shows_nothing_due_and_all_mode_shows_everything(self):
        app = self.run_app()
        for _ in range(2):
            self.answer(app, "A")
            app.button[0].click().run()
        fresh = self.run_app()
        self.assertIn("tekrar edilecek soru yok", fresh.success[0].value)
        fresh.sidebar.radio(key="mode").set_value("Hepsi").run()
        self.assertIn("First?", [m.value for m in fresh.markdown])

    def test_user_can_be_added_from_sidebar(self):
        app = self.run_app()
        app.sidebar.text_input[0].input("Ali")
        app.sidebar.button[0].click().run()
        db = connect_db(self.db_path)
        self.addCleanup(db.close)
        self.assertEqual(db.execute("SELECT name FROM users ORDER BY name").fetchall(),
                         [("Ali",), ("Sena",)])


if __name__ == "__main__":
    unittest.main()
