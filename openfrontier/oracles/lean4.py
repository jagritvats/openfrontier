"""Tier-1 oracle: Lean 4 kernel verification (wired; off in the seeded demo).

Contract: the artifact is a single .lean file. We build it with the pinned
toolchain (docker image leanprover/lean4:<tag>, --network none) and accept only
if:
  1. the build succeeds,
  2. the file contains no `sorry`,
  3. the axioms reported by `#print axioms` are a subset of the standard three
     (propext, Classical.choice, Quot.sound).

No kernel, no badge: if docker is unavailable the verdict is an honest
build_error, never a skip.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

from . import Verdict, sha256_file

NAME = "lean4/0.1"
IMAGE = "leanprover/lean4:v4.15.0"
STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
TIMEOUT_S = 600


class Lean4:
    def verify(self, artifact: str | Path) -> Verdict:
        artifact = Path(artifact).resolve()
        digest = sha256_file(artifact)
        src = artifact.read_text(encoding="utf-8")
        if re.search(r"\bsorry\b", src):
            return Verdict("refuted", NAME, digest, log_tail="contains `sorry`")
        if shutil.which("docker") is None:
            return Verdict("build_error", NAME, digest, log_tail="docker not available")
        cmd = [
            "docker", "run", "--rm", "--network", "none", "--memory", "4g",
            "-v", f"{artifact.parent}:/work:ro", "-w", "/work", IMAGE,
            "lean", artifact.name,
        ]
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return Verdict("build_error", NAME, digest, log_tail=f"timeout after {TIMEOUT_S}s")
        seconds = round(time.perf_counter() - t0, 3)
        log_tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-20:])
        if proc.returncode != 0:
            return Verdict("build_error", NAME, digest, log_tail=log_tail, seconds=seconds)
        lists = re.findall(r"\[([^\]]*)\]", proc.stdout)
        axioms = {a.strip() for a in lists[-1].split(",")} if lists else set()
        axioms.discard("")
        extra = axioms - STANDARD_AXIOMS
        if extra:
            return Verdict("refuted", NAME, digest,
                           details={"extra_axioms": sorted(extra)}, log_tail=log_tail, seconds=seconds)
        return Verdict("checked", NAME, digest,
                       details={"axioms": sorted(axioms)}, log_tail=log_tail, seconds=seconds)
