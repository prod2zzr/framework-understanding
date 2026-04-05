"""Rule version tracking — detect and record changes to compliance rules.

On each review session, computes a fingerprint of the rules file.
When the fingerprint changes, appends a record to rule_versions.jsonl.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from contract_reviewer.utils.hashing import file_sha256
from contract_reviewer.utils.jsonl import append_jsonl

logger = logging.getLogger(__name__)


def check_and_record(rules_path: str, history_path: str = "data/rule_versions.jsonl") -> bool:
    """Compare current rules fingerprint with last recorded; record if changed.

    Returns True if rules have changed since last check.
    """
    rules_file = Path(rules_path)
    if not rules_file.exists():
        return False

    current_hash = file_sha256(rules_file)
    history = Path(history_path)

    # Read last recorded hash
    last_hash = None
    if history.exists():
        try:
            with open(history, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    last_hash = last_entry.get("sha256")
        except (json.JSONDecodeError, KeyError):
            pass

    if current_hash == last_hash:
        return False

    # Rules changed — record
    append_jsonl(history, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sha256": current_hash,
        "rules_path": str(rules_file),
        "size_bytes": rules_file.stat().st_size,
    })

    logger.info("Rules file changed (hash=%s…), recorded in %s", current_hash[:12], history_path)
    return True
