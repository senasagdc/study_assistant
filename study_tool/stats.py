"""Tekrar kuralı ve konu bazlı zayıf nokta raporu; yalnızca answer_attempts'ten hesaplanır."""

import argparse
import json
import sqlite3
from pathlib import Path

from study_tool.manage import get_course_id, get_user_id
from study_tool.storage import DEFAULT_DB_PATH, connect_db


def last_results(connection, user_id):
    """Kullanıcının her soruya verdiği EN SON cevabın doğruluğu: {question_id: bool}.

    Sürümler aynı sorunun parçası sayılır. Sıra answer_attempts.id ile belirlenir
    (aynı saniyedeki iki cevapta answered_at eşit olabilir; id her zaman artar).
    """
    results = {}
    for question_id, is_correct in connection.execute(
        "SELECT v.question_id, a.is_correct FROM answer_attempts a "
        "JOIN question_versions v ON v.id = a.question_version_id "
        "WHERE a.user_id = ? ORDER BY a.id",
        (user_id,),
    ):
        results[question_id] = bool(is_correct)
    return results


def due_items(connection, items, user_id):
    """Tekrar kuralı: son cevabı yanlış olan veya hiç cevaplanmamış sorular kalır.

    items: quiz.load_chapter_questions çıktısı [(version_id, soru), ...]; sıra korunur.
    """
    if not items:
        return []
    version_ids = [version_id for version_id, _ in items]
    marks = ",".join("?" * len(version_ids))
    question_of = dict(connection.execute(
        f"SELECT id, question_id FROM question_versions WHERE id IN ({marks})", version_ids
    ))
    results = last_results(connection, user_id)
    return [item for item in items if results.get(question_of[item[0]]) is not True]


def topic_report(connection, user_id, course_id=None, chapter_id=None):
    """Konu bazlı özet; en zayıf konu en üstte.

    Her satır: topic, questions, answered, attempts, correct, accuracy (0–1 veya None),
    wrong_now (son cevabı yanlış soru sayısı), unanswered.
    Konu adı her sorunun son sürümünden alınır; büyük/küçük harf ve boşluk farkı yok sayılır.
    """
    sql = (
        "SELECT q.id, v.question_json FROM bank_questions q "
        "JOIN question_versions v ON v.question_id = q.id "
        "JOIN chapters ch ON ch.id = q.chapter_id JOIN documents d ON d.id = ch.document_id "
        "WHERE v.version_no = (SELECT MAX(version_no) FROM question_versions WHERE question_id = q.id)"
    )
    params = []
    if course_id is not None:
        sql += " AND d.course_id = ?"
        params.append(course_id)
    if chapter_id is not None:
        sql += " AND q.chapter_id = ?"
        params.append(chapter_id)

    topic_of = {}
    groups = {}
    for question_id, content in connection.execute(sql, params):
        name = " ".join(json.loads(content)["topic"].split())
        key = name.casefold()
        topic_of[question_id] = key
        row = groups.setdefault(key, dict(topic=name, questions=0, answered=0, attempts=0,
                                          correct=0, wrong_now=0, unanswered=0))
        row["questions"] += 1

    for question_id, is_correct in connection.execute(
        "SELECT v.question_id, a.is_correct FROM answer_attempts a "
        "JOIN question_versions v ON v.id = a.question_version_id WHERE a.user_id = ?",
        (user_id,),
    ):
        if question_id in topic_of:
            row = groups[topic_of[question_id]]
            row["attempts"] += 1
            row["correct"] += is_correct

    results = last_results(connection, user_id)
    for question_id, key in topic_of.items():
        row = groups[key]
        if question_id not in results:
            row["unanswered"] += 1
        else:
            row["answered"] += 1
            row["wrong_now"] += not results[question_id]

    rows = list(groups.values())
    for row in rows:
        row["accuracy"] = row["correct"] / row["attempts"] if row["attempts"] else None
    # Önce cevaplanmış konular (başarı artan, şu an yanlış azalan), en sonda hiç denenmemiş konular.
    rows.sort(key=lambda r: (r["accuracy"] is None, r["accuracy"] or 0, -r["wrong_now"], r["topic"]))
    return rows


def main():
    parser = argparse.ArgumentParser(description="Konu bazlı zayıf nokta raporu.")
    parser.add_argument("--user", required=True)
    parser.add_argument("--course", help="Yalnızca bu dersin soruları")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    if not args.db.is_file():
        parser.exit(1, f"Database bulunamadı: {args.db}\n")
    connection = connect_db(args.db)
    try:
        user_id = get_user_id(connection, args.user)
        course_id = get_course_id(connection, args.course) if args.course else None
        rows = topic_report(connection, user_id, course_id)
    except (ValueError, sqlite3.Error) as error:
        parser.exit(1, f"Rapor oluşturulamadı: {error}\n")
    finally:
        connection.close()
    if not rows:
        print("Soru yok.")
        return
    print("Başarı | Doğru/Deneme | Şu an yanlış | Hiç cevaplanmadı | Konu")
    for row in rows:
        accuracy = "   -  " if row["accuracy"] is None else f"%{100 * row['accuracy']:5.1f}"
        print(f"{accuracy} | {row['correct']:>3}/{row['attempts']:<3}      | {row['wrong_now']:>12} | "
              f"{row['unanswered']:>16} | {row['topic']} ({row['questions']} soru)")


if __name__ == "__main__":
    main()
