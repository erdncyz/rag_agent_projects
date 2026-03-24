from __future__ import annotations

import logging
from typing import Any
import chromadb
from chromadb.api.models.Collection import Collection

from app.config import Settings


logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = chromadb.PersistentClient(path=str(settings.chroma_dir))

    def get_collection(self) -> Collection:
        return self.client.get_or_create_collection(name=self.settings.chroma_collection)

    def reset_collection(self) -> None:
        try:
            logger.info(f"{self.settings.chroma_collection} koleksiyonu sıfırlanıyor.")
            self.client.delete_collection(name=self.settings.chroma_collection)
        except Exception as exc:
            logger.debug(f"Koleksiyon silinemedi (önceden olmayabilir): {exc}")
        self.client.get_or_create_collection(name=self.settings.chroma_collection)

    def add_chunks(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        collection = self.get_collection()
        logger.info(f"{len(ids)} adet doküman ChromaDB'ye ekleniyor.")
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(self, query_embedding: list[float], top_k: int = 4) -> dict[str, Any]:
        collection = self.get_collection()
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

    def count(self) -> int:
        return self.get_collection().count()