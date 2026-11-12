# PROJECT.md (güncel durum: 12 Kasım 2026)

> AI asistana not: Bu dosya araçtan bağımsız proje bağlamıdır. Aşağıdaki kurallara uy ve "Bir sonraki adım" bölümünden devam et. Araç değişebilir (ChatGPT Codex, Claude, Claude Code vb.). 12 Kasım 2026'da çalışma Claude (sohbet) üzerinden Claude Code'a devredildi.

## Kullanıcı ve amaç
- Sena: BAU Yazılım Mühendisliği 4. sınıf + Endüstri Mühendisliği çift anadal.
- Python orta+, SQL biliyor; Git temel döngüsünü (add, commit, push) öğreniyor. Henüz tamamlanmış bir proje yok.
- Veri, AI, LLM ve agent geliştirmeyi gerçek bir araç yaparak öğrenmek istiyor.
- Haftada 6–8 saat; bütçe yok. Gemini API ücretsiz katman, Colab ve açık kaynak araçlar kullanılabilir. Gemini öğrenci paketi API kotası sağlıyor varsayılmayacak.
- Mac Apple Silicon, Python 3.13.1, VS Code (terminalden `code` komutu kurulu değil), zsh. Proje: `~/projects/ai-tools`, sanal ortam `.venv`.

## Tek proje: Kişisel Soru ve Tekrar Aracı
Endüstri Mühendisliği (ve ileride başka) derslerin İngilizce PDF slaytlarından kaynakla ilişkili kaliteli sorular üretmek, quiz çözmek ve zamanla yanlışları takip edip tekrar planlamak. Hedef: kullanıcı sisteme herhangi bir dersin slaytını yükler ve soru alır; araç birden fazla dersi destekler. Kullanıcılar: Sena ve en fazla birkaç arkadaşı.

Özet ve konu anlatımını kullanıcı mevcut LLM sohbetleriyle yapacak. Notion özetini elle çıkarmak öğrenme sürecinin parçası. Study guide / otomatik özet üretimi kapsam dışı. Başka proje yok.

### Kullanım akışı
1. Kullanıcı dersi LLM ile çalışır ve Notion özetini elle çıkarır.
2. Araç PDF metninden chapter bazında sorular üretir ve kaydeder.
3. Kullanıcı quiz çözer; cevaptan sonra doğru cevap, açıklama ve kaynak sayfayı görür.
4. Sonraki katmanlarda yanlışlar tekrar sorulur ve zayıf konular gösterilir.

### Kapsam ve soru biçimi
- Yalnızca metin ve tablo ağırlıklı İngilizce slaytlar. Görsel ağırlıklı PDF'ler kapsam dışı.
- Soru türü: dört şıklı, tek doğru cevaplı MCQ. Diğer türler ihtiyaç doğarsa eklenir.
- Soru ve şıklar İngilizce; açıklama Türkçe, teknik terimler İngilizce.
- Soru stilleri (prompt'ta): (1) senaryo bazlı, uzun, düşündüren (en önemlisi; hesaplama ağırlıklı chapter'larda word problem), (2) kavram soruları, (3) hesaplama soruları (önemli). Slayttaki çözümlü örnekler KOPYALANMAZ; yöntem yeni senaryo ve yeni sayılarla kullanılabilir.
- Matematik: Streamlit Markdown'da render edilecek inline LaTeX `$...$`; JSON içinde ters bölüler iki kez yazılır. Para için `$` değil USD. Açıklamada "Türkçe Açıklama:" gibi önek yok. Terminalde ham LaTeX görünmesi kabul.
- Şıklar sözlük: `"options": {"A": "...", "B": "...", "C": "...", "D": "..."}`; `correct_answer` yalnızca harf.
- Her soru: id, type ("mcq"), question, options, correct_answer, explanation, topic, source_pages (orijinal PDF'in 1 tabanlı sayfa numaraları).
- Sorular verilen metne dayanmalı; kaynakta olmayan bilgi gerektirmemeli.
- Schema doğrulaması yalnızca biçimi kontrol eder; doğruluk/kalite garanti değildir. Kullanıcı soruları PDF ile karşılaştırır. Hesaplama sorularında cevap anahtarı hatası gerçek bir risk.
- Tekrar kontrolü: soru metninde case/whitespace yok sayılarak birebir tekrar engellenir. Anlamsal tekrara karşı prompt'a chapter'daki mevcut sorular (`- [topic] metin`, en fazla 300 karakter) verilir; bu garanti değildir.

## Mimari (12 Kasım 2026)
Asıl kayıt SQLite (`data/study.db`). JSON soru bankaları (`data/<pdf>_ch<N>_questions.json`) geçiş sürecinde paralel tutuluyor; uzun vadede yalnızca import/export biçimi.

### Database tabloları
- `courses (id, name UNIQUE NOCASE)`: dersler.
- `users (id, name UNIQUE NOCASE)`: kullanıcılar (Sena + arkadaşlar).
- `documents (id, content_hash UNIQUE, filename, course TEXT [eski, kullanılmıyor], week, course_id → courses)`: PDF kimliği içerik hash'idir; dosya adı değişse de tanınır.
- `chapters (id, document_id, chapter_no, start_page, end_page)`.
- `generations (id, chapter_id, kind 'import'|'llm', model, created_at)`.
- `bank_questions (id, chapter_id, original_id, generation_id)`: original_id JSON'daki ID.
- `question_versions (id, question_id, version_no, question_json, change_reason)`: quiz her sorunun en yüksek version_no'lu sürümünü sorar. Düzeltmeler yeni sürüm olarak eklenmeli (henüz fonksiyonu yok).
- `answer_attempts (id, question_version_id, selected_answer, is_correct, answered_at UTC, user_id → users)`: her cevap ayrı satır.
- Eski prototip tablolar `questions`/`attempts` ve `storage.save_question`/`save_attempt` kullanılmıyor; silinmedi.
- Normalizasyon kararı: ders bilgisi yalnızca `documents.course_id`'de; soru → chapter → document → course zinciriyle bulunur. Her ders için ayrı database yok.
- Migration: `storage.py` içinde `MIGRATIONS` listesi ve `PRAGMA user_version`. `connect_db()` eksik migration'ları sırayla, her birini tek transaction'da uygular. Migration 1: `documents.course_id`, `answer_attempts.user_id`. SQLite `ALTER TABLE ADD COLUMN` ile NOT NULL FK eklenemediği için bu sütunlar DB'de NULL olabilir; kurallar Python'da: quiz kullanıcısız cevap kaydetmez; derssiz PDF'ler `manage list`'te "(derssiz PDF)" olarak görünür.

### Dosyalar
- `study_tool/extract.py`: PDF → sayfa metinleri → chapter JSON (PyMuPDF).
- `study_tool/schema.py`: soru doğrulama.
- `study_tool/question_bank.py`: JSON bankasına güvenli ekleme (UUID, atomic replace).
- `study_tool/import_bank.py`: `prepare_chapter` (PDF hash + chapter metni PDF ile karşılaştırma), `prepare_import`, `import_questions(conn, prepared, kind, model, course)`. Tek transaction; çakışmada (aynı ID/farklı içerik, değişen chapter aralığı, başka derse bağlı PDF, bilinmeyen ders) tamamı geri alınır. Idempotent.
- `study_tool/generate.py`: API'den ÖNCE PDF/banka doğrulanır ve JSON'da olup DB'de olmayan eski sorular `import` olarak eşitlenir → Gemini → JSON bankası → yeni sorular `kind='llm'` + model adıyla SQLite'a. Tek ters bölülü LaTeX onarılır; JSON'da sessizce bozulan LaTeX (`\times`→TAB vb.) içeren soru geçersiz sayılır.
- `study_tool/quiz.py`: PDF hash + chapter no ile chapter bulunur, `--user` zorunlu; her cevap geri bildirimden önce kaydedilir.
- `study_tool/manage.py`: `add-course`, `add-user`, `set-course PDF DERS`, `claim-attempts KULLANICI` (kullanıcısız eski cevapları bağlar), `list`. Bir PDF başka derse bağlıysa taşınmaz (hata).
- `study_tool/storage.py`: `connect_db`, migration'lar.
- `study_tool/export_bank.py`: SQLite → JSON (her sorunun son sürümü), var olan dosyanın üzerine yazmaz.
- `study_tool/backup.py`: tarihli, doğrulanmış database yedeği (`data/backups/`).
- `core/llm.py`: Gemini (`gemini-3.5-flash-lite`), 429/503 retry.
- `prompts/generate_questions.txt`: prompt; `{N_QUESTIONS}`, `{EXISTING_QUESTIONS}`, `{CHAPTER_TEXT}`.
- `tests/`: 36 test (`unittest`). Gemini testlerde sahte `core.llm` modülüyle değiştirilir; API çağrısı yok.

## Katmanlar
1. PDF → chapter JSON. TAMAM.
2. Gemini ile soru üretimi. TAMAM (eksik: geçersiz JSON'da modele düzeltme retry'ı yok).
3. Terminal quiz. TAMAM, SQLite'tan okur ve cevap kaydeder.
4. SQLite. KOD TAMAM: veri modeli, import, üretim kaydı, quiz kaydı, dersler/kullanıcılar, JSON export, doğrulanmış yedek. Export ve yedek gerçek database'de henüz çalıştırılmadı; bilgisayar dışı yedek konumu belirlenmedi.
5. Streamlit arayüzü (slayt yükleme dahil), tekrar kuralı, konu bazlı zayıf nokta raporu.
6. Bonus: embedding ile kavram arama. Şimdilik yapılmayacak.

## Çalışma kuralları
- Kodun çoğunu asistan yazar; kullanıcı çalıştırıp sonucu getirir. Dosya yazabilen araç da ne yaptığını açıklamalı; kullanıcı anlamadan büyük değişiklik yapılmamalı.
- Önce kısa plan, sonra kod. Her kod parçasından sonra ne yaptığı, neden bu yaklaşımın seçildiği ve alternatif kısaca açıklanır.
- Her adım sonunda asistan PROJECT.md'yi günceller ve ilgili dosyalar için Git commit komutlarını verir; kullanıcıdan hatırlatma beklemez.
- Bir seferde tek küçük adım; kullanıcı sonucu getirmeden sonraki uygulama adımına geçilmez.
- Yeni kavram ilk geçtiğinde 2–3 cümleyle öğretilir. Türkçe konuşulur; teknik terimler İngilizce kalır.
- Her yanıtta en fazla bir soru. Gereksiz mimari, teknoloji ve bonus özellik eklenmez.
- Git gerektiği kadar öğretilir; commit'ten önce `git status --short`; seans sonunda commit (ve isterse push).
- Terminale verilen komutlarda `#` yorum satırı olmasın (zsh `parse error near ')'` veriyor). Her komut ayrı kod bloğunda.
- Anahtarlar .env içinde; .env ve data/ Git dışında. Anahtarlar sohbete yapıştırılmaz. Asistan .env ve data/ İÇERİĞİNİ okumaz veya göndermez (sayı/etiket gösteren sorguları kullanıcı çalıştırır).
- Gemini API çağrısı (generate komutu) chapter metnini dışarı gönderir: HER gerçek üretimden önce kullanıcı onayı alınır. Testler ve quiz API kullanmaz.
- SQLite aşaması bitince açıkça DUR: dosyaları ve veri akışını kullanıcıyla birlikte incele; ardından açıklama → kodu gösterme → kullanıcının uygulaması düzenine dön. Yeni özellik için otomatik kod değişikliği yapma.

## Doğrulanmış geçmiş (özet)
- 11 Kasım: 14 test Mac'te geçti; gerçek import doğrulandı (QualityManagementWeek5 ch1, 5 soru), tekrar import idempotent.
- 12 Kasım: üretim → SQLite doğrulandı (commit 42c31a2): generations `1|import||5`, `2|llm|gemini-3.5-flash-lite|5`; JSON 10. Quiz → SQLite doğrulandı (commit 9941e13): 10 cevap kaydedildi, ekranla birebir. 10 sorunun cevap anahtarı asistan tarafından doğru bulundu; ama eski prompt slayt örneklerini tekrar ettirdi (Q1≈Q7, Q4≈Q6, Q2≈Q10) ve LaTeX/önek biçimi tutarsızdı → prompt iyileştirildi (commit 75eff52, 23 test kullanıcıda geçti). Yeni prompt henüz gerçek üretimle denenmedi.
- 12 Kasım (Claude Code): ders/kullanıcı yapısı Mac'te doğrulandı. 30 test gerçek pymupdf ile geçti. Elle yedek `data/study_before_migration.db` alındı; migration 1 ilk `manage list` ile uygulandı ("(derssiz PDF)" ve "(kullanıcısız cevap) 11" görüldü). `add-course "Quality Management"`, `set-course`, `add-user Sena`, `claim-attempts Sena` (11 cevap bağlandı) çalıştı. Tekrar çalıştırmalar güvenli: `set-course` değişiklik yapmadı, `add-user` "zaten kayıtlı" hatası verdi, `claim-attempts` 0 cevap bağladı. Quiz `--user Sena` ile çalıştı; yeni cevaplar Sena'ya kaydedildi (liste 11 → 38).
- Not: Claude Code uygulamasının komut satırı (`!`/bash-input) klavye girdisi alamaz; quiz VS Code terminalinde veya Terminal panelinde çalıştırılmalı.
- Mevcut gerçek veri: 1 ders (Quality Management), 1 PDF, 1 chapter, 10 soru, 1 kullanıcı (Sena), 38 cevap.

## Bir sonraki adım
DURUM: Ders/kullanıcı yapısı commit edildi (103f2d4). SQLite'ın son adımı kullanıcının tam izniyle asistan tarafından yazıldı ve commit edildi; 36 test Mac'te (asistan, `.venv`, gerçek pymupdf) geçti. GERÇEK DATABASE ÜZERİNDE HENÜZ ÇALIŞTIRILMADI.
- `study_tool/export_bank.py`: PDF (hash) + chapter için her sorunun son sürümünü, eklenme sırasıyla import'un okuduğu JSON listesi olarak yazar. JSON içindeki `id` ile `original_id` uyuşmazsa veya soru schema'dan geçmezse durur. Var olan dosyanın üzerine yazmaz (`os.link` ile atomik). Testler: export → boş DB'ye import → birebir aynı; son sürüm kullanılır; var olan dosya korunur.
- `study_tool/backup.py`: kaynağı salt okunur (`mode=ro`) açar, `Connection.backup()` ile `data/backups/study_YYYY-MM-DD_HHMMSS.db` yazar; kopyada `PRAGMA integrity_check` = ok ve her tablonun satır sayısı asılla aynı olmalı, değilse kopya silinir. Var olan yedeğin üzerine yazmaz; olmayan database'i oluşturmaz. `--dest` ile başka klasör (ör. iCloud Drive) verilebilir.

Kullanıcının yapacakları (her komut ayrı):
1. `python -m study_tool.backup` → `integrity_check: ok` ve tablo sayıları (beklenen: courses 1, users 1, documents 1, chapters 1, bank_questions 10, answer_attempts 38).
2. `python -m study_tool.export_bank data/QualityManagementWeek5.pdf 1 data/export_ch1.json` → "10 soru yazıldı".
3. (İsteğe bağlı) export'u var olan banka dosyasıyla karşılaştırma: `diff <(python -m json.tool data/export_ch1.json) <(python -m json.tool data/QualityManagementWeek5_ch1_questions.json)` → çıktı yoksa birebir aynı.
4. Bilgisayar dışı yedek konumu kararı (iCloud Drive / Google Drive klasörü).

Elle geri yükleme (otomatik komut YOK):
1. Quiz/generate gibi database kullanan komut çalışmıyor olmalı.
2. Mevcut hâli sakla: `cp data/study.db data/study_before_restore.db`
3. Yedeği geri koy: `cp data/backups/study_YYYY-MM-DD_HHMMSS.db data/study.db`
4. Kontrol: `python -m study_tool.manage list`

Sonra:
- SQLite aşaması BİTTİ sayılır → DUR ve dosyaları/veri akışını birlikte incele (Çalışma kuralları). Ardından açıklama → kodu gösterme → kullanıcının uygulaması düzeni.
- (İsteğe bağlı, API onayıyla) yeni prompt'la gerçek üretim: `python -m study_tool.generate data/QualityManagementWeek5.json 1 5`. Kontrol: slayt örneği kopyası yok, eski sorulara anlamsal benzerlik yok, LaTeX `$...$` içinde ve tutarlı.

## Sonraya bırakılan kararlar
- TEKRAR KURALI (kullanıcı kararı, deployment sonrası): sorunun o kullanıcıya ait EN SON cevabı yanlışsa tekrar sorulur, doğruysa sorulmaz; hiç cevaplanmamış soru sorulur. answer_attempts'ten (user_id ile) hesaplanır; ek tablo gerekmez.
- HOSTED DATABASE (deployment adımında karar): kullanıcı birkaç arkadaşıyla kullanacak; Streamlit Cloud'da yerel SQLite dosyası kalıcı olmayabilir. 12 Kasım araştırması: Turso (SQLite uyumlu, kod en az değişir; ücretsiz 100 DB, 5 GB; Turso'nun Supabase'e katıldığı duyuruldu, koşullar tekrar kontrol edilmeli), Neon (PostgreSQL, ücretsiz proje başına 1 GB, 5 dk sonra uyur ve hızlı uyanır), Supabase (PostgreSQL, 500 MB, 1 hafta kullanılmazsa durdurulur). Ön eğilim: Turso. O zamana kadar veri tarihli yedekle korunur.
- Mixed/final exam: `documents.week` ve `course_id` üzerinden hafta/ders seçimi. Arayüz aşamasında.
- Geçersiz JSON'da modelden düzeltme isteyen retry.
- Soru düzeltme fonksiyonu (yeni question_version ekleyerek).

## Komutlar (proje kökünden, `.venv` aktif)
- Testler: `python -m unittest discover -s tests -v`
- PDF → chapter JSON: `python -m study_tool.extract data/<pdf>.pdf`
- Import: `python -m study_tool.import_bank data/QualityManagementWeek5.pdf data/QualityManagementWeek5.json 1 data/QualityManagementWeek5_ch1_questions.json [--course "Ders"]`
- Üretim (API, onay gerekir): `python -m study_tool.generate data/QualityManagementWeek5.json 1 5 [--course "Ders"]`
- Quiz: `python -m study_tool.quiz data/QualityManagementWeek5.pdf 1 --user Sena`
- Yönetim: `python -m study_tool.manage list | add-course AD | add-user AD | set-course PDF DERS | claim-attempts KULLANICI`
- Export: `python -m study_tool.export_bank data/QualityManagementWeek5.pdf 1 data/export_ch1.json`
- Yedek: `python -m study_tool.backup [--dest KLASÖR]`
- Tüm komutlarda alternatif database için `--db YOL`.
- Yeni bir ders/PDF için: `manage add-course` → `extract` → `generate ... --course "Ders"`.
