"""The oracle contract.

An oracle is the only thing allowed to produce a verdict. Agents submit
artifacts; oracles re-run them in a pinned, networkless environment and report.
`checked` means the oracle re-ran it and it held — never that an agent said so.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

VERDICTS = {"checked", "refuted", "build_error"}


@dataclass
class Verdict:
    status: str                      # checked | refuted | build_error
    oracle: str                      # name/version, e.g. "certificate_rerun/0.1"
    artifact_sha256: str
    details: dict = field(default_factory=dict)   # machine-readable payload
    log_tail: str = ""               # last lines of the run, for humans
    seconds: float = 0.0


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def get_oracle(name: str):
    if name == "certificate_rerun":
        from .certificate import CertificateRerun
        return CertificateRerun()
    if name == "lean4":
        from .lean4 import Lean4
        return Lean4()
    raise ValueError(f"unknown oracle: {name!r}")
