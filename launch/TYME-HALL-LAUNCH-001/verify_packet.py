#!/usr/bin/env python3
"""TYME-HALL-LAUNCH-001 offline structural assurance, no network or mutations.

Use: python3 launch/TYME-HALL-LAUNCH-001/verify_packet.py
This cannot prove an active model, Cloudflare deployment, public routes or security.
"""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

class LaunchPacketTests(unittest.TestCase):
    def setUp(self):
        self.ledger = load("issue-ledger.json")
        self.gates = load("release-gates.json")
        self.content = load("public-content-manifest.json")
        self.agi = load("fixtures/agi-0001-publication.json")

    def test_ids_and_command(self):
        self.assertEqual(self.gates["launch_id"], "TYME-HALL-LAUNCH-001")
        self.assertEqual(self.content["launch_id"], self.gates["launch_id"])
        self.assertEqual(self.ledger["command"], self.gates["command"])
        self.assertEqual(self.gates["conditional_release_date"], "2026-10-30")

    def test_seven_gates_open_without_self_approval(self):
        self.assertEqual([g["id"] for g in self.gates["gates"]], [f"G{i}" for i in range(7)])
        self.assertTrue(all(g["status"] == "OPEN" for g in self.gates["gates"]))
        self.assertFalse(self.gates["launch_authorized"])
        self.assertFalse(self.gates["production_deployment_authorized"])
        self.assertFalse(self.gates["autonomous_office_authority_authorized"])

    def test_issues_and_dep_graph(self):
        issues = self.ledger["issues"]
        self.assertEqual(len(issues), 9)
        self.assertEqual(len({(i["repo"], i["number"]) for i in issues}), len(issues))
        ids = {i["id"] for i in issues}
        self.assertTrue(all(i["accountable_owner"] for i in issues))
        self.assertTrue(all(i["status"] == "OPEN" for i in issues))
        self.assertTrue(all(set(i["depends_on"]) <= ids for i in issues))
        self.assertTrue(all(i["id"] not in i["depends_on"] for i in issues))

    def test_agi_is_document_published_not_autonomous(self):
        self.assertEqual(self.agi["scroll"]["scroll_id"], "AGI-0001")
        self.assertEqual(self.agi["scroll"]["public_posture"], "PUBLISHED_CANONICAL")
        self.assertTrue(self.agi["authority"]["publication_authorized"])
        self.assertFalse(self.agi["authority"]["system_self_authorizing"])
        self.assertEqual(self.agi["authority"]["institutional_effect"], "public_inheritance_only")
        self.assertFalse(self.agi["epistemic_posture"]["empirical_specification"])

    def test_manifest_source_identity(self):
        pub = self.content["release_publications"]
        self.assertEqual(len(pub), 1)
        self.assertEqual(pub[0]["id"], self.agi["scroll"]["scroll_id"])
        self.assertEqual(pub[0]["source_commit"], self.gates["source_baselines"]["sovereign-codex/Codex-interface-"])
        self.assertEqual(pub[0]["historical_source_sha256"], self.agi["provenance"]["historical_source_sha256"])
        self.assertEqual(pub[0]["current_live_http_status"], "UNVERIFIED_THIS_SESSION")

    def test_gfc_remains_unpublished_candidate(self):
        self.assertFalse(self.gates["gfc_publication_authorized"])
        self.assertEqual([p["id"] for p in self.content["excluded_publication_candidates"]], ["GFC-0001"])
        self.assertTrue(self.content["excluded_publication_candidates"][0]["excluded_from_beta_publication"])
        self.assertFalse(self.content["excluded_publication_candidates"][0]["publication_authorized"])

    def test_missions_and_identity(self):
        self.assertEqual([m["id"] for m in self.content["learning_missions"]], ["M01","M02","M03"])
        self.assertEqual(self.content["lab_mvp_mission_id"], "M03")
        self.assertTrue(all(not m["physical_build_authorized"] for m in self.content["learning_missions"]))
        self.assertEqual(self.content["hall_receipt_carrier"], "NONE_NATIVE")
        self.assertEqual(self.content["participation_write_carrier"], "EXTERNAL_GITHUB_ISSUES")
        self.assertTrue(self.content["no_self_authorizing_system"])

    def test_no_funded_bounties_or_false_canonical(self):
        self.assertFalse(self.gates["financial_bounties_authorized"])
        self.assertEqual(self.content["manifest_status"], "REVIEW_CANDIDATE_NOT_DEPLOYED")

if __name__ == "__main__":
    unittest.main(verbosity=2)
