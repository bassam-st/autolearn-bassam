import os, yaml, sys
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
from learner import Learner

def load_cfg(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.example.yaml"
    cfg = load_cfg(cfg_path)
    learner = Learner(cfg)

    goal = cfg.get("goal", "تعلم موضوع جديد")
    max_cycles = int(cfg.get("max_cycles", 3))
    queries_per_cycle = int(cfg.get("queries_per_cycle", 3))
    results_per_query = int(cfg.get("results_per_query", 5))

    notes = []
    print(f"== AutoLearn: {goal} ==")
    for c in range(1, max_cycles + 1):
        print(f"\n--- الدورة {c}/{max_cycles} ---")
        qs = learner.plan_queries(goal, notes)
        qs = qs[:queries_per_cycle]
        all_hits = []
        for q in qs:
            print(f"[بحث] {q}")
            hits = learner.searcher.search(q, max_results=results_per_query)
            all_hits.extend(hits)

        kept = learner.fetch_novel_docs(all_hits)
        print(f"[ذاكرة] مقاطع جديدة مُضافة: {len(kept)}")

        insight = learner.synthesize_insight(goal, kept)
        if insight:
            iid = learner.mem.store_insight(
                topic=insight.topic,
                summary=insight.summary,
                confidence=insight.confidence,
                sources=insight.sources,
                created_at=insight.created_at.isoformat(timespec="seconds"),
            )
            print(f"[معرفة] Insight#{iid} (ثقة {insight.confidence:.2f})")
            print(f"ملخص: {insight.summary[:300]} ...")
            print(f"مصادر: {', '.join(insight.sources)}")
            nxt = learner.reflect(goal, insight)
            if nxt:
                notes.append(nxt)

    print("\nانتهى. كل ما جُمِع مُخزَّن في SQLite ضمن autolearn.db (docs/chunks/insights).")

if __name__ == "__main__":
    main()
