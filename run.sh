#!/usr/bin/env bash
set -euo pipefail

# ====== إعدادات افتراضية آمنة ======
export AUTOLEARN_DB="${AUTOLEARN_DB:-/data/autolearn.db}"
export NEWS_INTERVAL_SEC="${NEWS_INTERVAL_SEC:-600}"   # كل 10 دقائق
export PYTHONUNBUFFERED=1

echo "📁 تهيئة مجلد البيانات..."
mkdir -p /data /data/inbox

# أنشئ القاعدة إن لم تكن موجودة (سيُنشئ الجداول عند أول تشغيل)
if [ ! -f "$AUTOLEARN_DB" ]; then
  echo "🆕 إنشاء قاعدة بيانات: $AUTOLEARN_DB"
  python - <<'PY'
import sqlite3, os
db=os.environ["AUTOLEARN_DB"]
con=sqlite3.connect(db); con.close()
print("✅ DB created:", db)
PY
fi

echo "🤖 بدء عامل التعلم الذاتي بالخلفية (كل $NEWS_INTERVAL_SEC ثانية)..."
(
  while true; do
    echo "⏳ [worker] تشغيل news_worker.py --once ..."
    python news_worker.py --once || echo "⚠️ worker: حدث خطأ وسيُعاد المحاولة"
    sleep "$NEWS_INTERVAL_SEC"
  done
) &

# (اختياري) عامل إضافي لمصادر أخرى إن أردت
# (
#   while true; do
#     python autolearn.py --once || true
#     sleep "$NEWS_INTERVAL_SEC"
#   done
# ) &

echo "🌐 تشغيل لوحة المتابعة على المنفذ $PORT ..."
exec uvicorn stats_web:app --host 0.0.0.0 --port "${PORT}"
