# Control Center handoff probe readiness 001

**Standing: draft CI and probe preparation; live routing remains disabled in the proposed policy.**

Coordinated review of [CCC #21](https://github.com/sovereign-codex/Codex-control-center/pull/21), [CCC #22](https://github.com/sovereign-codex/Codex-control-center/pull/22), and [AVOT #18](https://github.com/sovereign-codex/AVOT-engine/pull/18) found that the CCC integration had 50 recorded local tests but no matching GitHub CI workflow. This addition runs those existing tests on matching pull requests and main pushes. Pull requests have no main-only base filter, so the current #22 stack is covered.

## Change and verification

The sole added executable source is [control-center-handoff-contract.yml](../../.github/workflows/control-center-handoff-contract.yml). Its job has Contents read permission, pinned checkout and Node setup, Node 24, and the existing offline test command. It uses no application secrets, package installation, application transport, artifact upload, or ledger mutation.

```sh
node --test --test-isolation=none --test-reporter=tap tests/handoff/*.test.mjs
```

The local run completed on 2026-10-18 at 06:10:14 UTC with **50 passed, zero failed, skipped, or cancelled**, on Node v24.19.0. [TEST_RESULTS.json](TEST_RESULTS.json) records timestamps and all input hashes; [tests.tap](tests.tap) is the complete run output. This local result does not itself establish a GitHub run. The PR's Checks view supplies the separately attributable remote result.

## Preserved source and evidence

The source baseline is [`08e79156f540e3f869ad0dc2e6209f6e79f52164`](https://github.com/sovereign-codex/Codex-control-center/tree/08e79156f540e3f869ad0dc2e6209f6e79f52164). All original integration files remain unchanged, including the two runtime workflows, five handoff modules, disabled policy, tests, and original evidence package. The 16-file candidate from #21 is also unchanged. The AVOT interoperability fixtures therefore retain their exact historical CCC source pin.

This directory is a new evidence record. It does not overwrite the original candidate's 44-test record or the integration's earlier 50-test record. [SHA256SUMS](SHA256SUMS) covers the new CI file and this evidence package except the checksum file itself; check it from the repository root.

## Coordinated live probe

The fixed request, independent expectation template, five-record readback verifier, and full operations runbook are staged together in **AVOT #18**, under `review/handoff-receipt-probe-001/`. The probe has one explicit caller request ID and a receipt-only payload. It expects two CCC claims, two CCC outcomes, and one AVOT receipt; all three stages retain execution as unverified.

Before activation, both implementations must be installed on their repositories' main branches with disabled policies. #21 must land before #22 is retargeted or verified against main. Merging #22 into its current review-branch base does not deploy the integration. GitHub's [repository-dispatch event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch) uses the default branch; a payload field or historical receiver review pin cannot select a draft workflow.

The remaining live inputs are the three actual dispatch sender IDs, exact enabled policy digests, current runtime credential capability, and a bounded activation authorization. The current policies do not enforce a one-request quota or expiry. The runbook therefore requires an operator-controlled window, one initiating request, no retries or record reclamation, receipt readback, and policy shutdown. These draft changes perform no merge, activation, credential creation, or live dispatch.
