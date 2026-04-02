"""Clause-aware recursive text splitter for contracts."""

import tiktoken

from contract_reviewer.models.contract import Contract, ContractChunk


class ContractSplitter:
    """Split contract sections into chunks respecting clause boundaries."""

    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._enc = tiktoken.get_encoding("cl100k_base")

    def split(self, contract: Contract) -> list[ContractChunk]:
        """Split a parsed contract into chunks."""
        chunks: list[ContractChunk] = []

        for section in contract.sections:
            full_text = f"{section.heading}\n{section.body}".strip()
            token_count = self._count_tokens(full_text)

            if token_count <= self.chunk_size:
                # Section fits in one chunk
                chunks.append(
                    ContractChunk(
                        text=full_text,
                        chunk_index=0,
                        total_chunks=1,
                        section_heading=section.heading,
                        metadata={"section_type": section.section_type},
                    )
                )
            else:
                # Need to split this section
                sub_chunks = self._recursive_split(full_text)
                for i, text in enumerate(sub_chunks):
                    chunks.append(
                        ContractChunk(
                            text=text,
                            chunk_index=i,
                            total_chunks=len(sub_chunks),
                            section_heading=section.heading,
                            metadata={"section_type": section.section_type},
                        )
                    )

        # Assign global chunk indices
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        contract.chunks = chunks
        return chunks

    def _recursive_split(self, text: str) -> list[str]:
        """Recursively split text by paragraph, then sentence boundaries."""
        # Try splitting by double newline (paragraphs)
        parts = text.split("\n\n")
        if len(parts) > 1:
            return self._merge_parts(parts)

        # Try splitting by single newline
        parts = text.split("\n")
        if len(parts) > 1:
            return self._merge_parts(parts)

        # Try splitting by Chinese/English sentence endings
        import re

        sentences = re.split(r"(?<=[。；;.!?！？])\s*", text)
        if len(sentences) > 1:
            return self._merge_parts(sentences)

        # Last resort: split by tokens
        return self._split_by_tokens(text)

    def _merge_parts(self, parts: list[str]) -> list[str]:
        """Merge small parts into chunks respecting size limits, with overlap."""
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for part in parts:
            part = part.strip()
            if not part:
                continue
            part_tokens = self._count_tokens(part)

            if current_tokens + part_tokens > self.chunk_size and current:
                chunks.append("\n".join(current))
                # Keep overlap from the end of current chunk
                overlap_parts: list[str] = []
                overlap_tokens = 0
                for p in reversed(current):
                    p_tokens = self._count_tokens(p)
                    if overlap_tokens + p_tokens > self.overlap:
                        break
                    overlap_parts.insert(0, p)
                    overlap_tokens += p_tokens
                current = overlap_parts
                current_tokens = overlap_tokens

            current.append(part)
            current_tokens += part_tokens

        if current:
            chunks.append("\n".join(current))

        return chunks

    def _split_by_tokens(self, text: str) -> list[str]:
        """Split text into chunks by token count (last resort)."""
        tokens = self._enc.encode(text)
        chunks: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(self._enc.decode(chunk_tokens))
            start = end - self.overlap  # Overlap
        return chunks

    def _count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))
