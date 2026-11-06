"""Opt-in, read-only Ghidra Headless adapter."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path


class AdapterError(RuntimeError):
    """An external-tool adapter could not complete a validated operation."""


@dataclass(frozen=True)
class GhidraAnalysisResult:
    input_path: str
    input_sha256: str
    output_path: str
    log_path: str
    executable: str
    return_code: int
    elapsed_seconds: float
    summary: dict

    def to_dict(self):
        return asdict(self)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_ghidra(executable=None) -> Path:
    candidates = [Path(executable).expanduser()] if executable else []
    install = os.environ.get("GHIDRA_INSTALL_DIR")
    if install:
        root = Path(install).expanduser()
        candidates.extend(root / "support" / name for name in ("analyzeHeadless", "analyzeHeadless.bat"))
    for name in ("analyzeHeadless", "analyzeHeadless.bat"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_dir():
            candidate = candidate / "support" / ("analyzeHeadless.bat" if os.name == "nt" else "analyzeHeadless")
        if candidate.is_file():
            return candidate.resolve()
    raise AdapterError("Ghidra Headless not found. Set GHIDRA_INSTALL_DIR or pass --ghidra.")


def analyze_binary(binary, *, output=None, executable=None, timeout=1800,
                   analysis_timeout_per_file=1200, max_functions=20000):
    source = Path(binary).expanduser()
    if source.is_symlink() or not source.is_file():
        raise AdapterError("Input must be an existing regular file, not a symlink.")
    if not 10 <= timeout <= 7200 or not 1 <= analysis_timeout_per_file <= 7200:
        raise ValueError("Timeout values are outside the allowed range.")
    if not 1 <= max_functions <= 100000:
        raise ValueError("max_functions must be between 1 and 100000.")
    ghidra = discover_ghidra(executable)
    script_dir = Path(__file__).resolve().parent / "ghidra_scripts"
    script = script_dir / "AGPTExport.java"
    if not script.is_file():
        raise AdapterError(f"Bundled Ghidra script missing: {script}")
    target = Path(output).expanduser() if output else source.with_name(source.name + ".ghidra.json")
    if target.is_symlink() or target.with_suffix(target.suffix + ".log").is_symlink():
        raise AdapterError("Output and log paths must not be symlinks.")
    target.parent.mkdir(parents=True, exist_ok=True)
    log_path = target.with_suffix(target.suffix + ".log")
    before = _sha256(source)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="agpt-ghidra-") as temp:
        work = Path(temp)
        exported = work / "summary.json"
        vendor_log = work / "ghidra.log"
        args = [str(work), "AGPT_Analysis", "-import", str(source.resolve()),
                "-readOnly", "-deleteProject", "-analysisTimeoutPerFile",
                str(analysis_timeout_per_file), "-scriptPath", str(script_dir),
                "-postScript", "AGPTExport.java", str(exported), str(max_functions),
                "-log", str(vendor_log)]
        command = ([os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c",
                    subprocess.list2cmdline([str(ghidra), *args])]
                   if os.name == "nt" and ghidra.suffix.lower() in {".bat", ".cmd"}
                   else [str(ghidra), *args])
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=timeout, check=False, shell=False)
        except subprocess.TimeoutExpired as exc:
            log_path.write_text(f"Timed out after {timeout}s\n{exc.stdout}\n{exc.stderr}", encoding="utf-8")
            raise AdapterError(f"Ghidra timed out; see {log_path}") from exc
        vendor_text = vendor_log.read_text(encoding="utf-8", errors="replace") if vendor_log.exists() else ""
        log_path.write_text(
            f"COMMAND: {json.dumps(command)}\nEXIT: {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nGHIDRA LOG:\n{vendor_text}",
            encoding="utf-8")
        if result.returncode != 0:
            raise AdapterError(f"Ghidra exited with {result.returncode}; see {log_path}")
        if not exported.is_file():
            raise AdapterError(f"Ghidra produced no metadata export; see {log_path}")
        try:
            summary = json.loads(exported.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AdapterError("Ghidra metadata export is invalid.") from exc
        if not isinstance(summary, dict) or summary.get("schema_version") != "1.0":
            raise AdapterError("Ghidra export schema mismatch.")
        if _sha256(source) != before:
            raise AdapterError("Input changed during analysis; refusing to publish report.")
        payload = {"schema_version": "1.0", "tool": "Ghidra Headless",
                   "input_path": str(source.resolve()), "input_sha256": before, "analysis": summary}
        temp_out = target.with_suffix(target.suffix + ".tmp")
        temp_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp_out.replace(target)
    return GhidraAnalysisResult(str(source.resolve()), before, str(target), str(log_path),
                                str(ghidra), 0, round(time.monotonic() - started, 3), summary)
