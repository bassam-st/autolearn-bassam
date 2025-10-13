# ===========================
# 📊 AutoLearn Stats Viewer
# يعرض عدد المستندات والمقاطع والمعارف وحجم قاعدة البيانات
# ===========================

import sqlite3, os

DB_PATH = "autolearn.db"   # غيّره إذا كان اسم القاعدة مختلف في config.yaml

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ لا يوجد ملف قاعدة بيانات: {DB_PATH}")
        print("شغّل autolearn.py أولاً ليتم إنشاؤها.")
        return

    # حجم الملف
    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)

    # فتح القاعدة وقراءة الجداول
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    stats = {}
    for t in ["docs", "chunks", "insights"]:
        try:
            count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            stats[t] = count
        except Exception:
            stats[t] = "❌ (الجدول غير موجود بعد)"
    con.close()

    # عرض النتائج
    print("========== 📘 AutoLearn Database Stats ==========")
    print(f"📦 حجم قاعدة البيانات: {size_mb:.2f} MB\n")
    print(f"📄 المستندات (docs): {stats['docs']}")
    print(f"🧩 المقاطع (chunks): {stats['chunks']}")
    print(f"💡 المعارف (insights): {stats['insights']}")
    print("===============================================")

if __name__ == "__main__":
    main()
