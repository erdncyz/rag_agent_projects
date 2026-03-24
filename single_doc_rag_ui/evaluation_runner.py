from __future__ import annotations
import json
import os
import sys
from pathlib import Path

# Proje kök dizinini Python path'ine ekleyelim
sys.path.append(os.getcwd())

from app.config import get_settings
from app.services.rag_service import RagService

settings = get_settings()
service = RagService(settings)

dataset_path = Path("evaluation_dataset.json")

if not dataset_path.exists():
    print(f"HATA: {dataset_path} dosyası bulunamadı. Lütfen önce test setinizi oluşturun.")
    sys.exit(1)

dataset = json.loads(dataset_path.read_text(encoding="utf-8"))

passed = 0
total = len(dataset)

print(f"--- Evaluation Başlatılıyor ({total} Test Senaryosu) ---")

for idx, item in enumerate(dataset, start=1):
    question = item["question"]
    source_filter = item.get("source_filter")
    expected_source = item.get("expected_source")
    must_contain = item.get("must_contain", [])

    try:
        result = service.answer(
            question=question,
            top_k=6,
            source_filter=source_filter,
        )

        answer_text = result["answer"].lower()
        retrieved_sources = result["retrieved_sources"]

        # Kaynak doğruluğu kontrolü
        source_ok = True
        if expected_source:
             source_ok = any(expected_source.lower() in s.lower() for s in retrieved_sources)
        
        # İçerik doğruluğu kontrolü
        content_ok = all(term.lower() in answer_text for term in must_contain)

        success = source_ok and content_ok
        if success:
            passed += 1

        print(f"\n--- Test {idx} ---")
        print("Soru:", question)
        print("Beklenen kaynak (yaklaşık):", expected_source)
        print("Bulunan kaynaklar:", retrieved_sources)
        print("İçerik kontrolü:", "BAŞARILI" if content_ok else "BAŞARISIZ")
        print("Kaynak kontrolü:", "BAŞARILI" if source_ok else "BAŞARISIZ")
        print("Sonuç:", "PASS" if success else "FAIL")
    except Exception as e:
        print(f"\n--- Test {idx} HATA ---")
        print("Soru:", question)
        print("Hata:", str(e))
        print("Sonuç: FAIL")

print(f"\n==============================")
print(f"Genel Sonuç: {passed}/{total} test geçti.")
print(f"Başarı Oranı: %{ (passed/total)*100 if total > 0 else 0:.2f}")
print(f"==============================\n")
