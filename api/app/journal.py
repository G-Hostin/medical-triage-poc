import json
import os
from pathlib import Path

DEFAULT_LOG_PATH = "/app/logs/interactions.jsonl"


def write_entry(entry: dict) -> None:
    # Une ligne JSON par appel, ajoutée à la fin du fichier (traçabilité pour les audits)
    path = Path(os.getenv("LOG_PATH") or DEFAULT_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
