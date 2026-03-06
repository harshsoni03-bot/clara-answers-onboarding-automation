from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "dataset"
OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "accounts"


def load_text_file(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_transcripts(subdir: str):
    """
    Yield (account_id, Path) for all .txt transcripts in a dataset subdir.

    Filenames are assumed to be of the form:
      ACCOUNTID_demo_1.txt
      ACCOUNTID_onboarding_1.txt
    The account_id is everything before the first underscore.
    """
    base = DATASET_DIR / subdir
    if not base.exists():
        return
    for entry in base.glob("*.txt"):
        account_id = entry.stem.split("_", 1)[0]
        yield account_id, entry


def account_version_dir(account_id: str, version: str) -> Path:
    return OUTPUTS_DIR / account_id / version


def memo_path(account_id: str, version: str) -> Path:
    return account_version_dir(account_id, version) / "memo.json"


def agent_spec_path(account_id: str, version: str) -> Path:
    return account_version_dir(account_id, version) / "agent_spec.json"


def changelog_path(account_id: str) -> Path:
    return OUTPUTS_DIR / account_id / "changelog.md"


