"""Tek bir paylaşım döngüsü: üret → görselleştir → commit/push → yayınla → geçmişe kaydet.

Kullanım: python src/run.py [slot] [--dry-run]
Slot verilmezse Türkiye saatine göre otomatik seçilir.
"""
import datetime as dt
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import generate  # noqa: E402
import render  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TR = dt.timezone(dt.timedelta(hours=3))


def auto_slot(now):
    h = now.hour
    if h < 11:
        return "sabah"
    if h < 15:
        return "ogle"
    if h < 19:
        return "aksam"
    if h < 22:
        return "gece"
    return "gece_gec"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    dry = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    now = dt.datetime.now(TR)
    slot = args[0] if args and args[0] in generate.SLOTS else auto_slot(now)

    item = generate.generate(slot)
    rel = f"posts/{now:%Y-%m-%d}/{now:%H%M}-{slot}"
    outdir = os.path.join(ROOT, rel)
    files = render.render(item, outdir)
    with open(os.path.join(outdir, "content.json"), "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=2)

    if dry:
        print("DRY RUN — görseller:", outdir)
        print("=====CONTENT_JSON=====")
        print(json.dumps(item, ensure_ascii=False))
        print("=====END=====")
        return

    git("add", rel)
    git("commit", "-m", f"Gönderi: {item['topic_key']} ({slot})")
    git("push")
    sha = git("rev-parse", "HEAD")
    repo = os.environ["GITHUB_REPOSITORY"]
    urls = [f"https://raw.githubusercontent.com/{repo}/{sha}/{rel}/{os.path.basename(p)}" for p in files]

    import publish  # noqa: E402
    media_id = publish.publish(item, urls)

    hist = generate.load_history()
    hist["posts"].append({
        "date": now.isoformat(timespec="minutes"),
        "slot": slot,
        "topic_key": item["topic_key"],
        "category": item["category"],
        "headline": item["headline"],
        "media_id": media_id,
        "folder": rel,
    })
    with open(generate.HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    git("add", "data/history.json")
    git("commit", "-m", f"Yayınlandı: {item['topic_key']}")
    git("push")
    print("Yayınlandı:", media_id)


if __name__ == "__main__":
    main()
