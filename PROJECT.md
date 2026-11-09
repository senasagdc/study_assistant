# PROJECT.md (güncel durum: 10 Kasım 2026)

> Claude'a not: Bu dosya proje bağlamım. Önceki sohbetlerden hafızan yok. Aşağıdaki kurallara uy ve "Bir sonraki adım" bölümünden devam et.

## Ben kimim
- Bahçeşehir Üniversitesi, Yazılım Mühendisliği 4. sınıf + Endüstri Mühendisliği çift anadal.
- Python orta+, SQL biliyorum. Git'i sıfırdan öğreniyorum (şu an temel döngüyü yaptım).
- Hiç bitirilmiş tam bir proje çıkarmadım.
- Veri tarafıyla ilgileniyorum.
- Haftada 6-10 saat ayırabilirim.
- Bütçe yok: Gemini API ücretsiz katman, Google Colab, açık kaynak araçlar. Anthropic API anahtarım yok.
- Mac (Apple Silicon), Python 3.13.1, VS Code.

## Amaç
Yeni nesil yazılım mühendisliğine (LLM'ler, agent'lar, generative AI) alışmak ve birkaç konuda gerçekten bilgi sahibi olmak. Gerçek hayatta kendim kullanacağım, katmanlı ve sade araçlar istiyorum. Teknoloji gösterisi değil, işe yarayan araçlar.

## Projeler (sırayla, paralel değil)

### Proje 1: Kişisel Ders Çalışma Aracı
Mevcut yöntemim:
1. Ders PDF'ini AI'a verip anlattırırım (Türkçe, teknik terimler İngilizce, öz, maddeli, her konu için somut örnek).
2. Notion'a elle özet çıkarırım (1. tarama).
3. Her chapter için kaliteli sorular ürettiririm.
4. Yanlış yaptığım soruları tekrar tekrar çözerim.
5. Notion özetimi tekrar okurum (2. tarama).
6. Soru çözerim ve biter.

Notion özetini elle çıkarmak yöntemimin öğrenme kısmı, otomatikleştirilmeyecek. İstersek sonradan "özetimi slaytla karşılaştır" özelliği eklenir.

Katmanlar (her katman bitince kullanılabilir bir araç olmalı):
1. PDF'ten metin çıkarma, chapter'lara bölme, JSON'a kaydetme (PyMuPDF)
2. Chapter'dan study guide üretme (prompt şablonu dosyada, çıktı Markdown, Notion'a yapıştırılabilir)
3. Soru üretimi (JSON: soru tipi, şıklar, doğru cevap, açıklama, konu etiketi, kaynak sayfa), şema doğrulama, retry, terminalde quiz
4. SQLite ile cevap kaydı ve yanlış takibi, Leitner sistemiyle tekrar zamanlaması
5. Streamlit arayüzü ve konu bazlı zayıf nokta raporu
6. Bonus: embedding ile "bu kavram slaytta nerede geçiyor?" araması (RAG temeli)

### Proje 2: Fiş/Harcama Takibi (Proje 1 bittikten sonra)
Fiş fotoğrafı → vision modeliyle JSON → SQLite → kategori sınıflandırma → doğal dille soru sorma (text-to-SQL) → grafikler. Doğruluğu ölçmek için 30-50 fişlik elle etiketli test setim olacak. Fiş verisi hassas, repoya asla girmemeli.

### Ortak parçalar (core/ altında, baştan)
Tek bir LLM çağrı fonksiyonu (model kolayca değiştirilebilir), JSON şema doğrulama + retry, SQLite katmanı, Streamlit.

## Çalışma kuralları (Claude için)
- Birlikte çalışıyoruz: kodun çoğunu sen yaz, ben çalıştırıp çıktıyı getiririm.
- Her kod parçasından sonra kısaca "ne yapıyor, neden böyle, alternatifi neydi" açıkla.
- Yeni kavram (Git, venv, .env, şema doğrulama vb.) ilk geçtiğinde 2-3 cümleyle öğret.
- Bir seferde tek küçük adım ver, ben sonucu getirmeden sonrakine geçme.
- Önce kısa plan, sonra kod. Mimari karar varsa alternatifleri kısaca konuş.
- Git'i sadece gerektiği kadar öğret (init, add, commit, .gitignore, push). Her seans sonunda commit alışkanlığı kazandır.
- API anahtarı güvenliği baştan doğru: .env + .gitignore. Token/anahtarları sohbete asla yapıştırmayacağım.
- Büyük ya da gereksiz karmaşık şeyler önerme. Süre ve kapsam konusunda gerçekçi ol, bonus bonus kalsın.
- Her seferinde en fazla bir soru sor.
- Seans sonunda güncel PROJECT.md ver (hedef, klasör yapısı, kararlar, nerede kaldık, sonraki adım).
- Türkçe konuş, teknik terimler İngilizce kalsın.

## Ortam
- Yerel klasör: ~/projects/ai-tools
- GitHub repo: senasagdc/study_assistant (private), branch: main
- Venv: .venv (proje kökünde). Gün başı:
    cd ~/projects/ai-tools
    source .venv/bin/activate
- Kurulu: pymupdf 2.1 (+ bağımlılıkları), bkz. requirements.txt
- Terminal VS Code'un içinde; push şifre sormadan çalışıyor (token Keychain'de, doğrulandı).

## Klasör yapısı (şu an)
ai-tools/
├── .venv/          (Git'e girmez)
├── .gitignore      (.venv, .env, data/, __pycache__, *.pyc, .DS_Store, .ipynb_checkpoints)
├── requirements.txt
└── PROJECT.md

Hedef yapı (ihtiyaç doğdukça oluşturulacak): core/, study_tool/, receipts/, data/, .env

## Verilen kararlar
- PDF'ler slayt tabanlı, metin + madde + görsel karışık.
- Chapter bölme: önce bookmark'a (doc.get_toc()) bakılacak; yoksa chapter sayfa aralıkları elle bir config dosyasına yazılacak. Slaytlarda otomatik tahmin güvenilmez.
- venv seçildi (conda/uv yerine): Python ile gelir, yeterli.
- Gemini ücretsiz katman, tek değiştirilebilir LLM fonksiyonu core/ içinde.
- data/ tamamen Git dışında (ders PDF'leri, fiş verisi, üretilen JSON ve veritabanları).

## Öğrenilenler / notlar
- Git öğrenildi: init, add, commit, log, remote, push, .gitignore. Commit mesajı kısa ve "ne yaptım" şeklinde (örn. "Add .gitignore").
- Dosyayı sohbette görmek onu oluşturmaz: dosyalar önce diske yazılmalı (VS Code'da kaydet ya da terminalde cat > dosya << 'EOF'), sonra git add.
- VS Code terminali push'ta kimlik sorununa yol açmıştı (GIT_ASKPASS). Personal Access Token (classic, scope: repo, 90 gün) oluşturuldu, Keychain'e kaydedildi. Süresi yaklaşık Şubat 2027'de dolar; dolunca yeni token gerekir (github.com/settings/tokens).
- VS Code'da "Python: Select Interpreter" ile .venv henüz seçilmedi; terminalde elle aktive ediyorum. VS Code ayarlarım eskiden bozulmuştu, gerekirse yeni Profile açılabilir.
- Repo adı (study_assistant) klasör adından (ai-tools) farklı; Proje 2 aynı repoya girecekse GitHub'da ai-tools olarak yeniden adlandırmayı düşünebiliriz.
- .env henüz yok; Gemini API anahtarı Katman 2'de gerekecek.

## Nerede kaldık
Kurulum bitti: venv, Git, GitHub push, PyMuPDF, requirements.txt, PROJECT.md. Katman 1 kodu henüz yazılmadı.

## Bir sonraki adım
1. Terminali aç, cd ~/projects/ai-tools ve source .venv/bin/activate.
2. data/ klasörünü oluştur, test PDF'ini oraya koy (Git'e girmez).
3. Claude'a söyle: test PDF'inin adı ve sayfa sayısı.
4. PDF'te bookmark var mı kontrol et (doc.get_toc()).
5. İlk script: sayfa sayfa metin çıkar, JSON'a kaydet (Katman 1).
6. Seans sonu: commit + push, güncel PROJECT.md.
