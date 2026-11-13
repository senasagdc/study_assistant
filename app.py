"""Kişisel Soru ve Tekrar Aracı — Streamlit arayüzü.

Çalıştırma (proje kökünden, .venv aktif):  streamlit run app.py
Database: varsayılan data/study.db; STUDY_DB_PATH ortam değişkeniyle değiştirilebilir.
"""

import os
from pathlib import Path

import streamlit as st

from study_tool.manage import add_user
from study_tool.quiz import load_chapter_questions, record_answer
from study_tool.stats import due_items
from study_tool.storage import DEFAULT_DB_PATH, connect_db

DB_PATH = Path(os.environ.get("STUDY_DB_PATH", DEFAULT_DB_PATH))
NO_COURSE = "(Derssiz PDF'ler)"


def open_db():
    # Streamlit her etkileşimde script'i yeniden çalıştırır; her seferinde kısa ömürlü
    # bir bağlantı açmak sqlite3'ün thread kısıtlamasıyla uğraşmaktan daha basit.
    return connect_db(DB_PATH)


def pick(label, rows, key):
    """rows: [(id, etiket), ...] → seçilen id (liste boşsa None)."""
    if not rows:
        return None
    labels = dict(rows)
    return st.sidebar.selectbox(label, list(labels), format_func=labels.get, key=key)


def sidebar(conn):
    st.sidebar.header("Seçim")
    users = conn.execute("SELECT id, name FROM users ORDER BY name").fetchall()
    with st.sidebar.expander("Yeni kullanıcı ekle", expanded=not users):
        with st.form("new_user", clear_on_submit=True):
            name = st.text_input("İsim")
            if st.form_submit_button("Ekle"):
                try:
                    add_user(conn, name)
                    st.success(f"{name.strip()} eklendi.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    user_id = pick("Kullanıcı", users, "user")

    courses = conn.execute("SELECT id, name FROM courses ORDER BY name").fetchall()
    if conn.execute("SELECT 1 FROM documents WHERE course_id IS NULL").fetchone():
        courses.append((0, NO_COURSE))
    course_id = pick("Ders", courses, "course")

    documents = []
    if course_id is not None:
        documents = conn.execute(
            "SELECT id, filename FROM documents WHERE "
            + ("course_id IS NULL" if course_id == 0 else "course_id = ?")
            + " ORDER BY filename",
            () if course_id == 0 else (course_id,),
        ).fetchall()
    document_id = pick("PDF", documents, "document")

    chapters = []
    if document_id is not None:
        chapters = [
            (cid, f"Chapter {no} (s. {start}–{end}, {count} soru)")
            for cid, no, start, end, count in conn.execute(
                "SELECT c.id, c.chapter_no, c.start_page, c.end_page, COUNT(q.id) FROM chapters c "
                "LEFT JOIN bank_questions q ON q.chapter_id = c.id WHERE c.document_id = ? "
                "GROUP BY c.id ORDER BY c.chapter_no",
                (document_id,),
            )
        ]
    chapter_id = pick("Chapter", chapters, "chapter")

    due_only = st.sidebar.radio(
        "Sorular", ["Tekrar edilecekler", "Hepsi"], key="mode",
        help="Tekrar edilecekler: son cevabın yanlış olan veya hiç cevaplamadığın sorular.",
    ) == "Tekrar edilecekler"
    return user_id, chapter_id, due_only


def start_session(conn, user_id, chapter_id, due_only):
    """Seçim değişince yeni quiz başlatır. Soru listesi başta sabitlenir;
    böylece quiz sırasında doğru cevaplanan soru listeden kaybolmaz."""
    items = load_chapter_questions(conn, chapter_id)
    if due_only:
        items = due_items(conn, items, user_id)
    st.session_state.quiz = dict(
        key=(user_id, chapter_id, due_only),
        version_ids=[version_id for version_id, _ in items],
        index=0, correct=0, answered=0, feedback=None,
    )


def show_feedback(question, feedback):
    if feedback["is_correct"]:
        st.success(f"Doğru! Cevabın: {feedback['selected']}")
    else:
        st.error(f"Yanlış. Cevabın: {feedback['selected']}")
    expected = question["correct_answer"]
    st.markdown(f"**Doğru cevap:** {expected}) {question['options'][expected]}")
    st.markdown(f"**Açıklama:** {question['explanation']}")
    st.caption("Kaynak PDF sayfaları: " + ", ".join(map(str, question["source_pages"])))


def quiz_page(conn, user_id, chapter_id, due_only):
    if user_id is None:
        st.info("Başlamak için soldan bir kullanıcı ekle.")
        return
    if chapter_id is None:
        st.info("Soru bulunan bir ders, PDF ve chapter seç.")
        return

    key = (user_id, chapter_id, due_only)
    if st.session_state.get("quiz", {}).get("key") != key:
        start_session(conn, user_id, chapter_id, due_only)
    quiz = st.session_state.quiz
    total = len(quiz["version_ids"])

    if total == 0:
        st.success("Bu chapter'da tekrar edilecek soru yok: tüm son cevapların doğru. 🎉")
        st.caption("Bütün soruları görmek için soldan \"Hepsi\"ni seç.")
        return

    if quiz["index"] >= total:
        st.subheader("Quiz bitti")
        answered, correct = quiz["answered"], quiz["correct"]
        st.metric("Doğru", f"{correct} / {answered}",
                  f"%{100 * correct / answered:.0f}" if answered else None)
        if st.button("Baştan başla"):
            start_session(conn, user_id, chapter_id, due_only)
            st.rerun()
        return

    version_id = quiz["version_ids"][quiz["index"]]
    items = dict(load_chapter_questions(conn, chapter_id))
    if version_id not in items:
        # Quiz sırasında soru yeni sürüme geçtiyse güncel listeyle baştan başla.
        start_session(conn, user_id, chapter_id, due_only)
        st.rerun()
    question = items[version_id]

    st.progress(quiz["index"] / total, text=f"Soru {quiz['index'] + 1} / {total}")
    st.caption(question["topic"])
    st.markdown(question["question"])

    feedback = quiz["feedback"]
    letters = list(question["options"])
    choice = st.radio(
        "Cevabın", letters, index=None, key=f"choice_{version_id}_{quiz['index']}",
        format_func=lambda letter: f"{letter}) {question['options'][letter]}",
        disabled=feedback is not None,
    )

    if feedback is None:
        if st.button("Cevapla", type="primary", disabled=choice is None):
            # Cevap, geri bildirim gösterilmeden önce kaydedilir (terminal quiz'iyle aynı kural).
            is_correct = record_answer(conn, version_id, choice, user_id)
            quiz["answered"] += 1
            quiz["correct"] += is_correct
            quiz["feedback"] = dict(selected=choice, is_correct=is_correct)
            st.rerun()
    else:
        show_feedback(question, feedback)
        if st.button("Sonraki soru", type="primary"):
            quiz["index"] += 1
            quiz["feedback"] = None
            st.rerun()

    st.caption(f"Bu oturumda: {quiz['correct']} doğru / {quiz['answered']} cevap")


def main():
    st.set_page_config(page_title="Soru ve Tekrar", page_icon="📘")
    st.title("Soru ve Tekrar")
    conn = open_db()
    try:
        user_id, chapter_id, due_only = sidebar(conn)
        quiz_page(conn, user_id, chapter_id, due_only)
    except ValueError as error:
        st.error(f"Sorular yüklenemedi: {error}")
    finally:
        conn.close()


main()
