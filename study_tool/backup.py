"""SQLite database'inin tarihli yedeğini alır ve kopyayı doğrular.

Geri yükleme bilerek otomatik değildir (gerçek database'in üzerine yazma riski);
elle geri yükleme adımları PROJECT.md'de.
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from study_tool.storage import DEFAULT_DB_PATH


def open_read_only(path):
    return sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)


def table_counts(connection):
    """Her tablonun satır sayısını {tablo: sayı} olarak döndürür."""
    names = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    return {name: connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in names}


def create_backup(db_path, backup_dir, now=None):
    """Yedeği oluşturur, doğrular ve (yol, tablo sayıları) döndürür.

    Doğrulama başarısızsa bozuk kopya silinir ve ValueError verilir.
    """
    db_path, backup_dir = Path(db_path), Path(backup_dir)
    if not db_path.is_file():
        raise ValueError(f"Database bulunamadı: {db_path}")
    stamp = (now or datetime.now()).strftime("%Y-%m-%d_%H%M%S")
    target = backup_dir / f"{db_path.stem}_{stamp}.db"
    backup_dir.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError(f"{target} zaten var; üzerine yazılmadı.")

    source = open_read_only(db_path)
    try:
        copy = sqlite3.connect(target)
        try:
            source.backup(copy)
            # Kaynak salt okunur açık olduğu için iki sayım arasında değişemez.
            expected = table_counts(source)
            integrity = copy.execute("PRAGMA integrity_check").fetchone()[0]
            actual = table_counts(copy)
        finally:
            copy.close()
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        source.close()

    if integrity != "ok" or actual != expected:
        target.unlink(missing_ok=True)
        raise ValueError(f"Yedek doğrulanamadı (integrity: {integrity}); kopya silindi.")
    return target, actual


def main():
    parser = argparse.ArgumentParser(description="Database'in tarihli yedeğini al ve doğrula.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DB_PATH.parent / "backups",
                        help="Yedek klasörü (varsayılan: data/backups)")
    args = parser.parse_args()
    try:
        target, counts = create_backup(args.db, args.dest)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"Yedek başarısız: {error}\n")
    print(f"Yedek: {target.resolve()}")
    print("integrity_check: ok | Tablo satır sayıları asılla aynı:")
    for name, count in counts.items():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
