"""Tier-2 oracle: deterministic certificate re-run.

The artifact is a self-contained Python program that prints exactly one JSON
verdict on its last stdout line: {"result": "holds" | "fails", ...details}.
The oracle re-executes it in a clean subprocess (fixed PYTHONHASHSEED,
wall-clock timeout) and maps: holds -> checked, fails -> refuted,
anything else -> build_error.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import Verdict, sha256_file

NAME = "certificate_rerun/0.1"
TIMEOUT_S = 300


class CertificateRerun:
    def verify(self, artifact: str | Path) -> Verdict:
        artifact = Path(artifact)
        digest = sha256_file(artifact)
        env = dict(os.environ, PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(artifact)],
                capture_output=True, text=True, timeout=TIMEOUT_S, env=env,
            )
        except subprocess.TimeoutExpired:
            return Verdict("build_error", NAME, digest, log_tail=f"timeout after {TIMEOUT_S}s")
        seconds = round(time.perf_counter() - t0, 3)
        out_lines = proc.stdout.strip().splitlines()
        log_tail = "\n".join((out_lines + proc.stderr.strip().splitlines())[-20:])
        if proc.returncode != 0 or not out_lines:
            return Verdict("build_error", NAME, digest,
                           log_tail=log_tail or f"exit code {proc.returncode}", seconds=seconds)
        try:
            payload = json.loads(out_lines[-1])
        except json.JSONDecodeError:
            return Verdict("build_error", NAME, digest, log_tail=log_tail, seconds=seconds)
        result = payload.pop("result", None)
        status = {"holds": "checked", "fails": "refuted"}.get(result)
        if status is None:
            return Verdict("build_error", NAME, digest, log_tail=log_tail, seconds=seconds)
        return Verdict(status, NAME, digest, details=payload, log_tail=log_tail, seconds=seconds)
