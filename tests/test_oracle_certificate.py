import json
from pathlib import Path

import pytest

from openfrontier.oracles import get_oracle
from openfrontier.oracles.certificate import CertificateRerun

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "problems" / "erdos-straus" / "artifacts"


def _write(tmp_path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_holds_maps_to_checked(tmp_path):
    artifact = _write(tmp_path, "ok.py", 'import json; print(json.dumps({"result": "holds", "x": 1}))\n')
    v = CertificateRerun().verify(artifact)
    assert v.status == "checked"
    assert v.details == {"x": 1}
    assert len(v.artifact_sha256) == 64


def test_fails_maps_to_refuted(tmp_path):
    artifact = _write(tmp_path, "no.py", 'import json; print(json.dumps({"result": "fails", "counterexample": 2}))\n')
    v = CertificateRerun().verify(artifact)
    assert v.status == "refuted"
    assert v.details["counterexample"] == 2


def test_crash_maps_to_build_error(tmp_path):
    artifact = _write(tmp_path, "boom.py", "raise SystemExit(3)\n")
    assert CertificateRerun().verify(artifact).status == "build_error"


def test_garbage_output_maps_to_build_error(tmp_path):
    artifact = _write(tmp_path, "junk.py", "print('not json')\n")
    assert CertificateRerun().verify(artifact).status == "build_error"


def test_real_refutation_certificate():
    v = CertificateRerun().verify(ART / "refute_b_equals_c.py")
    assert v.status == "refuted"
    assert v.details["counterexample"] == {"n": 5, "claim": "b = c"}


def test_real_mod4_certificate():
    v = CertificateRerun().verify(ART / "cert_mod4.py")
    assert v.status == "checked"
    assert v.details["family"] == "n = 3 (mod 4)"


def test_real_bound_certificate():
    v = CertificateRerun().verify(ART / "cert_bound.py")
    assert v.status == "checked"
    assert v.details["bound"] == 10_000


def test_unknown_oracle_rejected():
    with pytest.raises(ValueError, match="unknown oracle"):
        get_oracle("trust_me_bro")
