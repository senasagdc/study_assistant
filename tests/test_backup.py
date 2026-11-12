import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from study_tool.backup import create_backup, open_read_only, table_counts
from study_tool.storage import connect_db


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.db_path = self.root / "study.db"
        with connect_db(self.db_path) as db:
            db.execute("INSERT INTO courses (name) VALUES ('Quality')")
            db.execute("INSERT INTO users (name) VALUES ('Sena')")
        db.close()
        self.now = datetime(2026, 11, 12, 18, 5, 9)

    def test_backup_copies_all_rows_and_leaves_source_unchanged(self):
        before = self.db_path.read_bytes()
        target, counts = create_backup(self.db_path, self.root / "backups", self.now)
        self.assertEqual(target.name, "study_2026-11-12_180509.db")
        self.assertEqual(counts["courses"], 1)
        self.assertEqual(counts["users"], 1)
        copy = open_read_only(target)
        self.addCleanup(copy.close)
        self.assertEqual(copy.execute("SELECT name FROM users").fetchone()[0], "Sena")
        self.assertEqual(copy.execute("PRAGMA user_version").fetchone()[0], 1)
        source = open_read_only(self.db_path)
        self.addCleanup(source.close)
        self.assertEqual(table_counts(source), table_counts(copy))
        self.assertEqual(self.db_path.read_bytes(), before)

    def test_existing_backup_is_not_overwritten(self):
        create_backup(self.db_path, self.root / "backups", self.now)
        with self.assertRaises(ValueError):
            create_backup(self.db_path, self.root / "backups", self.now)

    def test_missing_database_is_not_created(self):
        missing = self.root / "missing.db"
        with self.assertRaises(ValueError):
            create_backup(missing, self.root / "backups", self.now)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
