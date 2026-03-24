# Single Document RAG UI

Bu proje, tek bir doküman (PDF vb.) üzerinden sorgulama yapmanızı sağlayan Retrieval Augmented Generation (RAG) mimarisini temel alan bir web uygulamasıdır. Arka planda **FastAPI**, **ChromaDB** ve yerel olarak çalışan dil modelleri için **Ollama** kullanılmaktadır.

## Kurulum ve Başlangıç

### 1. Sanal Ortam (Virtual Environment) Oluşturma ve Aktifleştirme
Projeyi çalıştırırken bağımlılıkların sistemdeki diğer paketlerle çakışmaması için bir sanal ortam (`.venv`) kullanmanız önerilir.

```bash
# İlk defa kuracaksanız sanal ortam oluşturun:
python3 -m venv .venv

# Sanal ortamı aktifleştirin (Mac/Linux için):
source .venv/bin/activate

# (Windows kullanıyorsanız aktifleştirme komutu):
# .venv\Scripts\activate
```
*(Başarılı bir aktivasyon sonucunda terminal komut satırının başında `(.venv)` ifadesi belirecektir.)*

### 2. Gerekli Paketlerin Yüklenmesi
Sanal ortamınız aktifken uygulamanın çalışması için gereken paketleri kurun:

```bash
pip install -r requirements.txt
```

### 3. Uygulamayı Başlatma
Uygulamayı başlatmak için sanal ortamınızın aktif olduğuna emin olup `uvicorn` komutunu çalıştırın:

```bash
uvicorn app.main:app --reload
```
Uygulama arka planda dinlemeye başlayacaktır. Tarayıcınızdan `http://127.0.0.1:8000` adresine giderek arayüzü görebilir veya `http://127.0.0.1:8000/docs` üzerinden Swagger arayüzü ile API'yi test edebilirsiniz.

---

## 🏗 Sistem Nasıl Çalışıyor? (RAG Mimarisi)

Bu proje, bir doküman üzerinden **Retrieval-Augmented Generation (RAG)** yöntemini uygulayarak sorularınıza doğru ve bağlama dayalı cevaplar vermeyi amaçlar. Arka plandaki çalışma adımları temel olarak şu şekildedir:

1. **Doküman Yükleme ve Parçalama (Loader & Chunker):** Kullanıcı arayüz veya API üzerinden bir doküman (ör. PDF) yüklediğinde sistem içindeki metni ayıklar. Ardından anlam bütünlüğünün ve bağlamın kaybolmaması için belirli bir karakter büyüklüğünde (chunk size: 1100) ve birbiriyle bir miktar örtüşecek şekilde (chunk overlap: 180) küçük metin parçalarına ayırır.
2. **Vektörleştirme (Embedding):** Elde edilen bu metin parçaları, yerel makinenizde Ollama üzerinde çalışan gömme (embedding) modeli (varsayılan yapılandırma: `embeddinggemma`) kullanılarak çok boyutlu sayısal vektörlere dönüştürülür.
3. **Veri Tabanına Kaydetme (Vector Store - ChromaDB):** Üretilen bu vektörler; metnin aslı, sayfa numarası ve doküman bilgisi (metadata) ile birlikte yerel **ChromaDB** vektör veri tabanına kaydedilir (veri `./data/chroma` dizininde saklanır).
4. **Soru Sorma ve Benzerlik Araması (Retrieval):** Kullanıcı bir soru sorduğunda, sistem önce sorunun kendisini aynı embedding modeli ile vektöre dönüştürür. Daha sonra ChromaDB üzerinde soruya matematiksel olarak en benzer olan (en alakalı) "Top K" adet metin parçasını bulup getirir.
5. **Cevap Üretme (Generation - Ollama LLM):** Veri tabanından getirilen en alakalı metin parçaları (bağlam/context) ve kullanıcının sorusu özel bir prompt şablonunda birleştirilerek Ollama üzerinde çalışan yerel büyük dil modeline (varsayılan: `gemma3:4b`) iletilir. Model, soruyu **sadece** bu sağlanan bağlamı kullanarak yanıtlar; böylece yanlış bilgi üretimi (halüsinasyon) minimize edilmiş olunur.

---

## 🛠 Sık Karşılaşılan Hatalar ve Çözümleri

### 1. `zsh: command not found: uvicorn` Hatası
Eğer uvicorn komutunu çalıştırdığınızda komut bulunamadı hatası alıyorsanız, sistem bilgisayarınızdaki yüklü paketlere bakıyordur, proje klasörüne değil. Bazen sanal ortamın aktifleşmeyi unutulması kaynaklı olabilir.
**Çözüm:** Terminalde klasör dizininde olduğunuza emin olun ve `source .venv/bin/activate` ile sanal ortamınızı tekrar aktifleştirin.

### 2. Ollama "Address already in use" (Port 11434) Hatası
Eğer uygulamanız arka planda dil modeli için Ollama'yı çalıştırmak isterken şu hatayı veriyorsa: `listen tcp 127.0.0.1:11434: bind: address already in use`, bu durum arka planda (muhtemelen Mac menü çubuğunda) başka bir Ollama işleminin hali hazırda 11434 portunu meşgul ettiğini gösterir.

**Çözüm Yolu:**
1. Hangi sürecin bu portu kullandığını bulmak için:
   ```bash
   lsof -i :11434
   ```
2. Çıkan tablodaki `PID` (örneğin 1015) numarasını alarak süreci zorla durdurun:
   ```bash
   kill -9 <PID_NUMARASI>
   # Örnek: kill -9 1015
   ```
3. Alternatif olarak, Mac'te sağ üst menü çubuğunda Ollama simgesi (lama kafası) bulunuyorsa sağ tıklayıp "Quit Ollama" diyebilirsiniz.
4. Ardından kendi uygulamanızı veya `ollama serve` komutunu baştan çalıştırabilirsiniz.
