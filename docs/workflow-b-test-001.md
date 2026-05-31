# Workflow B Test 001

Purpose: Validate the governed Request → Attempt → Ledger → Repository lineage for Workflow B.

Status: Diagnostic write only.

Rules:
- No PR opened.
- No merge.
- No branch deletion.
- No unrelated files changed.
- No workflow files changed.
- No repository settings changed.
- No secrets changed.

## Workflow B Test 002

Purpose: Validate controlled modification of an existing Workflow B diagnostic branch.

Result target:
- Existing branch reused.
- Existing diagnostic file modified.
- No new branch created.
- No PR opened.
- No merge performed.
- No unrelated files changed.

Rules:
- Do not create a new branch.
- Do not edit any file except docs/workflow-b-test-001.md.
- Do not open a PR.
- Do not merge.
- Do not delete any branch.
- Do not edit workflow files.
- Do not change repository settings.
- Do not change secrets.
