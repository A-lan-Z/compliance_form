# Compliance Form Project Agent Guide

## Scope

This file applies to the entire repository. The product requirements and MVP architecture are
defined in `DCL_MVP_Handoff.md` until superseded by checked-in implementation documentation.

Follow the user's current request first, then these repository rules. Establish the active branch,
worktree state, and current implementation before interpreting or changing behavior.

## Start Every Task With Context

- Work in the native WSL checkout at `/home/alanz/compliance_form`.
- Inspect `git status --short --branch`, the current commit, and relevant branch divergence.
- Preserve unrelated tracked changes and untracked files. Never clean, reset, overwrite, format,
  stage, or move user work merely to obtain a clean tree.
- Read `DCL_MVP_Handoff.md` and the current branch's README, project configuration, CI workflow,
  implementation, and tests relevant to the task.
- Prefer `git ls-files`, `git grep`, and searches scoped to relevant directories. Avoid scanning
  virtual environments, build output, caches, downloaded runtimes, and dependency trees.

## Implementation Principles

- Do not preserve backward compatibility. Remove obsolete paths instead of adding compatibility
  layers, fallbacks, migrations, aliases, or dual behavior.
- Choose the simplest implementation that fully meets the current requirements. Avoid speculative
  abstractions, configuration, indirection, and extension points.
- Grow the system in layers. Start from the smallest version that works end to end, then add each
  capability on top of a working product.
- Keep components modular and concerns clearly separated.
- Prefer established, well-maintained libraries when they reduce overall complexity or improve
  reliability. Do not reimplement common functionality without a clear reason.
- Use dependencies already present before adding packages or writing custom implementations. Check
  installed documentation, types, and supported APIs before assuming a dependency lacks a feature.
- Make architectural decisions for the long term. Do not introduce deliberate stopgaps intended to
  be replaced later.
- Do not write over-defensive code.
- Do not design around extremely rare edge cases or add extensive logic for cases without
  significant impact. Keep code focused on the main path, with proportionate handling for likely
  or high-impact failures.
- Prefer explicit, readable control flow and data structures over cleverness.
- Keep comments concise and limited to useful local context. Do not write long AI-style comments or
  documentation that reads like an answer to a prompt.
- Do not leave dead code, commented-out alternatives, unused compatibility shims, or TODO-based
  partial implementations after completing a change.

## Architecture and Product Boundaries

- Treat `DCL_MVP_Handoff.md` as the architecture and scope baseline. Implement the defined MVP
  before adding deferred features or generic frameworks.
- Keep frontend presentation, API and domain logic, PostgreSQL persistence, authentication and
  authorization, DataHub integration, publication state, and audit reporting as separate concerns.
- Derive and validate compliance rules on the server. Do not rely on browser-only enforcement for
  authorization, workflow transitions, or derived values.
- Treat malformed input, failed persistence, authorization errors, and failed DataHub reads or
  writes as likely, high-impact failures. Handle them clearly without elaborate recovery systems.
- Preserve workflow invariants, optimistic locking, immutable submission revisions, idempotent
  publication state, and auditable state transitions described in the handoff.

## Security and Sensitive Data

- Never commit credentials, access tokens, database passwords, OIDC client secrets, resolved
  secrets, sensitive form submissions, or production data.
- Keep the DataHub publisher token backend-only and use the narrowest practical service identity.
- Do not log access tokens or full sensitive free-text values.
- Use environment-variable placeholders and the approved secret-management mechanism.

## Development and Verification

- Keep tests close to the behavioral boundary being changed. Start with the smallest relevant test
  selection, then run the repository's complete configured gates before handing off behavioral
  changes.
- Use representative fixtures and fakes for fast feedback, but do not treat mocked tests as final
  proof for persistence, authorization, workflow, or DataHub publication behavior.
- Validate affected end-to-end paths against configured local integration services when available.
  Report exactly which layer could not be checked and what was verified instead.
- Test likely and high-impact failures proportionately. Do not inflate the test suite with obscure
  cases that do not materially improve confidence.
- Do not weaken tests, coverage thresholds, lint rules, type checks, or security checks to make a
  change pass.

## Git and Handoff

- Keep changes narrowly scoped. Do not switch branches, merge, rebase, commit, push, or clean the
  worktree unless the task calls for it.
- Stage only the intended paths; never stage unrelated user work.
- Review the final diff and status, and confirm unrelated files remain intact.
- A completed handoff states what changed, which checks ran, which end-to-end paths were verified,
  and any verification layer that was unavailable.
- Do not claim completion while the requested path is unfinished or known to be broken.
