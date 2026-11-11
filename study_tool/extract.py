import json
import sys
from pathlib import Path

import pymupdf

MAX_SINGLE = 55  # bu sayfa sayısına kadar tek chapter, üstü ikiye bölünür


def extract_pages(pdf_path):
    doc = pymupdf.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        pages.append({"page": i + 1, "text": page.get_text().strip()})
    return pages


def split_chapters(pages, split_at=None):
    n = len(pages)
    if n <= MAX_SINGLE:
        return [{"chapter": 1, "pages": pages}]
    cut = split_at if split_at else n // 2  # split_at: ikinci parçanın başladığı sayfa
    first = [p for p in pages if p["page"] < cut]
    second = [p for p in pages if p["page"] >= cut]
    return [{"chapter": 1, "pages": first}, {"chapter": 2, "pages": second}]


if __name__ == "__main__":
    pdf_path = Path(sys.argv[1])
    split_at = int(sys.argv[2]) if len(sys.argv) > 2 else None
    pages = extract_pages(pdf_path)
    chapters = split_chapters(pages, split_at)
    out = Path("data") / f"{pdf_path.stem}.json"
    out.write_text(json.dumps(
        {"source": pdf_path.name, "chapters": chapters},
        ensure_ascii=False, indent=2), encoding="utf-8")
    for c in chapters:
        print(f"Chapter {c['chapter']}: sayfa {c['pages'][0]['page']}-{c['pages'][-1]['page']}")
    print("Kaydedildi:", out)