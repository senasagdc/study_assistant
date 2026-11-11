import json
import re
import sys
from pathlib import Path

from study_tool.schema import validate_question

PROMPT_PATH = Path("prompts/generate_questions.txt")


def load_chapter(json_path, chapter_no):
    """JSON'dan bir chapter'ın sayfa listesini döndürür."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    for chapter in data["chapters"]:
        if chapter["chapter"] == chapter_no:
            return chapter["pages"]
    raise ValueError(f"Chapter {chapter_no} bulunamadı")


def pages_to_text(pages):
    """Her sayfanın başına [Page N] etiketi koyup birleştirir."""
    return "\n\n".join(f"[Page {p['page']}]\n{p['text']}" for p in pages)


def build_prompt(pages, n_questions):
    """Prompt şablonundaki boşlukları doldurur."""
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return (template
            .replace("{N_QUESTIONS}", str(n_questions))
            .replace("{CHAPTER_TEXT}", pages_to_text(pages)))


def parse_questions(raw):
    """Model cevabını JSON listesine çevirir; olmazsa ValueError verir."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Modeller bazen son elemandan sonra fazladan virgül bırakır
        cleaned = re.sub(r",(\s*[}\]])", r"\1", text)
        data = json.loads(cleaned)
        print("Not: JSON'daki fazladan virgüller temizlendi.")
    if not isinstance(data, list):
        raise ValueError("Cevap bir JSON listesi değil")
    return data


def main():
    json_path = Path(sys.argv[1])
    chapter_no = int(sys.argv[2])
    n_questions = int(sys.argv[3])

    from core.llm import generate_text  # anahtar gerektirdiği için burada

    pages = load_chapter(json_path, chapter_no)
    prompt = build_prompt(pages, n_questions)

    print("Chapter metni Gemini API'ye gönderiliyor...")
    raw = generate_text(prompt)
    if not raw:
        print("Model boş cevap döndürdü.")
        return

    stem = f"{json_path.stem}_ch{chapter_no}"
    raw_path = Path("data") / f"{stem}_raw.txt"
    raw_path.write_text(raw, encoding="utf-8")
    print("Ham cevap kaydedildi:", raw_path)

    try:
        questions = parse_questions(raw)
    except ValueError as e:
        print("JSON okunamadı:", e)
        return

    allowed = {p["page"] for p in pages}
    valid = []
    for i, q in enumerate(questions, start=1):
        errors = validate_question(q, allowed)
        if errors:
            print(f"Soru {i}: GEÇERSİZ -> {errors}")
        else:
            valid.append(q)

    out = Path("data") / f"{stem}_questions.json"
    out.write_text(json.dumps(valid, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"İstenen: {n_questions} | gelen: {len(questions)} | geçerli: {len(valid)}")
    print("Geçerli sorular kaydedildi:", out)


if __name__ == "__main__":
    main()