# ==============================
# 📊 AutoLearn Stats Viewer
# يعرض عدد المستندات والمقاطع والمعارف وحجم قاعدة البيانات
# يعمل تلقائيًا مع Render أو محليًا
# ==============================

import sqlite3, os

# تحديد مسار قاعدة البيانات من المتغير البيئي أو الافتراضي
DB_PATH = os.getenv("AUTOLEARN_DB", "/data/autolearn.db")

def main():
    print("📡 فحص حالة قاعدة بيانات AutoLearn...\n")

    # تحقق من وجود قاعدة البيانات
    if not os.path.exists(DB_PATH):
        print(f"❌ لا يوجد ملف قاعدة بيانات في المسار: {DB_PATH}")
        print("💡 ربما لم يتم تشغيل النظام بعد أو لم تُنشأ القاعدة.")
        return

    # حجم الملف بالميغابايت
    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)

    # الاتصال بقاعدة البيانات
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
    except Exception as e:
        print(f"⚠️ خطأ في فتح قاعدة البيانات: {e}")
        return

    stats = {}
    tables = ["docs", "chunks", "insights"]

    for t in tables:
        try:
            count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            stats[t] = count
        except Exception:
            stats[t] = "❌ (الجدول غير موجود بعد)"

    con.close()

    # عرض النتائج
    print("========== 📘 إحصاءات قاعدة بيانات AutoLearn ==========")
    print(f"📦 حجم قاعدة البيانات: {size_mb:.2f} MB")
    print(f"📄 عدد المستندات (docs): {stats['docs']}")
    print(f"🍀 عدد المقاطع (chunks): {stats['chunks']}")
    print(f"💡 عدد المعارف (insights): {stats['insights']}")
    print("========================================================")

if __name__ == "__main__":
    main()
