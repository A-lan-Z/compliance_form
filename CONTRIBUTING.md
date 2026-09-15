# Contributing

Use Python 3.11 and install the development dependencies in a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install '.[dev]'
```

## Making changes

Keep changes focused and preserve unrelated work. Read [README.md](README.md) for the Action's
behavior and [DESIGN.md](DESIGN.md) for its assignment rules and concurrency limits.

Keep event parsing, assignment decisions, and DataHub calls in their existing modules. Remove
obsolete code instead of adding compatibility paths. Cover behavior changes with focused tests,
including failed reads and writes. Record changes to the assignment contract in the design notes.

Never commit credentials, tokens, company data, or sensitive form answers. Configure credentials
through environment variables and the deployment environment's secret manager.

## Running checks

Run the same checks as CI before submitting a change:

```bash
bash scripts/verify.sh
```

This runs unit tests, Ruff lint and formatting checks, a wheel build, and dependency checks.
For changes to Kafka or DataHub interactions, also run the local integration harness against
an isolated test stack using the instructions in [VERIFICATION.md](VERIFICATION.md).

Describe the behavior change, test results, and any integration paths that were not tested in
the pull request. Review the diff and stage only the intended files.
