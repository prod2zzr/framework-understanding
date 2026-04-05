#!/usr/bin/env python3
"""Precompute query embeddings for zero-model RAG retrieval.

Run this on a machine with the embedding model available.
Output is distributed to edge nodes alongside the ChromaDB vector store.

Usage:
    python scripts/precompute_queries.py --output data/precomputed_queries.json
"""

import argparse
import asyncio
import json

from contract_reviewer.models.config import Settings
from contract_reviewer.rag.embedder import Embedder
from contract_reviewer.rag.precomputed_queries import PrecomputedQueries


async def main(output_path: str) -> None:
    settings = Settings()
    embedder = Embedder(settings)
    pq = PrecomputedQueries()

    templates = pq.get_all_template_queries()
    print(f"Precomputing {len(templates)} query vectors...")

    texts = [t["query"] for t in templates]
    ids = [t["id"] for t in templates]

    embeddings = await embedder.embed(texts)

    vectors = dict(zip(ids, embeddings))
    PrecomputedQueries.save_vectors(vectors, output_path)

    print(f"Saved {len(vectors)} vectors to {output_path}")
    for t in templates:
        print(f"  [{t['dimension']}] {t['id']}: {t['query']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Precompute query embeddings")
    parser.add_argument("--output", "-o", default="data/precomputed_queries.json")
    args = parser.parse_args()
    asyncio.run(main(args.output))
