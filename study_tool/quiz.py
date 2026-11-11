import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from study_tool.schema import OPTION_KEYS, validate_question
from study_tool.storage import DEFAULT_DB_PATH, connect_db


def find_chapter(connection, pdf_path, chapter_no):
    """PDF'i içerik hash'iyle tanır ve chapter'ın database ID'sini döndürür."""
    pdf_hash = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    row = connection.execute(
        "SELECT c.id FROM chapters c JOIN documents d ON d.id = c.document_id "
        "WHERE d.content_hash = ? AND c.chapter_no = ?",
        (pdf_hash, chapter_no),
    ).fetchone()
    if row is None:
        raise ValueError("Bu PDF/chapter database'de yok. Önce import veya generate çalıştır.")
    return row[0]


def load_chapter_questions(connection, chapter_id):
    """Chapter'daki her sorunun son sürümünü (version_id, soru) olarak döndürür."""
    rows = connection.execute(
        "SELECT v.id, v.question_json FROM bank_questions q "
        "JOIN question_versions v ON v.question_id = q.id WHERE q.chapter_id = ? "
        "AND v.version_no = (SELECT MAX(version_no) FROM question_versions WHERE question_id = q.id) "
        "ORDER BY q.id",
        (chapter_id,),
    ).fetchall()
    if not rows:
        raise ValueError("Bu chapter'da soru yok.")
    items = []
    for version_id, content in rows:
        question = json.loads(content)
        errors = validate_question(question)
        if errors:
            raise ValueError(f"Soru sürümü {version_id}: {'; '.join(errors)}")
        items.append((version_id, question))
    return items


def record_answer(connection, version_id, selected_answer):
    """Cevabı hemen kaydeder; doğruluğu database'deki cevap anahtarından hesaplar."""
    if selected_answer not in OPTION_KEYS:
        raise ValueError("Cevap A, B, C veya D olmalı.")
    row = connection.execute(
        "SELECT question_json FROM question_versions WHERE id = ?", (version_id,)
    ).fetchone()
    if row is None:
        raise ValueError("Soru sürümü database'de bulunamadı.")
    is_correct = selected_answer == json.loads(row[0])["correct_answer"]
    with connection:
        connection.execute(
            "INSERT INTO answer_attempts (question_version_id, selected_answer, is_correct) "
            "VALUES (?, ?, ?)",
            (version_id, selected_answer, int(is_correct)),
        )
    return is_correct


def run_quiz(connection, items):
    """Cevapları alır, her birini kaydeder, geri bildirim gösterir ve sonucu hesaplar."""
    correct = 0
    answered = 0
    print("Cevap için A–D, çıkmak için Q yazabilirsin.")
    for index, (version_id, question) in enumerate(items, start=1):
        print(f"\nSoru {index}/{len(items)} — {question['topic']}")
        print(question["question"])
        for letter in OPTION_KEYS:
            print(f"{letter}) {question['options'][letter]}")

        while True:
            try:
                answer = input("Cevabın: ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                answer = "Q"
                print()
            if answer in OPTION_KEYS or answer == "Q":
                break
            print("Lütfen A, B, C, D veya Q gir.")

        if answer == "Q":
            break
        is_correct = record_answer(connection, version_id, answer)
        answered += 1
        if is_correct:
            correct += 1
            print("Doğru!")
        else:
            print("Yanlış.")
        expected = question["correct_answer"]
        print(f"Doğru cevap: {expected}) {question['options'][expected]}")
        print(f"Açıklama: {question['explanation']}")
        print("Kaynak PDF sayfaları: " + ", ".join(map(str, question["source_pages"])))

    print(f"\nSonuç: {answered}/{len(items)} soru cevaplandı.")
    print(f"Doğru: {correct} | Yanlış: {answered - correct}")
    if answered:
        print(f"Başarı (cevaplanan sorularda): %{100 * correct / answered:.1f}")
    print(f"{answered} cevap database'e kaydedildi.")
    return dict(answered=answered, correct=correct)


def main():
    parser = argparse.ArgumentParser(description="Database'deki chapter sorularını terminalde çöz.")
    parser.add_argument("pdf", type=Path, help="Chapter'ın ait olduğu PDF")
    parser.add_argument("chapter", type=int)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    if not args.db.is_file():
        parser.exit(1, f"Database bulunamadı: {args.db}\n")
    connection = connect_db(args.db)
    try:
        chapter_id = find_chapter(connection, args.pdf, args.chapter)
        items = load_chapter_questions(connection, chapter_id)
        run_quiz(connection, items)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"Quiz başlatılamadı: {error}\n")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
