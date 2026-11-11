import json
from pathlib import Path

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