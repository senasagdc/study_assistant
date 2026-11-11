OPTION_KEYS = ["A", "B", "C", "D"]
REQUIRED_FIELDS = [
    "id", "type", "question", "options",
    "correct_answer", "explanation", "topic", "source_pages",
]


def validate_question(q, allowed_pages=None):
    """Soruyu kontrol eder, hata mesajlarının listesini döndürür (boşsa geçerli)."""
    if not isinstance(q, dict):
        return ["Soru bir sözlük (dict) olmalı"]

    errors = []
    for field in REQUIRED_FIELDS:
        if field not in q:
            errors.append(f"Eksik alan: {field}")
    if errors:
        return errors

    if q["type"] != "mcq":
        errors.append("type 'mcq' olmalı")

    for field in ["id", "question", "explanation", "topic"]:
        if not isinstance(q[field], str) or not q[field].strip():
            errors.append(f"{field} boş olmayan bir metin olmalı")

    opts = q["options"]
    if not isinstance(opts, dict) or list(opts.keys()) != OPTION_KEYS:
        errors.append("options tam olarak A, B, C, D anahtarlarına sahip olmalı")
    elif not all(isinstance(v, str) and v.strip() for v in opts.values()):
        errors.append("Her şık boş olmayan bir metin olmalı")
    elif len(set(v.strip().lower() for v in opts.values())) < 4:
        errors.append("Şıklar birbirinden farklı olmalı")

    if q["correct_answer"] not in OPTION_KEYS:
        errors.append("correct_answer A, B, C veya D olmalı")

    pages = q["source_pages"]
    if (not isinstance(pages, list) or not pages
            or not all(isinstance(p, int) and not isinstance(p, bool) for p in pages)):
        errors.append("source_pages boş olmayan bir tam sayı listesi olmalı")
    elif allowed_pages is not None and not all(p in allowed_pages for p in pages):
        errors.append("source_pages chapter sayfaları dışında bir sayfa içeriyor")

    return errors