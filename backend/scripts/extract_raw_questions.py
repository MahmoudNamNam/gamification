"""
Extract questions from raw-data (JSON or JSONL) into the questions collection.
Each raw record: category_id, level, q [, hint, answer, q_media, hint_media, answer_media].
Output: Question docs with prompt, hint, answer (each PromptBlock: text + optional media).

Usage (from backend dir):
  python -m scripts.extract_raw_questions [path]
  path defaults to: raw-data/ (relative to backend) or env RAW_DATA_PATH.
  Reads all .json and .jsonl files from that directory.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import init_db, get_categories_collection, get_questions_collection

LEVEL_POINTS = {1: 100, 2: 200, 3: 500}


def _media_block(url: str | None) -> dict | None:
    if not url or not url.strip():
        return None
    return {
        "kind": "url",
        "url": url.strip(),
        "gridfs_file_id": None,
        "base64": None,
        "mime": None,
    }


def _prompt_block(text: str | None, media_url: str | None) -> dict:
    return {
        "text": (text or "").strip() or None,
        "media": _media_block(media_url),
    }


def _normalize_level(level) -> int:
    if isinstance(level, int) and level in (1, 2, 3):
        return level
    if isinstance(level, str):
        level = level.strip().lower()
        if level in ("1", "easy"): return 1
        if level in ("2", "medium"): return 2
        if level in ("3", "hard"): return 3
    return 1


def load_raw_records(path: Path) -> list[dict]:
    records = []
    for f in sorted(path.iterdir()):
        if f.suffix not in (".json", ".jsonl"):
            continue
        text = f.read_text(encoding="utf-8")
        if f.suffix == ".jsonl":
            for line in text.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"  Skip line in {f.name}: {e}")
        else:
            try:
                data = json.loads(text)
                if isinstance(data, list):
                    records.extend(data)
                else:
                    records.append(data)
            except json.JSONDecodeError as e:
                print(f"  Skip {f.name}: {e}")
    return records


def extract_one(raw: dict, categories_by_id: dict[str, ObjectId]) -> dict | None:
    cid = raw.get("category_id")
    if not cid:
        return None
    cid = str(cid).strip()
    if cid not in categories_by_id:
        return None
    level = _normalize_level(raw.get("level", 1))
    q_text = raw.get("q") or raw.get("question") or ""
    if not q_text:
        return None
    hint_text = raw.get("hint")
    answer_text = raw.get("answer")
    q_media = raw.get("q_media") or raw.get("prompt_media")
    hint_media = raw.get("hint_media")
    answer_media = raw.get("answer_media")
    points = LEVEL_POINTS.get(level, 100)
    now = datetime.now(timezone.utc)
    return {
        "category_id": categories_by_id[cid],
        "level": level,
        "points": points,
        "prompt": _prompt_block(q_text, q_media),
        "hint": {
            "enabled": bool(hint_text or hint_media),
            "content": _prompt_block(hint_text, hint_media) if (hint_text or hint_media) else None,
        },
        "answer": _prompt_block(answer_text, answer_media) if (answer_text or answer_media) else None,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }


def main():
    raw_dir = os.environ.get("RAW_DATA_PATH")
    if raw_dir is None:
        raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw-data")
    if len(sys.argv) > 1:
        raw_dir = sys.argv[1]
    path = Path(raw_dir)
    if not path.is_dir():
        print(f"Directory not found: {path}")
        print("Create raw-data/ and add .json or .jsonl files, or set RAW_DATA_PATH.")
        sys.exit(1)

    init_db()
    categories = list(get_categories_collection().find({"active": True}))
    categories_by_id = {str(c["_id"]): c["_id"] for c in categories}
    if not categories_by_id:
        print("No active categories in DB. Run seed or add categories first.")
        sys.exit(1)

    records = load_raw_records(path)
    if not records:
        print(f"No records found in {path} (.json / .jsonl).")
        sys.exit(0)

    col = get_questions_collection()
    inserted = 0
    skipped = 0
    for raw in records:
        doc = extract_one(raw, categories_by_id)
        if doc is None:
            skipped += 1
            continue
        col.insert_one(doc)
        inserted += 1
    print(f"Inserted {inserted} questions from {path}. Skipped {skipped}.")


if __name__ == "__main__":
    main()
