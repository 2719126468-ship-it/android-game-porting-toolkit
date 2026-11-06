"""Safe, review-only unified-diff proposals for game source files."""
from __future__ import annotations

import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

MAX_SOURCE_BYTES = 1024 * 1024
MAX_DIFF_BYTES = 256 * 1024


class PatchProposalError(ValueError):
    """A proposed patch cannot be safely represented."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_patch_proposal(
    source_root: str | Path,
    project_root: str | Path,
    *,
    file_path: str,
    replacement_text: str,
    rationale: str,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    """Write a review-only proposal; never modify the original source tree."""
    if not isinstance(file_path, str) or not file_path.strip():
        raise PatchProposalError("file_path must be a non-empty relative path")
    if "\\" in file_path or file_path.startswith(("/", "\\\\")):
        raise PatchProposalError("file_path must use relative POSIX path syntax")
    relative = PurePosixPath(file_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise PatchProposalError("file_path must not be absolute or traverse parent directories")
    if not isinstance(replacement_text, str) or "\x00" in replacement_text:
        raise PatchProposalError("replacement_text must be valid UTF-8 text")
    if len(replacement_text.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise PatchProposalError("replacement_text exceeds the 1 MiB safety limit")
    if not isinstance(rationale, str) or not rationale.strip():
        raise PatchProposalError("rationale is required")
    evidence_items = evidence or []
    if not isinstance(evidence_items, list) or any(not isinstance(item, str) or not item.strip() for item in evidence_items):
        raise PatchProposalError("evidence must be a list of non-empty strings")

    root = Path(source_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise PatchProposalError("source_root must be a directory")
    target = root
    for component in relative.parts:
        target = target / component
        if target.is_symlink():
            raise PatchProposalError("symbolic links are not valid patch targets")
    target = target.resolve(strict=True)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PatchProposalError("patch target resolves outside source_root") from exc
    if not target.is_file():
        raise PatchProposalError("patch target must be a regular file")
    before_bytes = target.read_bytes()
    if len(before_bytes) > MAX_SOURCE_BYTES:
        raise PatchProposalError("source file exceeds the 1 MiB safety limit")
    if b"\\x00" in before_bytes:
        raise PatchProposalError("binary files cannot receive text patch proposals")
    try:
        before_text = before_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchProposalError("source file is not valid UTF-8 text") from exc
    after_bytes = replacement_text.encode("utf-8")
    if before_bytes == after_bytes:
        raise PatchProposalError("replacement_text does not change the source file")

    relative_name = relative.as_posix()
    diff = "".join(
        difflib.unified_diff(
            before_text.splitlines(keepends=True),
            replacement_text.splitlines(keepends=True),
            fromfile=f"a/{relative_name}",
            tofile=f"b/{relative_name}",
            n=3,
        )
    )
    diff_bytes = diff.encode("utf-8")
    if len(diff_bytes) > MAX_DIFF_BYTES:
        raise PatchProposalError("unified diff exceeds the 256 KiB safety limit")

    before_sha = _sha256(before_bytes)
    after_sha = _sha256(after_bytes)
    proposal_id = hashlib.sha256(
        f"{relative_name}\0{before_sha}\\0{after_sha}\\0{rationale}".encode("utf-8")
    ).hexdigest()[:16]
    project = Path(project_root).expanduser().resolve()
    proposals_dir = project / "patches" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = proposals_dir / f"{proposal_id}.json"
    if proposal_path.exists() or proposal_path.is_symlink():
        raise FileExistsError(f"patch proposal already exists: {proposal_path}")

    proposal: dict[str, Any] = {
        "schema_version": "1.0",
        "proposal_id": proposal_id,
        "status": "proposed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_file": relative_name,
        "before_sha256": before_sha,
        "after_sha256": after_sha,
        "source_file_bytes": len(before_bytes),
        "rationale": rationale.strip(),
        "evidence": evidence_items,
        "unified_diff": diff,
        "approval_required": True,
        "applied": False,
        "safety": {
            "review_only": True,
            "source_tree_modified": False,
            "patch_executor_available": False,
            "note": "This file is a proposal for human review. No source file was changed.",
        },
    }
    proposal_path.write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"proposal": proposal, "proposal_path": str(proposal_path.resolve())}
