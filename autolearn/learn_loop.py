# learn_loop.py
import os, json, time, signal, traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from learner import Learner
import yaml

CHECKPOINT = Path("checkpoint.json")
STOP_FLAG = Path("STOP")        # أنشئ ملفًا باسم STOP لإيقاف آمن
LOGFILE = Path("autolearn.log")

def load_cfg(path: str = "config.example.yaml") -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def log(msg: str):
    line = f"[{datetime.utcnow().isoformat(timespec='seconds')}] {msg}"
    print(line)
    try:
        with LOGFILE.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
    except Exception:
        pass

def save_ckpt(state: Dict):
    with CHECKPOINT.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_ckpt() -> Dict:
    if CHECKPOINT.exists():
        try:
            return json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def should_stop() -> bool:
    return STOP_FLAG.exists()

def run_once(learner: Learner, goal: str, queries_per_cycle: int, results_per_query: int, notes):
    qs = learner.plan_queries(goal, notes)[:queries_per_cycle]
    all_hits = []
    for q in qs:
        log(f"[بحث] {q}")
        hits = learner.searcher.search(q, max_results=results_per_query)
        all_hits.extend(hits)

    kept = learner.fetch_novel_docs(all_hits)
    log(f"[ذاكرة] مقاطع جديدة: {len(kept)}")

    insight = learner.synthesize_insight(goal, kept)
    if insight:
        iid = learner.mem.store_insight(
            topic=insight.topic,
            summary=insight.summary,
            confidence=insight.confidence,
            sources=insight.sources,
            created_at=insight.created_at.isoformat(timespec="seconds"),
        )
        log(f"[معرفة] Insight#{iid} ثقة={insight.confidence:.2f}")
        log(f"[مصادر] {', '.join(insight.sources)}")
        nxt = learner.reflect(goal, insight)
        if nxt:
            notes.append(nxt)
    return notes

def run_loop(cfg_path: str = "config.example.yaml", forever: bool = True):
    cfg = load_cfg(cfg_path)
    learner = Learner(cfg)

    goal = cfg.get("goal", "تعلم موضوع جديد")
    queries_per_cycle = int(cfg.get("queries_per_cycle", 3))
    results_per_query = int(cfg.get("results_per_query", 5))
    max_cycles = int(cfg.get("max_cycles", 5))

    state = load_ckpt()
    notes = state.get("notes", [])
    cycle = state.get("cycle", 0)

    backoff = 5   # ثواني (تزايد أُسّي عند الأخطاء)

    log(f"== بدء حلقة التعلّم: {goal} ==")
    try:
        while True:
            if should_stop():
                log("تم العثور على ملف STOP — إيقاف آمن ✅")
                break

            if not forever and cycle >= max_cycles:
                log("وصلنا للحد الأقصى من الدورات — إنهاء ✅")
                break

            try:
                cycle += 1
                log(f"--- الدورة {cycle} ---")
                notes = run_once(learner, goal, queries_per_cycle, results_per_query, notes)

                # حفظ نقطة استعادة
                save_ckpt({"notes": notes, "cycle": cycle})
                backoff = 5  # إعادة تعيين بعد نجاح

                # اختياري: استراحة صغيرة للاحترام المواقع ولتفادي الحظر
                time.sleep(2)

            except Exception as e:
                log(f"[خطأ] {e}\n{traceback.format_exc()}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)  # حتى 5 دقائق

            # وضع التشغيل الدائم: يمكنك وضع Sleep أطول
            if forever:
                time.sleep(1)

    except KeyboardInterrupt:
        log("إيقاف يدوي (Ctrl+C) — تم الحفظ ✅")
        save_ckpt({"notes": notes, "cycle": cycle})

if __name__ == "__main__":
    # تشغيل مرة واحدة بعدد دورات max_cycles:
    # run_loop("config.example.yaml", forever=False)
    # تشغيل مستمر:
    run_loop("config.example.yaml", forever=True)
