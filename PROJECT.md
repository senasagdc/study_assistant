# PROJECT.md (güncel durum: 11 Kasım 2026)

> AI asistana not: Bu dosya araçtan bağımsız proje bağlamıdır. Aşağıdaki kurallara uy ve “Bir sonraki adım” bölümünden devam et. Şu anda ChatGPT Codex kullanılıyor; araç değişebilir.

## Kullanıcı ve amaç
- Sena: BAU Yazılım Mühendisliği 4. sınıf + Endüstri Mühendisliği çift anadal.
- Python orta+, SQL biliyor; Git temel döngüsünü yeni öğreniyor. Henüz tamamlanmış bir proje yok.
- Veri, AI, LLM ve agent geliştirmeyi gerçek bir araç yaparak öğrenmek istiyor.
- Haftada 6–8 saat; bütçe yok. Gemini API ücretsiz katman, Gemini öğrenci paketi, Colab ve açık kaynak araçlar kullanılabilir. Öğrenci paketi API kotası sağlıyor varsayılmayacak.
- Mac Apple Silicon, Python 3.13.1, VS Code.

## Tek proje: Kişisel Soru ve Tekrar Aracı
İngilizce Endüstri Mühendisliği ders PDF'lerinden kaynakla ilişkili kaliteli sorular üretmek, quiz çözmek ve zamanla yanlışları takip edip tekrar planlamak.

Özet ve konu anlatımını kullanıcı mevcut LLM sohbetleriyle yapacak. Notion özetini elle çıkarmak öğrenme sürecinin parçası. Study guide / otomatik özet üretimi proje kapsamından çıkarıldı. Fiş/harcama projesi iptal; başka proje yok.

### Kullanım akışı
1. Kullanıcı dersi LLM ile çalışır ve Notion özetini elle çıkarır.
2. Araç PDF metninden chapter bazında sorular üretir ve kaydeder.
3. Kullanıcı quiz çözer; cevaptan sonra doğru cevap, açıklama ve kaynak sayfayı görür.
4. Sonraki katmanlarda yanlışlar kalıcı tutulur, tekrar zamanı ve zayıf konular gösterilir.

### Kapsam ve ilk sürüm
- Yalnızca metin ve tablo ağırlıklı İngilizce Endüstri Mühendisliği slaytları. Görsel ağırlıklı PDF'ler kapsam dışı.
- İlk soru türü: İngilizce, dört şıklı, tek doğru cevaplı MCQ. Diğer türler ihtiyaç doğarsa eklenir.
- İlk deneme: bir chapter için 5 soru. Kullanıcı kaynak uygunluğu, açıklık, zorluk ve distractor kalitesini kontrol eder.
- Soru, şıklar ve doğru cevap İngilizce; açıklama Türkçe, teknik terimler İngilizce.
- Her soru: id, type, question, options, correct_answer, explanation, topic, source_pages.
- Sorular verilen metne dayanmalı; kaynakta bulunmayan bilgi gerektirmemeli. Kaynak sayfalar orijinal PDF'in 1 tabanlı sayfa numaraları olmalı.
- JSON schema doğrulaması biçim ve alanları kontrol eder; sorunun doğruluğunu veya kalitesini garanti etmez. İlk örnekler kullanıcı tarafından PDF ile karşılaştırılır.
- Soru geçmişine göre tekrar önleme, kalıcı kayıt eklendiğinde ele alınacak; ilk sürümde farklı çalıştırmalar arasında benzersizlik garantisi yok.

## Katmanlar
1. PDF → sayfa metinleri → chapter → JSON (PyMuPDF). İlk çıktı alındı, kullanıcı ön kontrolü tamamladı.
2. Gemini ile soru JSON üretimi: prompt dosyası, ortak LLM fonksiyonu, schema doğrulama, sınırlı retry ve dosyaya kayıt.
3. Terminal quiz: cevapları sırayla al, cevaptan sonra açıklamayı göster, sonuç ver. Burada “gerçekten faydalı mı?” değerlendirmesi yapılır.
4. SQLite ile soru/cevap geçmişi, yanlış takibi ve Leitner tekrar zamanlaması.
5. Streamlit arayüzü, zamanı gelen tekrarlar ve konu bazlı zayıf nokta raporu.
6. Bonus: embedding ile kavramın slaytta geçtiği yeri arama. Şimdilik yapılmayacak.

## Çalışma kuralları
- Kodun çoğunu asistan yazar; kullanıcı çalıştırıp sonucu getirir. Dosya yazabilen araç da ne yaptığını açıklamalı; kullanıcı anlamadan büyük değişiklik yapılmamalı.
- Önce kısa plan, sonra kod. Her kod parçasından sonra ne yaptığı, neden bu yaklaşımın seçildiği ve alternatif kısaca açıklanır.
- Bir seferde tek küçük adım; kullanıcı sonucu getirmeden sonraki uygulama adımına geçilmez.
- Yeni kavram ilk geçtiğinde 2–3 cümleyle öğretilir. Türkçe konuşulur; teknik terimler İngilizce kalır.
- Her yanıtta en fazla bir soru. Gereksiz mimari, teknoloji ve bonus özellik eklenmez.
- Git gerektiği kadar öğretilir; seans sonunda commit alışkanlığı kazandırılır.
- Anahtarlar .env içinde, .env ve data/ Git dışında. Anahtarlar sohbete yapıştırılmaz. Asistan .env ve data/ içeriğini okumaz veya göndermez.
- Uygulamanın kullanıcı tarafından çalıştırılan soru üretme komutu seçilen chapter metnini Gemini API'ye gönderecek. Bu davranış ilk çalıştırmadan önce kullanıcıya açıklanır; anahtar gönderilen prompt'a eklenmez.
- Seans sonunda PROJECT.md hedef, yapı, kararlar, mevcut durum ve sonraki adımla güncellenir.

## Ortam
- Yerel proje: ~/projects/ai-tools
- GitHub: senasagdc/study_assistant (private), branch main.
- Gün başı:
```bash
cd ~/projects/ai-tools
source .venv/bin/activate
```
- PyMuPDF kurulu; gerçek sürüm için requirements.txt esas alınır.
- VS Code terminali kullanılıyor. Push kimliği Keychain'de.
- VS Code interpreter olarak .venv henüz seçilmedi; terminalde elle aktive ediliyor.
- .env henüz oluşturulmadı; API entegrasyonu sırasında oluşturulacak.

## Mevcut klasör yapısı
```text
ai-tools/
├── .venv/                  # Git dışında
├── .gitignore
├── requirements.txt
├── PROJECT.md
├── check_toc.py             # geçici; varsa temizlenecek
├── study_tool/
│   └── extract.py
└── data/                   # Git dışında
    ├── QualityManagementWeek5.pdf
    └── QualityManagementWeek5.json
```
İhtiyaç doğdukça core/llm.py, soru üretme prompt'u, soru schema'sı ve terminal quiz modülü eklenecek. SQLite ve Streamlit sonraki katmanlarda.

## Verilen kararlar
- PDF bookmark'ları yok; otomatik konu sınırı tahmini yapılmıyor.
- MAX_SINGLE = 55: en fazla 55 sayfa tek chapter; daha uzun PDF iki chapter.
- Varsayılan bölme n // 2; CLI ikinci argümanıyla bölme sayfası verilebiliyor. Mevcut argümanın tam davranışı kod üzerinden doğrulanmalı.
- Konu etiketini soru üretiminde LLM verir; chapter yalnızca metni yönetilebilir parçalara ayırır.
- Tek değiştirilebilir LLM çağrı fonksiyonu core/ altında, ilk sağlayıcı Gemini.
- Ücretsiz kota/model sınırları entegrasyon sırasında güncel resmi dokümandan kontrol edilir. Rate limit için sınırlı retry/bekleme; geçersiz JSON için sınırlı düzeltme retry'ı ayrı ele alınır.
- venv yeterli; conda/uv geçişi yok. data/ tamamen Git dışında.
- page.find_tables() henüz eklenmedi. Kullanıcı tablo metnini anlaşılır buldu; somut bozulma görülürse eklenecek.

## Nerede kaldık
- venv, Git, GitHub push, PyMuPDF ve requirements.txt hazır.
- extract.py çalıştı; 59 sayfalık QualityManagementWeek5 PDF'inden JSON oluştu.
- Önceki notta chapter aralıkları 1–28 ve 29–59 olarak kaydedilmiş. Kod ve çıktı üzerinden bu sınırlar henüz asistan tarafından doğrulanmadı; data/ okunmayacak.
- Kullanıcı: tüm sayfalar mevcut, boş text yok, tablo metni anlaşılır görünüyor. Bu bir ön kontrol; bütün tabloların kusursuz çıkarıldığı iddia edilmiyor.
- Chapter sınırının konuya uygunluğu henüz teyit edilmedi; kullanıcı isterse değiştirebilir.
- extract.py önceki duruma göre henüz commit edilmedi; güncel Git durumu ayrıca kontrol edilmeli.
- Terminalde ilk iki çalıştırmada print görünmemiş, üçüncüde görünmüş. Tekrarlarsa önce dosyayı kaydet; çıktıyı yerelde dosyaya yönlendir veya Mac Terminal'de dene. Bu çıktı dosyası asistana otomatik okutulmayacak.
- Git token süresi önceki nota göre yaklaşık Şubat 2027; token değeri okunmaz/paylaşılmaz.

## Bir sonraki adım
1. Bu güncel PROJECT.md dosyasını proje kökündeki eski dosyanın yerine koy.
2. Kullanıcı git status --short çıktısını getirir. Yalnızca Git durumuna bakılır; .env/data içerikleri okunmaz.
3. Duruma göre geçici check_toc.py ve varsa cikti.txt temizlenir; extract.py ve PROJECT.md commit + push yapılır. Commit mesajı: Add PDF text extraction and update quiz plan.
4. Sonraki küçük adım: mevcut extract.py kodu okunarak JSON yapısı anlaşılır; data/ açılmaz. Ardından ilk MCQ schema'sı ve prompt hazırlanır.
5. Gemini API kurulumu: güncel resmi SDK/model/kota doğrulanır; kullanıcı anahtarı yerelde .env'ye ekler; .gitignore güvenliği kontrol edilir. API anahtarı sohbete gelmez.
6. Önce ortak LLM fonksiyonu, ardından tek chapter için 5 soruluk üretim denenir. Kullanıcı soruları PDF ile karşılaştırır; sonra terminal quiz'e geçilir.
