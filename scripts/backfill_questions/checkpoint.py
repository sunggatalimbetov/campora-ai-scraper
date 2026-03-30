"""Checkpoint save/load for resumable backfill progress."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CHECKPOINT_PATH = Path(__file__).parent / "backfill_progress.json"


def load_checkpoint(chat_id: int) -> Optional[dict]:
    """Load checkpoint for a given chat_id.

    Returns:
        Dict with 'last_message_id', 'messages_processed', 'questions_generated',
        or None if no checkpoint exists.
    """
    if not CHECKPOINT_PATH.exists():
        return None

    try:
        data = json.loads(CHECKPOINT_PATH.read_text())
        return data.get(str(chat_id))
    except (json.JSONDecodeError, OSError):
        return None


def save_checkpoint(
    chat_id: int,
    last_message_id: int,
    messages_processed: int,
    questions_generated: int,
) -> None:
    """Save checkpoint for a given chat_id."""
    data = {}
    if CHECKPOINT_PATH.exists():
        try:
            data = json.loads(CHECKPOINT_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    data[str(chat_id)] = {
        "last_message_id": last_message_id,
        "messages_processed": messages_processed,
        "questions_generated": questions_generated,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    tmp = CHECKPOINT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, CHECKPOINT_PATH)
