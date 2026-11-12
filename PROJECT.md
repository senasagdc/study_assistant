# PROJECT.md (güncel durum: 11 Kasım 2026)

> AI asistana not: Bu dosya araçtan bağımsız proje bağlamıdır. Aşağıdaki kurallara uy ve “Bir sonraki adım” bölümünden devam et. Araç değişebilir (ChatGPT Codex, Claude vb.).

## Kullanıcı ve amaç
- Sena: BAU Yazılım Mühendisliği 4. sınıf + Endüstri Mühendisliği çift anadal.
- Python orta+, SQL biliyor; Git temel döngüsünü (add, commit, push) öğreniyor. Henüz tamamlanmış bir proje yok.
- Veri, AI, LLM ve agent geliştirmeyi gerçek bir araç yaparak öğrenmek istiyor.
- Haftada 6–8 saat; bütçe yok. Gemini API ücretsiz katman, Colab ve açık kaynak araçlar kullanılabilir. Gemini öğrenci paketi API kotası sağlıyor varsayılmayacak.
- Mac Apple Silicon, Python 3.13.1, VS Code (terminalden `code` komutu kurulu değil, dosyalar VS Code arayüzünden açılıyor).

## Tek proje: Kişisel Soru ve Tekrar Aracı
İngilizce Endüstri Mühendisliği ders PDF'lerinden kaynakla ilişkili kaliteli sorular üretmek, quiz çözmek ve zamanla yanlışları takip edip tekrar planlamak.

Özet ve konu anlatımını kullanıcı mevcut LLM sohbetleriyle yapacak. Notion özetini elle çıkarmak öğrenme sürecinin parçası. Study guide / otomatik özet üretimi proje kapsamından çıkarıldı. Fiş/harcama projesi iptal; başka proje yok.

### Kullanım akışı
1. Kullanıcı dersi LLM ile çalışır ve Notion özetini elle çıkarır.
2. Araç PDF metninden chapter bazında sorular üretir ve kaydeder.
3. Kullanıcı quiz çözer; cevaptan sonra doğru cevap, açıklama ve kaynak sayfayı görür.
4. Sonraki katmanlarda yanlışlar kalıcı tutulur, tekrar zamanı ve zayıf konular gösterilir.

### Kapsam ve soru biçimi
- Yalnızca metin ve tablo ağırlıklı İngilizce Endüstri Mühendisliği slaytları. Görsel ağırlıklı PDF'ler kapsam dışı.
- İlk soru türü: dört şıklı, tek doğru cevaplı MCQ. Diğer türler ihtiyaç doğarsa eklenir.
- Soru ve şıklar İngilizce; açıklama Türkçe, teknik terimler İngilizce.
- Soru stilleri (prompt'ta): (1) senaryo bazlı, uzun, düşündüren (en önemlisi; hesaplama ağırlıklı chapter'larda word problem olarak), (2) kavram soruları (tanım, fark, "hangisi doğru değil", kavram tanıma, ne zaman kullanılır), (3) hesaplama soruları (önemli), (4) slayttaki örnek sorular.
- Şıklar sözlük: `"options": {"A": "...", "B": "...", "C": "...", "D": "..."}`; `correct_answer` yalnızca harf.
- Her soru: id, type ("mcq"), question, options, correct_answer, explanation, topic, source_pages (orijinal PDF'in 1 tabanlı sayfa numaraları).
- Sorular verilen metne dayanmalı; kaynakta bulunmayan bilgi gerektirmemeli.
- JSON schema doğrulaması yalnızca biçimi ve alanları kontrol eder; sorunun doğruluğunu, cevap anahtarını veya kalitesini garanti etmez. Üretilen sorular kullanıcı tarafından PDF ile karşılaştırılır. Hesaplama sorularında cevap anahtarı hatası gerçek bir risk (ilk denemede eşik 490 iken açıklamada 500 kullanılmış, cevap yanlış işaretlenmişti).
- Her PDF/chapter için tek `_questions.json` bankası kullanılır; yeni üretim geçerli ve yeni soruları bu listeye ekler, eskileri değiştirmez. Soru metninde case ve whitespace farkları yok sayılarak önceki banka ve aynı üretim içinde tekrar kontrolü yapılır. Anlamsal benzerlik ve cevap doğruluğu denetlenmez. Yeni kabul edilen sorulara UUID atanır; eski ID'ler korunur.
- Mevcut banka bozuksa veya ID'ler çakışıyorsa işlem durur. Yazma geçici dosya + atomic replace ile yapılır. Bu, eşzamanlı birden fazla üretimin güncellemelerini birleştirmez; şimdilik üretimler sırayla çalıştırılmalı.
- Uzun vadeli hedef: PDF, chapter, üretim ve sorular ilişkili tutulacak; her haftanın soruları ayrı seçilebilecek ve birden fazla haftadan mixed/final exam hazırlanabilecek. Ayrı haftalar için ayrı SQL tabloları yerine ilişkili ortak tablolar kullanılacak. Mevcut SQLite prototipi bu modele henüz uyarlanmadı.

## Katmanlar
1. PDF → sayfa metinleri → chapter → JSON (PyMuPDF). TAMAM.
2. Gemini ile soru JSON üretimi. NEREDEYSE TAMAM: prompt dosyası, `core/llm.py`, schema doğrulama, üretim komutu çalışıyor. Eksik: geçersiz JSON için modele düzeltme retry'ı yok (şimdilik yalnızca fazladan virgül temizleme).
3. Terminal quiz: TAMAM. `study_tool/quiz.py` soru JSON'unu doğrular, cevapları sırayla alır, her cevaptan sonra doğru şık, açıklama ve kaynak sayfaları gösterir; sonunda puan verir. Küçük harf, geçersiz giriş ve Q ile çıkış desteklenir. Kullanıcı 5 soruluk quiz'i çalıştırdı; 2 doğru / 3 yanlış ve %40 sonucu doğru hesaplandı. 12 Kasım 2026: quiz artık SQLite'tan okur ve her cevabı kaydeder (aşağıya bak).
4. SQLite ile soru/cevap geçmişi: ALTYAPI EKLENDİ. `study_tool/storage.py`: `connect_db`, `save_question`, `save_attempt`. Varsayılan database `data/study.db`; questions ve attempts tabloları. Aynı kaynak yolu ve aynı soru içeriği yeniden kaydedilmez; değişen içerik ayrı kayıt olur. Cevaplar doğruluk ve UTC zamanıyla ayrı ayrı kaydedilir. Geçici database ile kalıcılık, tekrar önleme ve doğru/yanlış cevap kontrolleri geçti. Quiz henüz bu katmana bağlı değil. Yanlış takibi ve Leitner zamanlaması bekliyor.
5. Streamlit arayüzü, zamanı gelen tekrarlar ve konu bazlı zayıf nokta raporu.
6. Bonus: embedding ile kavramın slaytta geçtiği yeri arama. Şimdilik yapılmayacak.

## Çalışma kuralları
- Kodun çoğunu asistan yazar; kullanıcı çalıştırıp sonucu getirir. Dosya yazabilen araç da ne yaptığını açıklamalı; kullanıcı anlamadan büyük değişiklik yapılmamalı.
- Önce kısa plan, sonra kod. Her kod parçasından sonra ne yaptığı, neden bu yaklaşımın seçildiği ve alternatif kısaca açıklanır.
- Kod eklenmeden önce ne yapacağı ve nedeni açıklanır.
- Her adım sonunda asistan PROJECT.md'yi günceller ve ilgili dosyalar için Git commit komutlarını verir; kullanıcıdan ayrıca hatırlatma beklemez.
- Bir seferde tek küçük adım; kullanıcı sonucu getirmeden sonraki uygulama adımına geçilmez.
- Yeni kavram ilk geçtiğinde 2–3 cümleyle öğretilir. Türkçe konuşulur; teknik terimler İngilizce kalır.
- Her yanıtta en fazla bir soru. Gereksiz mimari, teknoloji ve bonus özellik eklenmez.
- Git gerektiği kadar öğretilir; commit'ten önce `git status --short` ile bakılır, seans sonunda commit alışkanlığı kazandırılır.
- Anahtarlar .env içinde, .env ve data/ Git dışında. Anahtarlar sohbete yapıştırılmaz. Asistan .env ve data/ içeriğini okumaz veya göndermez.
- Soru üretme komutu seçilen chapter metnini Gemini API'ye gönderir. Önceki izin kaydı yarım kalmış; yeni API çağrısı öncesinde izin durumu netleştirilmeli. Terminal quiz API kullanmaz.

## Bir sonraki adım
- JSON bankasına ekleme davranışı uygulandı: `study_tool/question_bank.py`, üretim entegrasyonu, 4 otomatik test. Schema şık sırasından bağımsız A–D anahtarlarını kabul eder ve pozitif sayfa numarası ister. Mevcut kullanıcı verileri okunmadı; API çağrısı yapılmadı.
- JSON import komutu eklendi: `study_tool/import_bank.py`. PDF hash'i hesaplanır; chapter metni PDF sayfalarıyla karşılaştırılır. Chapter aralığı ve soru kaynakları doğrulanır. Eski JSON ID'leri ve içerikleri korunur. Aynı ID/aynı içerik atlanır, aynı metin/farklı ID tekrar sayılır; aynı ID/farklı içerik veya değişen chapter aralığı tüm transaction'ı geri alır. Kaynak dosyalar değişmez. Yalnızca yeni sorular varsa import generation kaydı eklenir; geçmiş üretim tarihleri bilinmediğinden uydurulmaz.
- 11 Kasım 2026: Çalışma Claude'a taşındı. Kullanıcı 14 testi kendi Mac'inde çalıştırdı, hepsi geçti. Gerçek veri aktarımı doğrulandı: `QualityManagementWeek5` chapter 1, database'de 5 soruyla kayıtlı (chapter database ID 1). Import iki kez çalıştırıldı, ikisinde de "Eklenen: 0 | Zaten kayıtlı: 5" çıktı. Yani 5 soru daha önceki bir çalıştırmada aktarılmış ve tekrar import kayıt çoğaltmıyor (idempotent). Asistan data/ veya .env içeriğini okumadı.
- zsh notu: `#` ile başlayan yorum satırları terminale yapıştırılınca zsh `parse error` verebilir (interactive comments varsayılan olarak kapalı). Komutları yorumsuz yapıştır.
- Üretimin SQLite'a kaydı UYGULANDI (asistan, kullanıcı doğrulaması bekliyor). `import_bank.py`: `prepare_chapter` (PDF/chapter doğrulaması) ayrıldı; `import_questions(..., kind="import"|"llm", model=None)`. `generate.py` artık argparse kullanır (`--pdf`, `--db` isteğe bağlı; PDF varsayılan olarak çıkarılmış JSON'daki `source` adıyla aynı klasörde aranır). Akış: API'den ÖNCE PDF ve banka doğrulanır, JSON'da olup database'de olmayan eski sorular `import` olarak eşitlenir → Gemini → JSON bankasına ekleme → yeni sorular `kind='llm'`, model adı ve "Generated by LLM" nedeniyle SQLite'a. Yeni soru yoksa generation açılmaz. SQLite yazımı başarısız olursa JSON kalır, import komutuyla eşitlenebilir (o durumda kind 'import' görünür). `tests/test_generate.py`: sahte `core.llm` ile 3 test, API çağrısı yok. Container'da gerçek pymupdf olmadığı için asistan testleri sahte bir pymupdf ile çalıştırdı (17/17); gerçek doğrulama kullanıcının Mac'inde yapılacak.
- 12 Kasım 2026 KULLANICI DOĞRULADI: Mac'te 17/17 test geçti (commit 42c31a2). Kullanıcının izniyle gerçek üretim çalıştırıldı (chapter 1, 5 soru istendi): 5 geldi, 5 eklendi, 0 geçersiz, 0 tekrar. Önce: generations `1|import||5`, JSON 5. Sonra: `1|import||5` ve `2|llm|gemini-3.5-flash-lite|5`, JSON 10. JSON ve SQLite tutarlı. Yeni 5 sorunun içerik doğruluğu henüz PDF ile kontrol edilmedi.
- Gerçek üretim komutu (API kullanır; her yeni API çağrısı öncesi kullanıcı onayı alınır): `python -m study_tool.generate data/QualityManagementWeek5.json 1 5`
- Quiz SQLite'a bağlandı UYGULANDI (asistan, kullanıcı doğrulaması bekliyor). `study_tool/quiz.py`: PDF içerik hash'i + chapter no ile chapter bulunur; her sorunun son sürümü (version_no en büyük) sorulur; her cevap gösterilmeden önce `answer_attempts` tablosuna question_version_id ile hemen kaydedilir (Q/çökme olsa da önceki cevaplar kalır). Doğruluk database'deki cevap anahtarından hesaplanır. JSON okuma modu kaldırıldı; JSON dosyaları silinmez, import/export için kalır. Eski storage.py `save_question`/`save_attempt` ve questions/attempts prototip tabloları kullanılmıyor ama silinmedi. `tests/test_quiz.py`: 4 test (sahte input, geçici database). Asistan sahte pymupdf ile 21/21 test çalıştırdı.
- Quiz komutu (proje kökünden): `python -m study_tool.quiz data/QualityManagementWeek5.pdf 1` (alternatif database için `--db`). API kullanılmaz.
- 12 Kasım 2026 KULLANICI DOĞRULADI (commit 9941e13): gerçek quiz 10 soruyu database'den getirdi; 10 cevap answer_attempts'e kaydedildi, ekrandaki Doğru/Yanlış ile is_correct değerleri birebir eşleşti. Q ile çıkışta 0 kayıt. answered_at UTC (Türkiye saati = UTC+3). Ayrıca 23:57:45 UTC tarihli, daha önceki bir oturumdan kalan 1 cevap var. Kullanıcı bu adımda birim testlerin çıktısını paylaşmadı.
- Soru kalitesi bulguları (generation 2, asistan hesapları kontrol etti; 10 sorunun cevap anahtarı doğru): (1) Anlamsal tekrar: yeni sorular eski soruların aynı slayt örneklerini başka kelimelerle tekrar ediyor (Q1≈Q7 dolum hedefi 509.3, Q4≈Q6 kayma sonrası 0.0670, Q2≈Q10 R(200)=0.6703). Metin bazlı tekrar kontrolü bunları yakalamaz. Olası çözüm: prompt'a mevcut soruların konu/özet listesini verip farklı soru istemek. (2) Biçim: yeni açıklamalar "Türkçe Açıklama:" önekiyle başlıyor ve terminalde ham görünen LaTeX ($...$, \Phi) kullanıyor; prompt'a düz metin kuralı eklenmeli. (3) Bazı kelimeler bitişik (ör. "ikenz", "0.002failures"). (4) Soru 9'un source_pages değerinde açıklamada geçmeyen 23 var; PDF ile kontrol edilmeli. Bunlar SQLite aşaması bittikten sonra prompt iyileştirmesi olarak ele alınacak.
- Prompt iyileştirmesi UYGULANDI (12 Kasım, asistan; kullanıcı doğrulaması bekliyor). Kullanıcı kararları: (1) slayttaki çözümlü örnekler kopyalanmaz; yöntem yeni senaryo ve yeni sayılarla kullanılabilir (eski stil 4 'slayt örneğini sayılarıyla koru' kaldırıldı). (2) Matematik düz metne çevrilmez; UI'de (Streamlit Markdown) render edilecek şekilde tutarlı inline LaTeX `$...$` kullanılır; terminalde ham görünmesi kabul. Para için `$` yerine USD. Açıklamada "Türkçe Açıklama:" gibi önek yok; kelime ile sayı/birim arasında boşluk. (3) Soru 9 sayfa 23 kullanıcı tarafından uygun bulundu.
- Anlamsal tekrara karşı: prompt'a {EXISTING_QUESTIONS} bölümü eklendi; `generate.py` chapter'daki mevcut soruları `- [topic] soru metni` (en fazla 300 karakter) listesi olarak verir ve modelden aynı durumu, sayıları veya test edilen fikri tekrar etmemesini ister. Bu bir garanti değildir; tekrarlar hâlâ kullanıcı tarafından quiz'de fark edilebilir. Banka çok büyürse liste prompt'u uzatır; o zaman konu bazlı özet düşünülür.
- LaTeX/JSON koruması: tek ters bölülü LaTeX (\\Phi) JSON'u bozarsa yedek ayrıştırmada geçersiz kaçışlar ikiye katlanır (geçerli kaçışlar korunur). \\times, \\frac, \\beta, \\rho gibi ifadeler JSON'da sessizce TAB/form feed/backspace/CR karakterine dönüşeceği için bu karakterleri içeren soru GEÇERSİZ sayılır ve eklenmez. Testler: 23 (asistan sahte pymupdf ile çalıştırdı). Eski 10 sorunun mevcut biçimi değiştirilmedi.
- SEANS DURDU (12 Kasım 03:06). Yarın buradan başla: (1) kullanıcı 23 testi çalıştırıp prompt değişikliklerini commit eder; (2) izin verirse yeni prompt'la 5 soruluk gerçek üretim denenir ve slayt kopyası, eski sorulara benzerlik ve LaTeX biçimi kontrol edilir; (3) ardından JSON export + tarihli yedek (plan kabul edildi: export_bank.py round-trip testiyle; backup.py sqlite backup() + integrity_check + tablo sayısı karşılaştırması; data/backups/ altında; otomatik restore komutu yok, elle kopyalama adımları yazılacak).
- SQLite'ta hâlâ eksik olanlar: JSON export, tarihli yedek/geri yükleme kontrolü.
- SONRA EKLENECEK (kullanıcı fikri, 12 Kasım'da sadeleştirildi; deployment sonrası, şimdi uygulanmayacak): tekrar kuralı. Sorunun EN SON cevabı yanlışsa tekrar sorulur, doğruysa sorulmaz. Hiç cevaplanmamış soru sorulur. answer_attempts geçmişinden hesaplanır; ek tablo gerekmez.
- Import komutu: `python -m study_tool.import_bank data/QualityManagementWeek5.pdf data/QualityManagementWeek5.json 1 data/QualityManagementWeek5_ch1_questions.json` (alternatif database için `--db`). API kullanılmaz.
- Testler: `python -m unittest discover -s tests -v`

## Kabul edilen SQLite hedefi ve çalışma düzeni
- Asıl kayıt SQLite olacak: PDF/chapter, üretim, soru, soru sürümü ve kullanıcı cevapları. JSON yalnızca import/export biçimi olacak; geçiş tamamlanana kadar mevcut üretim ve quiz JSON kullanmaya devam ediyor.
- `study_tool/database_schema.sql` eklendi; `connect_db()` yeni tabloları da oluşturur. Tablolar: documents, chapters, generations, bank_questions, question_versions, answer_attempts. Eski questions/attempts prototipi silinmez ve henüz taşınmaz.
- documents.content_hash PDF kimliğidir; import komutu hash hesaplar ve belgeyi kaydeder. bank_questions.original_id eski JSON ID'sini chapter içinde korur. Cevaplar question_versions kaydına bağlanır. Schema tek başına sürümleri değişmez yapmaz; import eski içeriği değiştirmez, yalnızca ilk sürümü ekler. Gelecekte güncelleme fonksiyonları yeni sürüm eklemeli. JSON içerik doğrulaması Python katmanında yapılır.
- SQLite bitiş çizgisi: veri modeli → JSON import → üretimin SQLite'a kaydı → quiz cevaplarının kaydı → JSON export ve tarihli yedek/geri yükleme kontrolü. Bilgisayar dışı yedek konumu henüz belirlenmedi. Mixed exam, Leitner ve arayüz bu aşamada eklenmez.
- Kullanıcı SQLite aşaması bitene kadar açıklamalı uygulamayı yetkilendirdi. Her adım önceden açıklanır; kullanıcı sonucundan önce sonraki uygulamaya geçilmez. SQLite tamamlanınca açıkça DUR: dosyaları ve veri akışını birlikte incele; ardından açıklama → kodu gösterme → kullanıcının uygulaması düzenine dön. Yeni özellik için otomatik kod değişikliği yapma.
