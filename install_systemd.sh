#!/bin/bash
# ===========================================
# AutoLearn — Installer for systemd services
# سيكتشف المسار واسم المستخدم تلقائياً
# ثم ينشئ ويُفعّل خدمتين:
#  - autolearn.service (حلقة التعلّم)
#  - autolearn-dashboard.service (لوحة الويب)
# ===========================================

set -e

# 1) اكتشاف المسار واسم المستخدم
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="$(whoami)"
PYTHON_BIN="$(command -v python3 || true)"
UVICORN_BIN="$(command -v uvicorn || true)"

if [ -z "$PYTHON_BIN" ]; then
  echo "❌ Python3 غير موجود في PATH. ثبّت python3 أولاً."
  exit 1
fi

# 2) بيئة افتراضية (اختياري لكنها مفضلة)
if [ ! -d "$PROJECT_DIR/venv" ]; then
  echo "🧪 إنشاء بيئة افتراضية venv..."
  $PYTHON_BIN -m venv "$PROJECT_DIR/venv"
fi
source "$PROJECT_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"
pip install fastapi uvicorn >/dev/null
deactivate

# 3) التحقق من الملفات الأساسية
for f in autolearn.py stats_web.py config.yaml; do
  if [ ! -f "$PROJECT_DIR/$f" ]; then
    echo "❌ الملف $f غير موجود في $PROJECT_DIR"
    exit 1
  fi
done

# 4) كتابة ملفات systemd
SERVICE1="/etc/systemd/system/autolearn.service"
SERVICE2="/etc/systemd/system/autolearn-dashboard.service"

echo "📝 إنشاء $SERVICE1 و $SERVICE2 (يتطلب sudo)..."
sudo bash -c "cat > '$SERVICE1' <<EOF
[Unit]
Description=AutoLearn continuous learning loop
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
# يمكنك ضبط مفاتيح LLM هنا أو في /etc/environment:
# Environment=OPENAI_API_KEY=sk-xxxx
# Environment=GEMINI_API_KEY=AIza...
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/autolearn.py
ExecStop=/usr/bin/touch $PROJECT_DIR/STOP
ExecStopPost=/bin/sleep 5
Restart=always
RestartSec=5
User=$USER_NAME

[Install]
WantedBy=multi-user.target
EOF"

sudo bash -c "cat > '$SERVICE2' <<EOF
[Unit]
Description=AutoLearn stats web dashboard
After=autolearn.service
Requires=autolearn.service

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
Environment=STATS_PORT=8082
# غيّر مسار القاعدة إن لزم:
# Environment=AUTOLEARN_DB=$PROJECT_DIR/autolearn.db
ExecStart=$PROJECT_DIR/venv/bin/uvicorn stats_web:app --host 0.0.0.0 --port 8082
Restart=always
RestartSec=3
User=$USER_NAME

[Install]
WantedBy=multi-user.target
EOF"

# 5) إعادة تحميل systemd وتفعيل الخدمات
echo "🔁 إعادة تحميل systemd وتفعيل الخدمات للتشغيل التلقائي..."
sudo systemctl daemon-reload
sudo systemctl enable --now autolearn.service
sudo systemctl enable --now autolearn-dashboard.service

# 6) طباعة الحالة ونصائح الوصول
echo "✅ تم التثبيت والتشغيل!"
echo "📊 افتح لوحة الويب:  http://<IP-السيرفر>:8082"
echo "ℹ️ تحقق من الحالة:"
echo "   sudo systemctl status autolearn.service --no-pager"
echo "   sudo systemctl status autolearn-dashboard.service --no-pager"
echo "🧾 سجلات حية:"
echo "   journalctl -u autolearn.service -f"
echo "   journalctl -u autolearn-dashboard.service -f"
echo "🛑 إيقاف آمن للتعلّم:  sudo systemctl stop autolearn.service"
