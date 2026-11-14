"""Pipeline entry point for Day 06 Data Ingestion."""
import json
import sys
from pathlib import Path

sys.path.append(".")

from starter.src.chunking import by_paragraph, fixed_size
from starter.src.embeddings import MyEmbedder
from starter.src.evaluation import evaluate_query, summarize
from starter.src.ingestion import load_html
from starter.src.store import PgVectorStore

def main() -> None:
    # 1. Ingestion & Chunking
    pages = load_html(Path("data/the_great_gatsby.html"), "the-great-gatsby", "data/the_great_gatsby.html")
    chunks_a = [c for p in pages for c in fixed_size(p, 500, 50)]
    chunks_b = [c for p in pages for c in by_paragraph(p, 800)]

    # 2. Database & Embeddings (skip if already ingested)
    store = PgVectorStore()
    store.create_schema()
    embedder = MyEmbedder()

    for strat, chunks in [("A", chunks_a), ("B", chunks_b)]:
        start_idx = store.count(strat)
        if start_idx < len(chunks):
            print(f"Ingesting Strategy {strat} ({start_idx}/{len(chunks)} already in DB)...")
            for i in range(start_idx, len(chunks), 50):
                batch = chunks[i : i + 50]
                vecs = embedder.embed_documents([c.text for c in batch])
                store.upsert(strat, batch, vecs)

    # 3. Benchmark 20 questions
    with open("benchmark/questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)

    print("Embedding benchmark questions...")
    q_vecs = {q["id"]: embedder.embed_query(q["question"]) for q in questions}

    print("Evaluating strategies A, B, C...")
    traces = []
    for strat in ["A", "B", "C"]:
        db_strat = "B" if strat == "C" else strat
        for q in questions:
            filters = q.get("filter") if strat == "C" else None
            hits = store.search(db_strat, q_vecs[q["id"]], top_k=3, filters=filters)
            traces.append(evaluate_query({**q, "strategy": strat}, hits))

    # 4. Save results & experiment log
    summary = summarize(traces)
    Path("results").mkdir(exist_ok=True)
    with open("results/traces.json", "w", encoding="utf-8") as f:
        json.dump(traces, f, indent=2, ensure_ascii=False)
    with open("results/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # artifacts/experiment_log.csv
    configs = [
        ("A", "fixed_size", 500, 50, "none"),
        ("B", "by_paragraph", 800, 0, "none"),
        ("C", "by_paragraph", 800, 0, "chapter_filter"),
    ]
    rows = [
        "strategy,chunking,chunk_size,overlap,metadata,filter,vectorizer,hypothesis,dev_hit1,dev_hit3,test_hit1,test_hit3,notes\n"
    ]
    for s, c_type, sz, ov, flt in configs:
        dev = summary[s]["dev"]
        test = summary[s]["test"]
        row = (
            f"{s},{c_type},{sz},{ov},chapter,{flt},gemini-embedding-001,,"
            f"{dev['hit@1_ratio']},{dev['hit@3_ratio']},"
            f"{test['hit@1_ratio']},{test['hit@3_ratio']},\n"
        )
        rows.append(row)

    Path("artifacts/experiment_log.csv").write_text("".join(rows), encoding="utf-8")

    print("\nBenchmark Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
