#!/usr/bin/env bash
set -euo pipefail

# ============ إعدادات عامة وافتراضية ============
APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$APP_ROOT/logs"
DATA_DIR="${DATA_DIR:-$APP_ROOT/data}"   # افتراضيًا ./data محليًا
PORT_WEB="${PORT:-8000}"                 # منفذ لوحة الويب stats_web
PORT_CORE="${PORT_CORE:-10000}"          # منفذ واجهة الـ Core API

mkdir -p "$LOG_DIR" "$DATA_DIR"

# متغيرات البيئة (افتراضيات آمنة محلياً)
export AUTOLEARN_DB="${AUTOLEARN_DB:-$DATA_DIR/autolearn.db}"
export HF_HOME="${HF_HOME:-$DATA_DIR/hf_cache}"
export SENTENCE_TRANSFORMERS_HOME="${SENTENCE_TRANSFORMERS_HOME:-$DATA_DIR/st_cache}"
export LANGUAGE="${LANGUAGE:-ar}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# مفاتيح اختيارية (اتركها فارغة إن لم تتوفر)
: "${OPENAI_API_KEY:=}"
: "${GEMINI_API_KEY:=}"

echo "== AutoLearn local runner =="
echo "APP_ROOT:   $APP_ROOT"
echo "DATA_DIR:   $DATA_DIR"
echo "DB:         $AUTOLEARN_DB"
echo "LANG:       $LANGUAGE"
echo "LOG_LEVEL:  $LOG_LEVEL"
echo

# ============ بيئة بايثون محلية (اختياري) ============
# لو تريد بيئة افتراضية محلياً:
if [[ -z "${RENDER:-}" ]]; then
  if [[ ! -d "$APP_ROOT/.venv" ]]; then
    echo "[py] creating venv ..."
    python3 -m venv "$APP_ROOT/.venv"
  fi
  # shellcheck disable=SC1091
  source "$APP_ROOT/.venv/bin/activate"
  python -m pip install --upgrade pip wheel setuptools
  pip install -r "$APP_ROOT/requirements.txt"
fi

# ============ وظائف تشغيل مكونات النظام ============
start_dashboard () {
  echo "[web] starting stats_web on :$PORT_WEB ..."
  nohup uvicorn stats_web:app --host 0.0.0.0 --port "$PORT_WEB" \
    > "$LOG_DIR/web.out" 2> "$LOG_DIR/web.err" < /dev/null &
  echo $! > "$LOG_DIR/web.pid"
}

start_core () {
  echo "[core] starting autolearn core API on :$PORT_CORE ..."
  nohup uvicorn autolearn:app --host 0.0.0.0 --port "$PORT_CORE" \
    > "$LOG_DIR/core.out" 2> "$LOG_DIR/core.err" < /dev/null &
  echo $! > "$LOG_DIR/core.pid"
}

start_news () {
  echo "[news] starting news_worker (interval via env NEWS_INTERVAL_SEC, default 60s) ..."
  : "${NEWS_INTERVAL_SEC:=60}"
  export NEWS_INTERVAL_SEC
  nohup python news_worker.py \
    > "$LOG_DIR/news.out" 2> "$LOG_DIR/news.err" < /dev/null &
  echo $! > "$LOG_DIR/news.pid"
}

stop_all () {
  for name in web core news; do
    if [[ -f "$LOG_DIR/$name.pid" ]]; then
      pid=$(cat "$LOG_DIR/$name.pid" || true)
      if [[ -n "${pid:-}" ]]; then
        echo "[stop] $name pid=$pid"
        kill "$pid" 2>/dev/null || true
      fi
      rm -f "$LOG_DIR/$name.pid"
    fi
  done
}

status_all () {
  for name in web core news; do
    if [[ -f "$LOG_DIR/$name.pid" ]]; then
      pid=$(cat "$LOG_DIR/$name.pid" || true)
      if ps -p "$pid" > /dev/null 2>&1; then
        echo "[ok] $name running (pid=$pid)"
      else
        echo "[!!] $name not running (stale pid file)"
      fi
    else
      echo "[..] $name not started"
    fi
  done
}

tail_logs () {
  echo "Tailing logs (Ctrl+C للإيقاف) ..."
  tail -n +1 -f "$LOG_DIR/"*.out "$LOG_DIR/"*.err
}

# ============ أوامر السكربت ============
case "${1:-all}" in
  all)
    stop_all || true
    start_dashboard
    start_core
    start_news
    status_all
    echo
    echo "URLs:"
    echo "• Dashboard: http://localhost:${PORT_WEB}/"
    echo "• Ask page : http://localhost:${PORT_WEB}/chat"
    echo "• Core API : http://localhost:${PORT_CORE}/docs"
    echo
    tail_logs
    ;;
  web)
    stop_all || true
    start_dashboard
    status_all
    tail_logs
    ;;
  core)
    stop_all || true
    start_core
    status_all
    tail_logs
    ;;
  news)
    stop_all || true
    start_news
    status_all
    tail_logs
    ;;
  stop)
    stop_all
    status_all
    ;;
  status)
    status_all
    ;;
  logs)
    tail_logs
    ;;
  *)
    echo "Usage: $0 [all|web|core|news|stop|status|logs]"
    exit 1
    ;;
esac
