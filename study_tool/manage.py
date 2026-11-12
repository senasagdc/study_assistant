"""Dersleri ve kullanıcıları yönetir; PDF'leri derslere bağlar."""

import argparse
import hashlib
import sqlite3
from pathlib import Path

from study_tool.storage import DEFAULT_DB_PATH, connect_db


def _add(connection, table, name):
    name = name.strip()
    if not name:
        raise ValueError("İsim boş olamaz.")
    try:
        with connection:
            return connection.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,)).lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"'{name}' zaten kayıtlı.") from None


def _get_id(connection, table, name, hint):
    row = connection.execute(f"SELECT id FROM {table} WHERE name = ?", (name.strip(),)).fetchone()
    if row is None:
        raise ValueError(f"'{name}' bulunamadı. Önce: python -m study_tool.manage {hint} \"{name}\"")
    return row[0]


def add_course(connection, name):
    return _add(connection, "courses", name)


def add_user(connection, name):
    return _add(connection, "users", name)


def get_course_id(connection, name):
    return _get_id(connection, "courses", name, "add-course")


def get_user_id(connection, name):
    return _get_id(connection, "users", name, "add-user")


def link_document_course(connection, document_id, course_name):
    """Belgeyi derse bağlar. Transaction'ı çağıran yönetir.

    Belge zaten başka bir derse bağlıysa hata verir (yanlışlıkla taşınmasın diye).
    """
    course_id = get_course_id(connection, course_name)
    current = connection.execute(
        "SELECT course_id FROM documents WHERE id = ?", (document_id,)
    ).fetchone()[0]
    if current is None:
        connection.execute("UPDATE documents SET course_id = ? WHERE id = ?", (course_id, document_id))
    elif current != course_id:
        raise ValueError("Bu PDF başka bir derse bağlı; işlem geri alındı.")
    return course_id


def document_course_name(connection, document_id):
    row = connection.execute(
        "SELECT c.name FROM documents d LEFT JOIN courses c ON c.id = d.course_id WHERE d.id = ?",
        (document_id,),
    ).fetchone()
    return row[0] if row else None


def set_course(connection, pdf_path, course_name):
    """Database'de kayıtlı bir PDF'i (içerik hash'iyle) derse bağlar."""
    pdf_hash = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    row = connection.execute("SELECT id FROM documents WHERE content_hash = ?", (pdf_hash,)).fetchone()
    if row is None:
        raise ValueError("Bu PDF database'de yok. Önce import veya generate çalıştır.")
    with connection:
        return link_document_course(connection, row[0], course_name)


def claim_attempts(connection, user_name):
    """Kullanıcısı olmayan (eski) cevapları verilen kullanıcıya bağlar."""
    user_id = get_user_id(connection, user_name)
    with connection:
        return connection.execute(
            "UPDATE answer_attempts SET user_id = ? WHERE user_id IS NULL", (user_id,)
        ).rowcount


def overview(connection):
    """Dersler, belgeler ve kullanıcılar için kısa bir özet satırları listesi."""
    lines = ["Dersler:"]
    for name, docs, questions in connection.execute(
        "SELECT c.name, COUNT(DISTINCT d.id), COUNT(q.id) FROM courses c "
        "LEFT JOIN documents d ON d.course_id = c.id LEFT JOIN chapters ch ON ch.document_id = d.id "
        "LEFT JOIN bank_questions q ON q.chapter_id = ch.id GROUP BY c.id ORDER BY c.name"
    ):
        lines.append(f"  {name}: {docs} PDF, {questions} soru")
    for (filename,) in connection.execute(
        "SELECT filename FROM documents WHERE course_id IS NULL ORDER BY id"
    ):
        lines.append(f"  (derssiz PDF) {filename}")
    lines.append("Kullanıcılar:")
    for name, answers in connection.execute(
        "SELECT u.name, COUNT(a.id) FROM users u LEFT JOIN answer_attempts a ON a.user_id = u.id "
        "GROUP BY u.id ORDER BY u.name"
    ):
        lines.append(f"  {name}: {answers} cevap")
    orphan = connection.execute(
        "SELECT COUNT(*) FROM answer_attempts WHERE user_id IS NULL"
    ).fetchone()[0]
    if orphan:
        lines.append(f"  (kullanıcısız cevap) {orphan}")
    return lines


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser = argparse.ArgumentParser(description="Dersleri ve kullanıcıları yönet.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("add-course", parents=[common]).add_argument("name")
    sub.add_parser("add-user", parents=[common]).add_argument("name")
    p = sub.add_parser("set-course", parents=[common], help="Kayıtlı bir PDF'i derse bağla")
    p.add_argument("pdf", type=Path)
    p.add_argument("course")
    sub.add_parser("claim-attempts", parents=[common],
                   help="Kullanıcısız eski cevapları bir kullanıcıya bağla").add_argument("user")
    sub.add_parser("list", parents=[common])
    args = parser.parse_args()

    # Yeni kurulumda ilk ders eklenebilsin diye database yoksa oluşturulur.
    print(f"Database: {args.db.resolve()}")
    connection = connect_db(args.db)
    try:
        if args.command == "add-course":
            add_course(connection, args.name)
            print(f"Ders eklendi: {args.name}")
        elif args.command == "add-user":
            add_user(connection, args.name)
            print(f"Kullanıcı eklendi: {args.name}")
        elif args.command == "set-course":
            set_course(connection, args.pdf, args.course)
            print(f"{args.pdf.name} -> {args.course}")
        elif args.command == "claim-attempts":
            count = claim_attempts(connection, args.user)
            print(f"{count} cevap {args.user} kullanıcısına bağlandı.")
        print("\n".join(overview(connection)))
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"İşlem başarısız: {error}\n")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
