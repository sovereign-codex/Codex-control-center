# Control Center handoff integration evidence

This directory records the local verification of the disabled workflow integration described in [the integration contract](../../docs/CONTROL_CENTER_HANDOFF_INTEGRATION_001.md).

The original `control-center-handoff-001` candidate remains frozen in PR #21. This follow-on change supplies production preparation, a create-only claim executor, a real GitHub HTTP adapter, and two proposed workflow revisions. The checked-in policy remains disabled and admits no sender. No live transport or receiver completion is established here.

| File | Purpose |
|---|---|
| [TEST_RESULTS.json](TEST_RESULTS.json) | Recorded run, counts, source identities, validation scope, and input hashes. |
| [tests.tap](tests.tap) | Complete final Node test output. |
| [CLI_SMOKE.json](CLI_SMOKE.json) | Four CLI paths checked under the disabled policy with a forbidden-network guard. |
| [SHA256SUMS](SHA256SUMS) | Hashes of all files changed by this integration, except the checksum manifest itself. Paths are relative to repository root. |

Verify the files from repository root before making edits:

```sh
sha256sum -c review/control-center-handoff-integration-001/SHA256SUMS
```

Reproduce the tests on Node 24:

```sh
node --test --test-isolation=none --test-reporter=tap tests/handoff/*.test.mjs
```

The test services and HTTP responses are injected fakes. The production CLI has no fake-transport flag or environment switch. Test results do not prove live GitHub atomicity, current credential scope, sender provenance, receiver compatibility, or institutional acceptance.

The [receiver review](../../docs/CONTROL_CENTER_HANDOFF_RECEIVER_REVIEW.md) explains why AVOT-engine activation remains held. A later review must establish preserved input, attributable receipt, sender policy, and actual ledger behavior before enabling dispatch.
