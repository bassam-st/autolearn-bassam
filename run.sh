#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$APP_ROOT/logs"
DATA_DIR="${DATA_DIR:-$APP_ROOT/data}"
PORT_WEB="${PORT:-8000}"
PORT_CORE="${PORT_CORE:-10000}"
mkdir -p "$LOG_DIR" "$DATA_DIR"

export AUTOLEARN_DB="${AUTOLEARN_DB:-$DATA_DIR/autolearn.db}"
export HF_HOME="${HF_HOME:-$DATA_DIR/hf_cache}"
export SENTENCE_TRANSFORMERS_HOME="${SENTENCE_TRANSFORMERS_HOME:-$DATA_DIR/st_cache}"
export LANGUAGE="${LANGUAGE:-ar}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

start_dashboard(){ nohup uvicorn stats_web:app --host 0.0.0.0 --port "$PORT_WEB" >"$LOG_DIR/web.out" 2>"$LOG_DIR/web.err" & echo $! >"$LOG_DIR/web.pid"; }
start_core(){ nohup uvicorn autolearn:app --host 0.0.0.0 --port "$PORT_CORE" >"$LOG_DIR/core.out" 2>"$LOG_DIR/core.err" & echo $! >"$LOG_DIR/core.pid"; }
start_news(){ nohup python news_worker.py >"$LOG_DIR/news.out" 2>"$LOG_DIR/news.err" & echo $! >"$LOG_DIR/news.pid"; }
stop_all(){ for n in web core news; do [[ -f "$LOG_DIR/$n.pid" ]] && kill "$(cat "$LOG_DIR/$n.pid")" 2>/dev/null || true; rm -f "$LOG_DIR/$n.pid"; done; }
status_all(){ for n in web core news; do if [[ -f "$LOG_DIR/$n.pid" ]] && ps -p "$(cat "$LOG_DIR/$n.pid")" >/dev/null; then echo "[ok] $n"; else echo "[..] $n not running"; fi; done; }

case "${1:-all}" in
  all) stop_all; start_dashboard; start_core; start_news; status_all; tail -f "$LOG_DIR/"*.out "$LOG_DIR/"*.err ;;
  web) stop_all; start_dashboard; status_all; tail -f "$LOG_DIR/web."* ;;
  core) stop_all; start_core; status_all; tail -f "$LOG_DIR/core."* ;;
  news) stop_all; start_news; status_all; tail -f "$LOG_DIR/news."* ;;
  stop) stop_all; status_all ;;
  status) status_all ;;
  *) echo "Usage: $0 [all|web|core|news|stop|status]"; exit 1 ;;
esac
