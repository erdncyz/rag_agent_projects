from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from app.config import Settings
from app.prompts import SYSTEM_PROMPT, build_user_prompt
from app.schemas import SourceChunk
from app.services.chunker import TextChunker
from app.services.document_loader import DocumentLoader
from app.services.ollama_client import OllamaClient
from app.services.vector_store import VectorStore
from app.services.search_strategies import rerank_score, distance_to_similarity


class RagService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.loader = DocumentLoader()
        self.chunker = TextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        self.ollama = OllamaClient(settings)
        self.store = VectorStore(settings)
        self.logger = logging.getLogger("rag_service")

    def ingest_document(self, file_path: Path) -> dict[str, Any]:
        self.logger.info("Doküman ingest başladı: %s", file_path.name)

        pages = self.loader.load(file_path)
        source_name = file_path.stem.replace(" ", "_").lower()
        chunks = self.chunker.split_pages(pages, source_name=source_name)

        if not chunks:
            raise ValueError("Belgeden chunk üretilemedi.")

        self.logger.info(
            "Chunk üretildi | dosya=%s | chunk_sayisi=%s",
            file_path.name,
            len(chunks),
        )

        embeddings = self.ollama.embed([chunk.text for chunk in chunks])

        self.logger.info("Embedding üretildi | dosya=%s", file_path.name)

        self.store.add_chunks(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[chunk.metadata for chunk in chunks],
        )

        self.logger.info("Doküman ingest tamamlandı: %s", file_path.name)

        return {
            "message": "Doküman başarıyla yüklendi ve indekslendi.",
            "filename": file_path.name,
            "total_chunks": len(chunks),
            "pages": len(pages),
            "source_name": source_name,
        }

    def retrieve(
        self,
        question: str,
        top_k: Optional[int] = None,
        source_filter: Optional[str] = None
    ) -> list[SourceChunk]:
        # Eğer rerank açıksa, vektör tabanından daha fazla (x3) aday çekiyoruz
        fetch_k = (top_k or self.settings.top_k) * 3 if self.settings.rerank_enabled else (top_k or self.settings.top_k)
        
        self.logger.info(
            "Retrieve başladı | soru=%s | base_top_k=%s | filter=%s | rerank=%s",
            question, fetch_k, source_filter, self.settings.rerank_enabled
        )

        query_embedding = self.ollama.embed([question])[0]
        raw = self.store.query(
            query_embedding=query_embedding,
            top_k=fetch_k,
            source_filter=source_filter
        )

        ids = raw.get("ids", [[]])[0]
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        all_candidates: list[SourceChunk] = []
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            metadata = metadata or {}
            
            # Eşik Değer Kontrolü (Max Acceptable Distance)
            # Mesafe çok yüksekse (yani benzerlik çok azsa) o parçayı eliyoruz.
            if distance is not None and distance > self.settings.max_acceptable_distance:
                # Ancak kullanıcı min_context_results zorunluluğu koyduysa, boş dönmeyelim
                if len(all_candidates) >= self.settings.min_context_results:
                    continue

            # Rerank Skoru Hesaplama
            final_score = distance
            if self.settings.rerank_enabled:
                # rerank_score fonksiyonu mesafeyi benzerlik skoruna (0-1) çevirip lexical ile birleştirir.
                final_score = rerank_score(question, document, distance)

            all_candidates.append(
                SourceChunk(
                    chunk_id=chunk_id,
                    score=float(final_score) if final_score is not None else None,
                    page=metadata.get("page"),
                    text=document,
                    metadata=metadata,
                )
            )

        # Rerank Açıksa Yeniden Sıralama
        if self.settings.rerank_enabled:
            # Score ne kadar büyükse o kadar iyidir (benzerlik bazlı)
            all_candidates.sort(key=lambda x: x.score or 0.0, reverse=True)
        else:
            # Score mesafedir (distance), ne kadar küçükse o kadar iyidir
            all_candidates.sort(key=lambda x: x.score or 9.9)

        # İstediğimiz sayıya (top_k) kısıtlama
        final_results = all_candidates[:(top_k or self.settings.top_k)]

        # Tekil Kayıt Kontrolü (Duplikasyonları önle)
        final_results = self._deduplicate_sources(final_results)
        
        self.logger.info("Retrieve tamamlandı | sonuc_sayisi=%s", len(final_results))
        return final_results

    def _deduplicate_sources(self, results: list[SourceChunk]) -> list[SourceChunk]:
        unique: list[SourceChunk] = []
        seen_keys = set()

        for item in results:
            text_key = item.text[:250].strip().lower()
            source = item.metadata.get("source", "default")
            key = (source, item.page, text_key)

            if key in seen_keys:
                continue

            seen_keys.add(key)
            unique.append(item)

        return unique

    def _select_context_chunks(self, retrieved: list[SourceChunk]) -> list[SourceChunk]:
        return retrieved[:self.settings.max_context_chunks]

    def answer(
        self,
        question: str,
        top_k: Optional[int] = None,
        source_filter: Optional[str] = None
    ) -> dict[str, Any]:
        self.logger.info("Answer başladı | soru=%s | filter=%s", question, source_filter)
        retrieved = self.retrieve(question=question, top_k=top_k, source_filter=source_filter)

        # Eğer güçlü bir bağlam (strong context) şartı varsa ve sonuçlar çok uzaksa (veya azsa) reddet
        if self.settings.abstain_if_no_strong_context and not retrieved:
            return {
                "answer": (
                    "Kısa Cevap:\nÜzgünüm, sorunuzla ilgili belgelerde yeterli ve güçlü bir kanıt/baglam bulamadım.\n\n"
                    "Detaylı Açıklama:\n'Yetersiz Bağlam Şartı' aktif olduğu için uydurma cevap vermem engellenmiştir.\n\n"
                    "Kaynaklar:\nYok"
                ),
                "sources": [],
                "prompt_context_length": 0,
                "retrieved_pages": [],
                "source_count": 0,
                "retrieved_sources": [],
            }

        selected = self._select_context_chunks(retrieved)

        context_blocks = [
            {
                "page": item.page,
                "text": item.text,
                "score": item.score,
                "source": item.metadata.get("source", "-")
            }
            for item in selected
        ]

        user_prompt = build_user_prompt(question, context_blocks)
        answer = self.ollama.chat(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

        retrieved_pages = sorted({item.page for item in selected if item.page is not None})
        retrieved_sources = sorted({item.metadata.get("source") for item in selected if item.metadata.get("source")})

        self.logger.info("Answer tamamlandı | kaynak_sayisi=%s", len(selected))

        return {
            "answer": answer,
            "sources": selected,
            "prompt_context_length": len(user_prompt),
            "retrieved_pages": retrieved_pages,
            "source_count": len(selected),
            "retrieved_sources": retrieved_sources,
        }

    def list_documents(self) -> list[dict[str, Any]]:
        return self.store.list_documents()

    def delete_document(self, source_name: str) -> None:
        self.logger.warning("Belge siliniyor: %s", source_name)
        self.store.delete_by_source(source_name)

    def reset_all(self) -> None:
        self.store.reset_collection()