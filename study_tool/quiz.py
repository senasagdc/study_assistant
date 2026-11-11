import argparse
import json
from pathlib import Path

from study_tool.schema import OPTION_KEYS, validate_question


def load_questions(path):
    """Kaydedilmiş soru listesini okur ve biçimini kontrol eder."""
    questions = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(questions, list) or not questions:
        raise ValueError("Dosya boş olmayan bir soru listesi içermeli.")
    for index, question in enumerate(questions, start=1):
        errors = validate_question(question)
        if errors:
            raise ValueError(f"Soru {index}: {'; '.join(errors)}")
    return questions


def run_quiz(questions):
    """Cevapları alır, geri bildirim gösterir ve oturum sonucunu hesaplar."""
    correct = 0
    answered = 0
    print("Cevap için A–D, çıkmak için Q yazabilirsin.")
    for index, question in enumerate(questions, start=1):
        print(f"\nSoru {index}/{len(questions)} — {question['topic']}")
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
        answered += 1
        expected = question["correct_answer"]
        if answer == expected:
            correct += 1
            print("Doğru!")
        else:
            print("Yanlış.")
        print(f"Doğru cevap: {expected}) {question['options'][expected]}")
        print(f"Açıklama: {question['explanation']}")
        print("Kaynak PDF sayfaları: " + ", ".join(map(str, question["source_pages"])))

    print(f"\nSonuç: {answered}/{len(questions)} soru cevaplandı.")
    print(f"Doğru: {correct} | Yanlış: {answered - correct}")
    if answered:
        print(f"Başarı (cevaplanan sorularda): %{100 * correct / answered:.1f}")
    print("Bu oturumun sonuçları kaydedilmedi.")


def main():
    parser = argparse.ArgumentParser(description="Kaydedilmiş MCQ sorularını terminalde çöz.")
    parser.add_argument("questions_path", type=Path, help="Soru JSON dosyasının yolu")
    args = parser.parse_args()
    try:
        questions = load_questions(args.questions_path)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Sorular yüklenemedi: {error}\n")
    run_quiz(questions)


if __name__ == "__main__":
    main()
