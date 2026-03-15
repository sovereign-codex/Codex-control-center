
# Codex Control Center

Governance and observability engine for the Codex repository ecosystem.

This repository implements the core runtime that:
- Receives GitHub webhook events
- Analyzes repository purpose and structure
- Runs council debates across AVOT roles
- Produces recommendation artifacts
- Writes decisions back to GitHub via issues and PRs

The runtime typically runs as a GitHub App service that listens for webhook events from repositories it is installed on. GitHub sends webhook POST payloads when events occur, allowing the service to respond programmatically through the GitHub API.
