import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from study_tool.schema import validate_question


def question_key(question):
    """Metindeki harf büyüklüğü ve boşluk farklarını yok sayar."""
    return " ".join(question["question"].casefold().split())


def load_bank(path, allowed_pages):
    path = Path(path)
    if not path.exists():
        return []
    questions = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(questions, list):
        raise ValueError("Mevcut soru bankası JSON listesi olmalı; dosya değiştirilmedi.")
    ids = set()
    for index, question in enumerate(questions, 1):
        errors = validate_question(question, allowed_pages)
        if errors:
            raise ValueError(f"Mevcut banka, soru {index}: {errors}. Dosya değiştirilmedi.")
        if question["id"] in ids:
            raise ValueError("Mevcut bankada tekrarlanan ID var; dosya değiştirilmedi.")
        ids.add(question["id"])
    return questions


def append_questions(path, candidates, allowed_pages):
    """Geçerli ve yeni soruları bankaya güvenli biçimde ekler."""
    path = Path(path)
    existing = load_bank(path, allowed_pages)
    keys = {question_key(q) for q in existing}
    added = []
    report = dict(existing=len(existing), added=0, invalid=0, duplicate=0)
    for index, question in enumerate(candidates, 1):
        errors = validate_question(question, allowed_pages)
        if errors:
            report["invalid"] += 1
            print(f"Soru {index}: GEÇERSİZ -> {errors}")
            continue
        key = question_key(question)
        if key in keys:
            report["duplicate"] += 1
            print(f"Soru {index}: TEKRAR -> eklenmedi.")
            continue
        added.append(dict(question, id=str(uuid4())))
        keys.add(key)

    report["added"] = len(added)
    report["total"] = len(existing) + len(added)
    if not added:
        return report

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(existing + added, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return report
