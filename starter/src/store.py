"""Store and search vectors using PostgreSQL + pgvector."""
import json
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import psycopg
from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str | None = None, dimensions: int = 768) -> None:
        """Retain connection settings; validate model dimensions."""
        if not database_url:
            load_dotenv()
            load_dotenv(Path(__file__).resolve().parent.parent / ".env")
            database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL is not set.")
        self.database_url = database_url
        self.dimensions = dimensions

    def create_schema(self) -> None:
        """Create table with vector column and metadata fields."""
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS chunks (
                        chunk_id TEXT PRIMARY KEY,
                        strategy TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INT NOT NULL,
                        text TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}',
                        embedding vector({self.dimensions}) NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_chunks_strategy ON chunks(strategy);
                """)
                conn.commit()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate lengths/dimensions and write stable IDs without duplicates."""
        if len(chunks) != len(vectors):
            raise ValueError(f"Mismatch: {len(chunks)} chunks vs {len(vectors)} vectors.")

        if not chunks:
            return

        rows = []
        for chunk, vector in zip(chunks, vectors):
            if len(vector) != self.dimensions:
                raise ValueError(f"Vector dim {len(vector)} does not match store dim {self.dimensions}.")
            chunk_pk = f"{strategy}_{chunk.chunk_id}" if not chunk.chunk_id.startswith(f"{strategy}_") else chunk.chunk_id
            rows.append((
                chunk_pk,
                strategy,
                chunk.document_id,
                chunk.source,
                chunk.page,
                chunk.text,
                json.dumps(chunk.metadata),
                str(vector),
            ))

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.executemany("""
                    INSERT INTO chunks (chunk_id, strategy, document_id, source, page, text, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        strategy = EXCLUDED.strategy,
                        document_id = EXCLUDED.document_id,
                        source = EXCLUDED.source,
                        page = EXCLUDED.page,
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding;
                """, rows)
                conn.commit()

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Filter metadata in SQL, rank by cosine distance (<=>), return top-k."""
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Query vector dim {len(query_vector)} != store dim {self.dimensions}.")

        q_vec_str = str(query_vector)
        sql = """
            SELECT chunk_id, document_id, source, page, text, metadata,
                   1 - (embedding <=> %s::vector) AS score
            FROM chunks
            WHERE strategy = %s
        """
        params: list[Any] = [q_vec_str, strategy]

        if filters:
            for k, v in filters.items():
                sql += " AND metadata->>%s = %s"
                params.extend([k, str(v)])

        sql += " ORDER BY embedding <=> %s::vector LIMIT %s;"
        params.extend([q_vec_str, top_k])

        results = []
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                for row in cur.fetchall():
                    results.append({
                        "chunk_id": row[0],
                        "document_id": row[1],
                        "source": row[2],
                        "page": row[3],
                        "text": row[4],
                        "metadata": row[5] if isinstance(row[5], dict) else json.loads(row[5]),
                        "score": float(row[6]),
                    })
        return results

    def count(self, strategy: str) -> int:
        """Count existing chunks for a given strategy."""
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM chunks WHERE strategy = %s;", (strategy,))
                row = cur.fetchone()
                return int(row[0]) if row else 0
