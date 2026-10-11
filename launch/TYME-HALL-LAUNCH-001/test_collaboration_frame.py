"""Fail-closed offline test of the Door 04 collaboration framework.

These tests prove static contract and manifest invariants only. They cannot
prove GitHub rules are still active, test live security-reporting, verify
licenses, retain data lawfully, or authorize public participation.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
FILE = ROOT / "collaboration-frame-gates.json"
CROSSWALK = ROOT / "collaboration-frame-preflight.md"
HALL_PR = "https://github.com/sovereign-codex/Codex-interface-/pull/19"


class CollaborationFrameViolation(ValueError):
    pass


def load():
    return json.loads(FILE.read_text(encoding="utf-8"))


def validate(packet):
    def require(condition, text):
        if not condition:
            raise CollaborationFrameViolation(text)

    require(packet.get("schema") == "tyme-hall-launch-001/collaboration-frame/v0.1",
            "schema drift")
    require(packet.get("launch_id") == "TYME-HALL-LAUNCH-001", "wrong launch")
    require(packet.get("posture") == "REVIEW_CANDIDATE_NON_AUTHORIZING",
            "cannot claim reviewed/approved")
    src = packet.get("source_refs", {})
    for name in ("door04", "door04_mobile", "live_participation", "trail",
                 "routing", "hall_ruleset", "public_source", "issue18", "hall_pr19"):
        require(isinstance(src.get(name), str) and src[name].startswith("https://"),
                "missing source: " + name)
    require(src["hall_pr19"] == HALL_PR, "unreviewed PR substituted")
    surfaces = {i["id"]: i for i in packet.get("surfaces", [])}
    require(set(surfaces) == {
        "PUBLIC_HALL", "LEARNING_SHARE", "CONTRIBUTION",
        "NATIVE_HALL_RECEIPT", "INSTITUTIONAL_WORK",
    }, "public/intake/institutional surface altered")
    require(surfaces["LEARNING_SHARE"]["transport"] == "CLIENT_SESSION_ONLY",
            "Share cannot be treated as institutional submission")
    require(surfaces["CONTRIBUTION"]["transport"] == "GITHUB_ISSUES_EXTERNAL",
            "current external transport changed without approval")
    require(surfaces["NATIVE_HALL_RECEIPT"]["transport"] == "NONE"
            and surfaces["NATIVE_HALL_RECEIPT"]["observed"] == "ABSENT",
            "native Hall receiving carrier falsely claimed")

    decisions = packet.get("decisions", [])
    require([i.get("id") for i in decisions] == [f"D{i}" for i in range(1, 7)],
            "six founder decisions must be preserved in order")
    for decision in decisions:
        require(bool(decision.get("owner")) and bool(decision.get("evidence"))
                and isinstance(decision.get("blocks"), list)
                and bool(decision["blocks"]), "unowned or unbounded decision")
        require(decision.get("action_executed") is False,
                "review packet cannot claim founder decision executed")
        require(decision.get("status") in {
            "HUMAN_DECISION_REQUIRED", "QUALIFICATION_PENDING", "TEST_PENDING",
        }, "unearned decision completion")

    abuse = packet.get("abuse_case", {})
    require(abuse.get("incident") == "ISSUE_18_REPEATED_UNSOLICITED_BOUNTY_CLAIMS",
            "source incident lost")
    require(abuse.get("comments_observed", 0) >= 91
            and abuse.get("same_author_comments_observed", 0) >= 91
            and abuse.get("same_author_comments_observed") <= abuse.get("comments_observed"),
            "incident snapshot lacks observed abundance")
    require(abuse.get("containment") == "LOCKED_SPAM",
            "incident response status must not be invented")
    for key in ("financial_commitment", "offsite_payload_verified",
                "hall_native_receipt_issued", "promotion_authorized"):
        require(abuse.get(key) is False, "abuse cannot create effect: " + key)

    r = packet.get("release_controls", {})
    require(r.get("ruleset_id") == 24880323 and r.get("ruleset_status") == "ACTIVE"
            and r.get("target_branch") == "main", "saved ruleset baseline changed")
    require(r.get("required_approvals") == 1 and r.get("bypass_actors") == 0,
            "human approval or no-bypass bound changed")
    for key in ("require_last_push_approval", "dismiss_stale_reviews",
                "require_conversation_resolution", "unmerged_review_branch"):
        require(r.get(key) is True, "release-review control missing: " + key)
    for key in ("force_push_allowed", "deletion_allowed",
                "required_ci_currently_enforced", "production_release_authorized"):
        require(r.get(key) is False, "release authority falsified: " + key)
    require(r.get("candidate_ci_context") == "hall_launch_001_premerge",
            "candidate check is no longer identified")
    transition = packet.get("transitions", {})
    require(len(transition) >= 9 and all(value is False
                                        for value in transition.values()),
            "untrusted contribution granted institutional state")
    expected_transitions = {
        "external_submission_is_hall_event", "external_issue_is_hall_receipt",
        "local_share_is_external_submission", "submitted_contribution_is_verified",
        "review_is_institutional_authority", "github_approval_is_deployment_authorization",
        "financial_bounties_authorized", "native_identity_or_receipt_enabled",
    }
    require(expected_transitions <= set(transition),
            "expected invariant removed")
    acceptance = packet.get("acceptance", [])
    require([a.get("id") for a in acceptance] == [f"A{i}" for i in range(1, 9)],
            "collaboration acceptance sequence incomplete")
    require(all(a.get("status") == "OPEN" and a.get("evidence_refs") == []
                for a in acceptance), "manifest cannot certify missing evidence")
    for key in ("public_contribution_campaign_authorized", "public_site_mutated",
                "new_private_ingress_created", "license_granted_by_this_packet",
                "contributors_invited"):
        require(packet.get(key) is False,
                "static review cannot create consequence: " + key)
    require(packet.get("authority_effect") == "none", "authority transfer attempted")
    require(packet.get("status")
            == "FRAME_NOT_ACCEPTED_FOR_PUBLIC_INTENTIONAL_RECRUITMENT",
            "false completion")
    text = CROSSWALK.read_text(encoding="utf-8")
    require("Door 04" in text and "GitHub Issues" in text
            and "license" in text.lower(), "crosswalk incomplete")
    require("Do not claim the door is production-safe" in text,
            "fail-closed gate not explicit")
    return {"state": "SYNTHETIC_CONTRACT_VALID",
            "gate": "OPEN", "authority_effect": "none", "founder_decisions": 6,
            "evidence_acceptance_gates": 8, "public_site_modified": False}


class CollaborationFrameTests(unittest.TestCase):
    def setUp(self):
        self.packet = load()

    def test_expected_candidate_is_non_authorizing(self):
        result = validate(self.packet)
        self.assertEqual(result["gate"], "OPEN")
        self.assertEqual(result["founder_decisions"], 6)

    def test_license_cannot_be_awarded_by_document(self):
        p = deepcopy(self.packet)
        p["license_granted_by_this_packet"] = True
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_financial_bounty_cannot_be_implied(self):
        p = deepcopy(self.packet)
        p["transitions"]["financial_bounties_authorized"] = True
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_native_receipt_cannot_be_forged(self):
        p = deepcopy(self.packet)
        p["surfaces"][3]["observed"] = "LIVE"
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_external_issue_does_not_promote_hall_event(self):
        p = deepcopy(self.packet)
        p["transitions"]["external_submission_is_hall_event"] = True
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_share_not_submission(self):
        p = deepcopy(self.packet)
        p["surfaces"][1]["transport"] = "HALL_EVENT_ENVELOPE"
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_review_does_not_grant_authority(self):
        p = deepcopy(self.packet)
        p["transitions"]["review_is_institutional_authority"] = True
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_required_review_cannot_be_disabled(self):
        p = deepcopy(self.packet)
        p["release_controls"]["required_approvals"] = 0
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_rule_bypass_cannot_be_hidden(self):
        p = deepcopy(self.packet)
        p["release_controls"]["bypass_actors"] = 1
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_ci_must_not_be_falsely_marked_required(self):
        p = deepcopy(self.packet)
        p["release_controls"]["required_ci_currently_enforced"] = True
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_g4_g5_cannot_pass_without_evidence(self):
        p = deepcopy(self.packet)
        p["acceptance"][0]["status"] = "PASS"
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_founder_decisions_stay_pending(self):
        p = deepcopy(self.packet)
        p["decisions"][2]["action_executed"] = True
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_cannot_announce_public_recruitment(self):
        p = deepcopy(self.packet)
        p["public_contribution_campaign_authorized"] = True
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_abuse_is_not_accepted_contribution(self):
        p = deepcopy(self.packet)
        p["abuse_case"]["promotion_authorized"] = True
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)

    def test_no_out_of_band_production_permission(self):
        p = deepcopy(self.packet)
        p["release_controls"]["production_release_authorized"] = True
        with self.assertRaises(CollaborationFrameViolation):
            validate(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
