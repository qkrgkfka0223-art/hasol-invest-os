"""Offline regression that strict Frozen handoff cannot pass without source freshness."""
import copy
import json
import subprocess
import sys

from test_brain_handoff import fixture as brain_fixture
from test_discovery_freshness import sample as source_fixture


def pair():
    brain = brain_fixture()
    source = source_fixture()
    source["run_id"] = brain["run_id"]
    source["blind_locked_at_utc"] = brain["blind_locked_at_utc"]
    source["first_price_exposure_at_utc"] = brain["first_market_data_access_at_utc"]
    source["cutoff_utc"] = brain["frozen"][0]["FROZEN_AT_UTC"]
    source["candidate_packets"][0]["ticker"] = "T001"
    source["issuer_releases"][0]["ticker"] = "T001"
    source["issuer_sweeps"][0]["completed_at_utc"] = "2026-11-17T12:30:00Z"
    source["issuer_sweeps"][1]["completed_at_utc"] = "2026-11-17T12:59:00Z"
    return brain, source


def invoke(tmp_path, brain, source=None, strict=True):
    brain_file = tmp_path / "brain.json"
    source_file = tmp_path / "source.json"
    brain_file.write_text(json.dumps(brain), encoding="utf-8")
    cmd = [sys.executable, "-m", "scripts.validate_brain_handoff", "--input", str(brain_file)]
    if source is not None:
        source_file.write_text(json.dumps(source), encoding="utf-8")
        cmd += ["--source-audit-input", str(source_file)]
    if strict:
        cmd.append("--require-evidence-ready")
    output = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert output.stdout, output.stderr
    return output.returncode, json.loads(output.stdout)


def test_strict_pair_synthetic_evidence_ready_requires_independent_verification(tmp_path):
    brain, source = pair()
    code, result = invoke(tmp_path, brain, source)
    assert code == 0
    assert result["decision"] == "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY"
    assert result["source_audit"]["decision"] == "EVIDENCE_READY_REQUIRES_INDEPENDENT_VERIFY"


def test_old_single_gate_cannot_claim_strict_evidence_ready(tmp_path):
    brain, _ = pair()
    code, result = invoke(tmp_path, brain)
    assert code == 3
    assert result["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
    assert any("source freshness" in x for x in result["degraded"])


def test_known_sls_style_material_release_unhandled_blocks_both_gates(tmp_path):
    brain, source = pair()
    source["candidate_packets"][0]["handled_release_ids"] = []
    code, result = invoke(tmp_path, brain, source)
    assert code == 2
    assert any("MATERIAL_ISSUER_RELEASE_NOT_HANDLED" in x for x in result["errors"])


def test_mismatched_run_id_blocks(tmp_path):
    brain, source = pair()
    source["run_id"] = "WRONG-RUN"
    code, result = invoke(tmp_path, brain, source)
    assert code == 2
    assert any("RUN_ID mismatch" in x for x in result["errors"])


def test_candidate_missing_from_brain_blocks(tmp_path):
    brain, source = pair()
    source["candidate_packets"][0]["ticker"] = "SLS"
    source["issuer_releases"][0]["ticker"] = "SLS"
    code, result = invoke(tmp_path, brain, source)
    assert code == 2
    assert any("absent from Brain" in x for x in result["errors"])


def test_mismatched_blind_lock_blocks(tmp_path):
    brain, source = pair()
    source["blind_locked_at_utc"] = "2026-11-17T12:40:00Z"
    code, result = invoke(tmp_path, brain, source)
    assert code == 2
    assert any("Blind locks differ" in x for x in result["errors"])


def test_source_cutoff_after_frozen_blocks(tmp_path):
    brain, source = pair()
    source["cutoff_utc"] = "2026-11-17T13:01:00Z"
    code, result = invoke(tmp_path, brain, source)
    assert code == 2
    assert any("after Frozen" in x for x in result["errors"])


def test_unverified_price_free_sweep_cannot_be_clean(tmp_path):
    brain, source = pair()
    source["issuer_sweeps"][0]["price_reaction_preview"] = None
    code, result = invoke(tmp_path, brain, source)
    assert code == 3
    assert result["decision"] == "OFFICIAL_PARTIAL_NOT_CLEAN"
