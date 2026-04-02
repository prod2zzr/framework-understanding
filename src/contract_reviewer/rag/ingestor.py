"""Ingest legal knowledge base into the vector store."""

import hashlib
import json
import logging
import re
from pathlib import Path

from contract_reviewer.rag.embedder import Embedder, EmbeddingError
from contract_reviewer.rag.vectorstore import VectorStore

logger = logging.getLogger(__name__)


MANIFEST_FILE = ".manifest.json"


class KnowledgeIngestor:
    """Load, chunk, embed, and store legal knowledge documents."""

    def __init__(self, embedder: Embedder, vectorstore: VectorStore):
        self.embedder = embedder
        self.vectorstore = vectorstore

    async def ingest_directory(self, directory: str, source_type: str = "civil_code") -> int:
        """Ingest all text files from a directory. Returns count of new chunks added."""
        dir_path = Path(directory)
        if not dir_path.exists():
            return 0

        manifest_path = dir_path / MANIFEST_FILE
        manifest = self._load_manifest(manifest_path)
        added = 0

        for file_path in sorted(dir_path.glob("**/*.txt")):
            file_hash = self._file_hash(file_path)
            rel_path = str(file_path.relative_to(dir_path))

            if manifest.get(rel_path) == file_hash:
                continue  # File unchanged, skip

            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    text = file_path.read_text(encoding="gb18030")
                except Exception:
                    logger.warning("Cannot decode %s, skipping", rel_path)
                    continue

            chunks = self._chunk_legal_text(text, source_type, file_path.stem)

            if chunks:
                ids = [c["id"] for c in chunks]
                texts = [c["text"] for c in chunks]
                metadatas = [c["metadata"] for c in chunks]

                try:
                    embeddings = await self.embedder.embed(texts)
                    self.vectorstore.add(
                        ids=ids,
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas,
                    )
                    added += len(chunks)
                except (EmbeddingError, Exception) as e:
                    logger.error("Failed to ingest %s: %s", rel_path, e)
                    continue  # Don't update manifest for failed files

            # Update manifest and save immediately after each successful file
            manifest[rel_path] = file_hash
            self._save_manifest(manifest_path, manifest)

        return added

    def _chunk_legal_text(
        self, text: str, source_type: str, document_name: str
    ) -> list[dict]:
        """Split legal text by articles/sections with metadata."""
        chunks = []

        # Try to split by article pattern (第X条)
        article_pattern = re.compile(
            r"(第[一二三四五六七八九十百千零\d]+条)\s*(.*?)(?=第[一二三四五六七八九十百千零\d]+条|$)",
            re.DOTALL,
        )
        matches = list(article_pattern.finditer(text))

        if matches:
            for match in matches:
                article_num = match.group(1)
                article_text = f"{article_num} {match.group(2).strip()}"
                if len(article_text.strip()) < 10:
                    continue

                chunk_id = hashlib.md5(
                    f"{document_name}:{article_num}".encode()
                ).hexdigest()
                chunks.append({
                    "id": chunk_id,
                    "text": article_text,
                    "metadata": {
                        "source_type": source_type,
                        "document_name": document_name,
                        "article_number": article_num,
                    },
                })
        else:
            # Fallback: split by paragraphs
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for i, para in enumerate(paragraphs):
                if len(para) < 10:
                    continue
                chunk_id = hashlib.md5(
                    f"{document_name}:p{i}".encode()
                ).hexdigest()
                chunks.append({
                    "id": chunk_id,
                    "text": para,
                    "metadata": {
                        "source_type": source_type,
                        "document_name": document_name,
                        "article_number": f"para_{i}",
                    },
                })

        return chunks

    @staticmethod
    def _file_hash(path: Path) -> str:
        return hashlib.md5(path.read_bytes()).hexdigest()

    @staticmethod
    def _load_manifest(path: Path) -> dict:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    @staticmethod
    def _save_manifest(path: Path, manifest: dict) -> None:
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
