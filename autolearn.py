# autolearn.py
import os, time, yaml, subprocess, sys

CONFIG_PATH = os.path.join(os.getcwd(), "config.yaml")

def load_cfg():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_once():
    # نشغّل worker مرة واحدة (في نفس بيئة البايثون)
    cmd = [sys.executable, "news_worker.py", "--once"]
    subprocess.run(cmd, check=False)

def main():
    print("🔁 AutoLearn main loop starting...")
    while True:
        try:
            cfg = load_cfg()
            minutes = int(cfg.get("pace", {}).get("interval_minutes", 10))
        except Exception as e:
            print("⚠️ Failed to read config.yaml, defaulting to 10 min:", e)
            minutes = 10

        print("▶️ Running learning cycle (news_worker --once)")
        run_once()
        print(f"⏱ Sleeping {minutes} minutes ...")
        time.sleep(minutes * 60)

if __name__ == "__main__":
    main()
