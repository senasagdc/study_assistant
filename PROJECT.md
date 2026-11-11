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
3. Terminal quiz: TAMAM. `study_tool/quiz.py` soru JSON'unu doğrular, cevapları sırayla alır, her cevaptan sonra doğru şık, açıklama ve kaynak sayfaları gösterir; sonunda puan verir. Küçük harf, geçersiz giriş ve Q ile çıkış desteklenir. Kullanıcı 5 soruluk quiz'i çalıştırdı; 2 doğru / 3 yanlış ve %40 sonucu doğru hesaplandı. Sonuçlar henüz kaydedilmez.
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
- Kullanıcı `python -m unittest discover -s tests -v` ile kontrolleri çalıştıracak. Sonraki uygulama: SQLite modelini PDF/chapter/üretim ilişkilerine göre düzenle ve mevcut JSON bankasını eski ID'leri koruyarak aktar. Dosya taşınmasına dayanıklı PDF kimliği ve JSON/SQLite tutarlılığı tasarlanmalı. Sonrasında quiz cevaplarını bağla; mixed/final exam seçimi ve Leitner daha sonra.
- Quiz komutu (proje kökünden): `python -m study_tool.quiz data/QualityManagementWeek5_ch1_questions.json`
