# DCL Compliance Form

The DCL Compliance Form is a standalone sidecar application for collecting private, auditable
compliance metadata before any future publication to DataHub. The current implementation is the
DCL-001 vertical slice: an authorised fixture Business Contact can open one fixture-backed form,
edit Disposal Class, save a shared versioned draft in PostgreSQL, and reload it. Disposal Action is
always derived by the server.

This repository does **not** connect to DataHub. It contains no DataHub token, production endpoint,
production identifier, or metadata mutation capability.

## Current scope

The implemented slice includes:

- a React and TypeScript form route;
- a Spring Boot REST API;
- PostgreSQL persistence managed by Flyway;
- one immutable, explicitly non-production form revision and asset fixture;
- a read-only fixture seed adapter;
- first-open baseline capture and idempotent reopen;
- server-authoritative Disposal Class to Disposal Action derivation;
- optimistic locking for a shared draft;
- server-side fixture authorisation;
- append-only workflow-created and material-draft-saved audit events;
- unit, API, real-PostgreSQL integration, component, and browser tests.

Only `DRAFT` / `NOT_STARTED` is reachable. Submission, review, approval, rejection, publication,
native Change Proposals, Verification Form verification, production OIDC, and live DataHub reads or
writes are deliberately absent.

## Architecture

The product is a modular sidecar with separate presentation, API/application, domain, persistence,
authorisation, and integration concerns:

```text
Browser -> React UI -> Spring Boot API -> workflow domain -> PostgreSQL
                                      -> read-only fixture seed port
```

Private drafts, baselines, versions, and audit events belong to this application's PostgreSQL
database. DataHub integration is behind a narrow read boundary; DCL-001 supplies only a fixture
implementation, with no HTTP client or write port. See
[ADR-0001](docs/architecture/ADR-0001-sidecar-private-drafts.md) for the durable architectural
decision.

The authoritative build packages the compiled React application into the Spring Boot jar, producing
one deployable while retaining separate frontend and backend processes for local development.

## Prerequisites

Run commands from the native WSL checkout at `/home/alanz/compliance_form`.

- Java 21
- Node.js 22.22.0 (recorded in `.nvmrc`)
- npm 11
- Docker with an accessible daemon
- Bash and curl
- Google Chrome for the Playwright browser test

The repository commits a Maven Wrapper configured for Maven 3.9.10, so a separate Maven install is
not required. The first verification run downloads Maven artifacts, npm packages, the PostgreSQL
image, and Testcontainers support images when they are not already cached.

## Run locally

### 1. Start PostgreSQL

The following credentials are local fixture values, not production secrets:

```bash
docker run --detach \
  --name dcl-postgres-local \
  --publish 127.0.0.1:5432:5432 \
  --env POSTGRES_DB=dcl_local \
  --env POSTGRES_USER=dcl_local \
  --env POSTGRES_PASSWORD=dcl_local_only \
  postgres:17.10-alpine3.24
```

Flyway applies the schema automatically when the backend starts against an empty database.

### 2. Start the backend

```bash
export SPRING_PROFILES_ACTIVE=local
export SPRING_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:5432/dcl_local
export SPRING_DATASOURCE_USERNAME=dcl_local
export SPRING_DATASOURCE_PASSWORD=dcl_local_only
./backend/mvnw -f backend/pom.xml spring-boot:run
```

DCL-001 supplies the read-only fixture adapter. The `local` profile additionally installs the fixed
authenticated principal `bcp.alice`. Fixed-principal behavior exists only in that explicit profile;
there is no fixed-user fallback in other profiles.

### 3. Start the frontend

In another WSL shell:

```bash
npm --prefix frontend ci
DCL_BACKEND_URL=http://127.0.0.1:8080 npm --prefix frontend run dev
```

Open:

```text
http://127.0.0.1:5173/compliance-form?assetUrn=urn%3Ali%3Acontainer%3A00000000000000000000000000000001&formKey=dcl.edw.database.fixture
```

The page persistently identifies the data as a local fixture and states that no DataHub changes are
made.

## Database lifecycle

Stop and resume the local fixture database without deleting it:

```bash
docker stop dcl-postgres-local
docker start dcl-postgres-local
```

To deliberately discard the local fixture database, remove its container. This is irreversible for
data stored only in that container:

```bash
docker rm --force dcl-postgres-local
```

The automated integration and browser tests use isolated temporary PostgreSQL containers. Their
containers are removed after each run and do not use or alter `dcl-postgres-local` or any DataHub
container.

## Verification

Run every configured repository gate with one command:

```bash
./scripts/verify.sh
```

This authoritative path installs the locked frontend dependencies and runs backend unit and
real-PostgreSQL integration tests, frontend static checks and component tests, the production
frontend build, and the Playwright browser scenario. GitHub Actions calls the same script.

The underlying commands are also available independently:

```bash
./backend/mvnw -f backend/pom.xml verify
npm --prefix frontend ci
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

The browser test starts its own uniquely named PostgreSQL container, launches the backend with the
local profile, launches Vite on an isolated port, exercises save and refresh, and cleans up only the
resources it created.

## Fixture contract

- Form key: `dcl.edw.database.fixture`
- Form revision: `1`
- Asset: `Fixture EDW Database`
- Asset URN: `urn:li:container:00000000000000000000000000000001`
- Authorised principal: `bcp.alice`
- Classes: `TEST_CLASS_A`, `TEST_CLASS_B`
- Derived actions: `TEST_ACTION_A`, `TEST_ACTION_B`

These values are intentionally unmistakable test fixtures. The Container entity type in this fixture
does not establish the production DataHub entity type.

## Troubleshooting

### Docker or PostgreSQL tests do not start

Confirm that `docker info` succeeds from WSL and that the current user can access
`/var/run/docker.sock`. The first run also needs network access to pull
`postgres:17.10-alpine3.24` and the Testcontainers cleanup image.

### Port 5432 is already in use

Stop the conflicting local service or publish `dcl-postgres-local` on another host port and update
`SPRING_DATASOURCE_URL`. Automated tests use dynamically allocated ports.

### The browser test cannot launch Chrome

Confirm that `google-chrome --version` succeeds in WSL. The Playwright configuration uses the
installed stable Chrome channel rather than downloading a separate browser.

### A save reports a version conflict

Another request saved the shared draft first. Use the page's reload action and then reapply the
change. The application never performs an automatic merge or last-write-wins update.

### The API reports that the database is unavailable

Check the datasource environment variables and `docker logs dcl-postgres-local`. The application
does not fall back to in-memory persistence.

## Documentation and authority

- [DCL-001 approved task](docs/tasks/DCL-001-private-versioned-draft.md) defines this slice.
- [ADR-0001](docs/architecture/ADR-0001-sidecar-private-drafts.md) records its accepted architecture.
- [DataHub target validation](docs/integration/datahub-target-validation.md) is the evidence gate for
  any later integration work.
- [DCL_MVP_Handoff.md](DCL_MVP_Handoff.md) remains contextual planning material for the broader MVP;
  it is not evidence that deferred behavior is implemented.

The authority order is the current user-approved request, `AGENTS.md`, current implementation and
configured verification evidence, maintained architecture/task documentation, and then contextual
planning documents. When documentation and running behavior differ, reconcile the discrepancy
rather than treating an older plan as implemented fact.

