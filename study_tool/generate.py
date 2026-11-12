import argparse
import json
import re
import sqlite3
from pathlib import Path

from study_tool.import_bank import import_questions, prepare_chapter
from study_tool.question_bank import append_questions, load_bank
from study_tool.storage import DEFAULT_DB_PATH, connect_db

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "generate_questions.txt"


def pages_to_text(pages):
    """Her sayfanın başına [Page N] etiketi koyup birleştirir."""
    return "\n\n".join(f"[Page {p['page']}]\n{p['text']}" for p in pages)


MAX_EXISTING_CHARS = 300  # prompt'a eklenen her eski sorunun en fazla uzunluğu


def existing_summary(questions):
    """Mevcut soruları modelin tekrar etmemesi için kısa bir listeye çevirir."""
    if not questions:
        return "None yet."
    lines = []
    for q in questions:
        text = " ".join(q["question"].split())
        if len(text) > MAX_EXISTING_CHARS:
            text = text[:MAX_EXISTING_CHARS] + "..."
        lines.append(f"- [{q['topic']}] {text}")
    return "\n".join(lines)


def build_prompt(pages, n_questions, existing=()):
    """Prompt şablonundaki boşlukları doldurur."""
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return (template
            .replace("{N_QUESTIONS}", str(n_questions))
            .replace("{EXISTING_QUESTIONS}", existing_summary(existing))
            .replace("{CHAPTER_TEXT}", pages_to_text(pages)))


# JSON'da tek ters bölü ile yazılmış LaTeX (\times, \frac, \beta, \rho) sessizce
# tab, form feed, backspace veya carriage return karakterine dönüşür.
def broken_escape_fields(question):
    """Bozuk LaTeX kaçışı içeren alanların adlarını döndürür."""
    texts = {"question": question.get("question"), "explanation": question.get("explanation")}
    options = question.get("options")
    if isinstance(options, dict):
        texts.update({f"options.{k}": v for k, v in options.items()})
    return [name for name, value in texts.items()
            if isinstance(value, str) and any(c in value for c in "\t\f\b\r")]


def _fix_escape(match):
    """Geçerli JSON kaçışlarını korur; diğer tek ters bölüleri ikiye katlar."""
    char = match.group(1)
    return match.group(0) if char in '\\"/bfnrtu' else "\\\\" + char


def parse_questions(raw):
    """Model cevabını JSON listesine çevirir; olmazsa ValueError verir."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Modeller bazen son elemandan sonra fazladan virgül bırakır ve
        # LaTeX ters bölüsünü (\Phi, \mu) JSON için ikiye katlamayı unutur.
        cleaned = re.sub(r",(\s*[}\]])", r"\1", text)
        cleaned = re.sub(r"\\(.)", _fix_escape, cleaned, flags=re.DOTALL)
        data = json.loads(cleaned)
        print("Not: JSON'daki fazladan virgüller / tek ters bölüler düzeltildi.")
    if not isinstance(data, list):
        raise ValueError("Cevap bir JSON listesi değil")
    return data


def default_pdf_path(json_path):
    """Çıkarılmış JSON'daki 'source' adını aynı klasörde arar."""
    source = json.loads(Path(json_path).read_text(encoding="utf-8"))["source"]
    return Path(json_path).parent / source


def run_generation(json_path, chapter_no, n_questions, pdf_path=None, db_path=DEFAULT_DB_PATH):
    """Soru üretir; yeni soruları önce JSON bankasına, sonra SQLite'a ekler."""
    json_path = Path(json_path)
    pdf_path = Path(pdf_path) if pdf_path else default_pdf_path(json_path)

    # API kotası harcanmadan önce PDF, chapter ve mevcut banka doğrulanır.
    chapter = prepare_chapter(pdf_path, json_path, chapter_no)
    allowed = set(range(chapter["start_page"], chapter["end_page"] + 1))
    out = json_path.parent / f"{json_path.stem}_ch{chapter_no}_questions.json"
    existing = load_bank(out, allowed)
    print(f"Mevcut soru bankası: {len(existing)} soru")

    connection = connect_db(db_path)
    try:
        # JSON'da olup database'de olmayan eski sorular 'import' olarak eşitlenir;
        # böylece aşağıdaki 'llm' kaydına yalnızca bu üretimin soruları girer.
        sync = import_questions(connection, dict(chapter, questions=existing))
        if sync["added"]:
            print(f"Database'de olmayan {sync['added']} eski soru 'import' olarak eşitlendi.")

        from core.llm import MODEL, generate_text  # anahtar gerektirdiği için burada

        print("Chapter metni Gemini API'ye gönderiliyor...")
        raw = generate_text(build_prompt(chapter["pages"], n_questions, existing))
        if not raw:
            print("Model boş cevap döndürdü.")
            return None

        stem = f"{json_path.stem}_ch{chapter_no}"
        raw_path = json_path.parent / f"{stem}_raw.txt"
        raw_path.write_text(raw, encoding="utf-8")
        print("Ham cevap kaydedildi:", raw_path)

        try:
            questions = parse_questions(raw)
        except ValueError as e:
            print("JSON okunamadı:", e)
            return None

        accepted, broken = [], 0
        for index, question in enumerate(questions, 1):
            fields = broken_escape_fields(question) if isinstance(question, dict) else []
            if fields:
                broken += 1
                print(f"Soru {index}: GEÇERSİZ -> bozuk LaTeX kaçışı: {', '.join(fields)}")
            else:
                accepted.append(question)
        report = append_questions(out, accepted, allowed)
        report["invalid"] += broken
        print(f"İstenen: {n_questions} | gelen: {len(questions)}")
        print(f"Önceki: {report['existing']} | Eklenen: {report['added']} | "
              f"Geçersiz: {report['invalid']} | Tekrar: {report['duplicate']} | "
              f"Toplam: {report['total']}")
        print("Soru bankası:", out)
        if not report["added"]:
            print("SQLite: yeni soru yok, kayıt eklenmedi.")
            return report

        try:
            saved = import_questions(
                connection, dict(chapter, questions=load_bank(out, allowed)),
                kind="llm", model=MODEL,
            )
        except (ValueError, sqlite3.Error) as e:
            print("UYARI: Sorular JSON bankasına eklendi ama SQLite'a kaydedilemedi:", e)
            print("Sorunu giderdikten sonra import komutuyla eşitleyebilirsin.")
            return report
        print(f"SQLite: eklenen {saved['added']} | chapter toplamı {saved['total']} | "
              f"generation ID {saved['generation_id']} (llm, {MODEL})")
        return dict(report, sqlite=saved)
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(
        description="Chapter metninden Gemini ile soru üret; JSON bankasına ve SQLite'a kaydet.")
    parser.add_argument("extracted_json", type=Path)
    parser.add_argument("chapter", type=int)
    parser.add_argument("n_questions", type=int)
    parser.add_argument("--pdf", type=Path,
                        help="Varsayılan: JSON'daki 'source' adıyla aynı klasördeki PDF")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    try:
        run_generation(args.extracted_json, args.chapter, args.n_questions, args.pdf, args.db)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, sqlite3.Error) as error:
        parser.exit(1, f"Üretim başarısız: {error}\n")


if __name__ == "__main__":
    main()
