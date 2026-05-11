# Production-Safe Repository Partitioning Checklist

This document is a checklist of implementation prompts to be executed by AI coding agents.

Each checklist item is intentionally written as an English prompt that can be copied and assigned to an implementation agent.

## Operating Rule For All Prompts

When a prompt says to document all required keys, codes, and passwords, the agent must produce a complete secret inventory that includes exact secret names, exact storage backends, exact injection points, exact retrieval procedures, exact validation commands, exact rotation steps, and exact ownership. The agent must not commit live secret values, private keys, plaintext passwords, or raw production tokens into Git. Instead, the agent must document the source of truth for each secret, such as GitHub Actions secret names, host file paths, password manager entries, or encrypted local stores.

## Practical Execution Order

This section converts the checklist into the actual execution order for the first production split.

The split must not be run as a flat list. It must be run in three operational waves: before the first real cutover, during the first real cutover, and after the first real cutover.

### Decision About The Operational Manual Rewrite

Prompt 6, the rewrite of docs/acesso_repositórios_github.md, is an early pre-cutover task and must happen before production-sensitive repository extraction or deploy activity is delegated broadly to other agents.

However, it is not the very first task.

Prompt 1 must happen first because the operational manual should reflect a verified production baseline, not assumptions. Therefore:

1. Prompt 1 is first.
2. Prompt 6 is second.
3. Prompt 6 should be finished before the team starts executing production-sensitive split work at scale.

### Before The First Real Cutover

These prompts must be completed before any public routing switch or first live split-owned production publish.

1. Prompt 1: Freeze The Current Production Baseline Before Any Split.
Reason: this is the safety anchor for every later decision and rollback.

2. Prompt 6: Review And Rewrite docs/acesso_repositórios_github.md As The Complete Operational Safety Manual.
Reason: after the baseline is frozen, every later agent needs one authoritative manual for safe commit, push, deploy, secrets, and stop conditions.

3. Prompt 2: Add A Deployment Ownership Guard So The Root Repository Cannot Accidentally Overwrite The Split.
Reason: the guard must be implemented before cutover day, even if final activation happens during the cutover window.

4. Prompt 4: Eliminate Data-Loss Risk By Freezing Docker Volume Names And Persisted Storage Ownership.
Reason: the API split must never create fresh-looking storage when ownership moves away from the monolith directory.

5. Prompt 3: Prepare The API Repository As A Fully Standalone Operational Backend.
Reason: the API is the owner of /api, /assets, forms-worker, and Transport AI runtime, so it must be stabilized first.

6. Prompt 5: Implement API Deployment Automation With Full Environment Rehydration, Health Gates, And Rollback.
Reason: the split API must be deployable and reversible before any frontend split can be trusted.

7. Prompt 7: Extract And Deploy The Admin Website As An Independent Static Production Unit.
Reason: this is the lowest-risk frontend split and should happen before the more coupled sites.

8. Prompt 8: Extract And Deploy The Checking Web Application As An Independent Static Production Unit.
Reason: this remains API-dependent but is still less risky than the Transport dashboard.

9. Prompt 9: Extract And Deploy The Transport Dashboard Last, With Explicit AI Compatibility Gates.
Reason: Transport is the highest-risk frontend split because its visible UX depends on backend-owned AI behavior and persisted configuration.

10. Prompt 12: Build The Flutter Repository Pipeline As An Artifact Publication Flow, Not A Website Deploy.
Reason: this can be prepared before cutover, but it is not on the critical path of the first web/API cutover.

11. Prompt 11: Create A Shared Cross-Repository Smoke And Go/No-Go Validation Layer.
Reason: the suite must exist before public cutover so it can be executed immediately after routing changes.

12. Prompt 13: Rehearse Rollback For Every Repository Before Declaring The Split Safe.
Reason: rollback is a precondition for safe cutover, not a post-mortem improvement.

13. Prompt 14: Add A Final Cutover Readiness Gate And Refuse Production Split Until Every Prior Prompt Is Green.
Reason: this is the last pre-cutover decision gate and must be the final item before the live switch.

### During The First Real Cutover

These are not new prompts. They are the live activation order of the already prepared prompts.

1. Re-run the evidence-backed go/no-go decision from Prompt 14 immediately before touching public routing.

2. Activate the ownership switch from Prompt 2 so the root repository cannot silently remain the production deploy owner once the split goes live.

3. Deploy the prepared API split stack from Prompts 3, 4, and 5 into its dedicated remote directory and validate it locally on port 18080 before public routing changes.

4. Deploy the prepared admin, user-web, and transport-web stacks from Prompts 7, 8, and 9 into their dedicated remote directories and validate them locally on ports 18081, 18082, and 18083 before public routing changes.

5. Execute Prompt 10, Implement And Verify The Split Nginx Edge Cutover, only after all split upstreams are already healthy locally.

6. Immediately run Prompt 11, the shared cross-repository smoke suite, against the public URLs after the edge change.

7. If any critical validation fails, execute the correct rollback path from Prompt 13 without continuing the rollout.

### After The First Real Cutover

These prompts remain active as the new steady-state operating model.

1. Prompt 6 remains a living manual and must be updated whenever repository ownership, secret handling, deployment flow, or cutover behavior changes.

2. Prompt 11 becomes mandatory after every production deploy, not only after the first cutover.

3. Prompt 13 remains mandatory as the rollback source of truth for each repository.

4. Prompt 14 should be reused as a recurring readiness gate for any later wave that changes production ownership, routing, secrets, or Transport AI contracts.

5. The root repository must remain outside the normal production publish path except for explicitly documented emergency fallback behavior.

### Hard Ordering Constraints

These constraints are not optional:

1. Prompt 1 must be executed before Prompt 6.

2. Prompt 6 must be executed before broad production-sensitive split implementation, because later agents need one authoritative operational manual.

3. Prompt 10 must not be executed before Prompts 3, 4, 5, 7, 8, and 9 are already green on the split local ports.

4. Prompt 9 must remain after Prompts 3, 5, 7, and 8 because the Transport dashboard is the most coupled frontend.

5. Prompt 14 must be the final gate before the first live public cutover.

## 1. Freeze The Current Production Baseline Before Any Split

```text
You are the implementation agent responsible for creating an immutable production baseline before any repository extraction, workflow split, or deployment ownership change happens.

Your mission is to add the smallest safe amount of code, scripts, and documentation necessary to capture the real current production state and make any future regression objectively measurable.

Work in this order:

1. Audit the current deployment ownership in the root repository.
2. Capture the live edge routing topology that currently serves /api, /assets, /checking/admin, /checking/user, and /checking/transport.
3. Capture the currently running Docker containers, Docker Compose projects, Docker images, named volumes, and relevant environment variables by name.
4. Capture public and local health evidence for API, admin, user, and transport.
5. Capture one explicit Transport AI baseline proving whether the AI runtime is healthy, degraded, or disabled.

Required inputs to inspect:

- .github/workflows/deploy-oceandrive.yml
- deploy/nginx/checking-edge-routes.conf
- deploy/nginx/verify_checking_edge_cutover.sh
- docker-compose.yml
- docker-compose.api.yml
- docker-compose.websites.yml
- sistema/app/core/config.py
- any existing operational runbooks under docs/ and deploy/maintenance/

Implementation requirements:

1. Create a production baseline report under docs/ with a clear file name that indicates this is the pre-split baseline.
2. Create or extend a repeatable capture script under deploy/maintenance/ that gathers the production topology evidence in a deterministic way.
3. Include capture steps for nginx -T, docker ps, docker compose ps, docker volume ls, docker volume inspect for Postgres and event archives, and local curl validation for ports 18080, 18081, 18082, and 18083 where applicable.
4. Record whether production is still using any monolithic upstream on port 8000, any split upstream on ports 18080-18083, or an unsafe mixture of both.
5. Record whether the root repository is still the only deploy owner for production.
6. Record the Transport AI mode, required secret names, and whether the persisted LLM settings dependency is present.
7. Add explicit “stop the rollout” conditions if drift or ambiguity is detected.

Validation requirements:

1. The new report must state the current production topology in one unambiguous sentence.
2. The capture script must be repeatable and safe to run multiple times.
3. The report must contain evidence paths and timestamps.
4. The report must explicitly answer whether the split edge topology is already live on the host.

Do not:

- change production routing yet;
- rotate secrets;
- move repositories yet;
- assume that a versioned nginx file matches the live host without evidence.

Definition of done:

- there is a baseline report, a repeatable evidence capture path, and a clear written decision on whether the host is ready for split ownership work.
```

## 2. Add A Deployment Ownership Guard So The Root Repository Cannot Accidentally Overwrite The Split

```text
You are the implementation agent responsible for preventing the root repository from silently remaining the production owner after the split repositories become active.

Your mission is to make deployment ownership explicit and fail-safe.

Work in this order:

1. Inspect the root production workflow and any other deploy workflows in the root repository.
2. Design a reversible guard that prevents accidental production overwrite from the root repository once the split rollout starts.
3. Implement the guard in code and document the exact activation procedure.

Required inputs to inspect:

- .github/workflows/deploy-oceandrive.yml
- .github/workflows/deploy-oceandrive-api-only.yml
- .github/workflows/deploy-oceandrive-admin-only.yml
- .github/workflows/deploy-oceandrive-user-only.yml
- .github/workflows/deploy-oceandrive-transport-only.yml
- docs/acesso_repositórios_github.md
- docs/temp_015.md

Implementation requirements:

1. Add an explicit production ownership guard to the root deploy workflow. Acceptable patterns include a manual-only trigger after cutover, a required repository variable gate, or a hard fail step when split ownership is enabled.
2. Make the guard default to safety. If ownership is ambiguous, production deploy from the root repository must stop instead of proceeding.
3. Document the exact switch-over procedure, including the point in time when root push-to-main must no longer deploy production.
4. Add a short runbook section explaining how to temporarily re-enable the root workflow for emergency rollback only.
5. Ensure the solution does not break current production before the split is intentionally activated.

Validation requirements:

1. The workflow logic must be readable and explicit.
2. The documentation must explain the pre-cutover state and the post-cutover state.
3. There must be a clear rollback path that does not depend on tribal knowledge.

Do not:

- leave both the root repository and split repositories as concurrent production owners;
- rely on comments alone without executable workflow logic;
- make the rollback path destructive.

Definition of done:

- the root repository can no longer accidentally overwrite split production ownership after the guard is activated, and the activation procedure is documented.
```

## 3. Prepare The API Repository As A Fully Standalone Operational Backend

```text
You are the implementation agent responsible for extracting the backend into the future checking_api repository without losing assets, migrations, forms processing, or Transport AI runtime behavior.

Your mission is to transform the API scope into a self-contained, production-runnable backend package.

Work in this order:

1. Inventory every file required for the backend to run independently.
2. Build the new repository structure so it contains not only sistema/app without static, but also every operational artifact required to build, migrate, run, validate, and roll back.
3. Update the API compose stack so it is operationally equivalent to the existing production backend responsibilities.

Required scope to include:

- sistema/app excluding sistema/app/static
- assets/
- alembic.ini
- alembic/
- requirements.txt
- requirements-dev.txt
- Dockerfile and compose files required for API runtime
- smoke and validation scripts required for API ownership
- backend tests, health tests, forms tests, and Transport AI tests

Critical implementation requirements:

1. The API stack must include api, db, migrate, and forms-worker. Do not drop forms-worker from the split stack.
2. The API stack must preserve /assets ownership.
3. The API runtime must keep SERVE_ADMIN_SITE_IN_API=false, SERVE_USER_SITE_IN_API=false, and SERVE_TRANSPORT_SITE_IN_API=false in the split design.
4. The entrypoint must remain compatible with python -m sistema.app.http_runtime unless there is a strongly justified and fully tested replacement.
5. The repository must be able to bootstrap itself without depending on files that remain only in the root monolith.

Validation requirements:

1. The split API repository must pass targeted backend tests.
2. A local compose run must expose health at /api/health and readiness at /api/health/ready.
3. /assets must still be reachable from the API runtime.
4. forms-worker must be present, healthy, and documented.

Do not:

- assume that “API code only” means “runtime complete”;
- move static frontends into the API repository;
- remove any Transport AI backend contract by accident.

Definition of done:

- the API repository is operationally standalone, not just source-code standalone.
```

## 4. Eliminate Data-Loss Risk By Freezing Docker Volume Names And Persisted Storage Ownership

```text
You are the implementation agent responsible for eliminating the risk that the API split creates new empty-looking Docker volumes when the deployment directory or Compose project name changes.

Your mission is to make persisted storage names stable and explicit before production ownership changes.

Work in this order:

1. Inspect the current Docker Compose files for Postgres and event archive volume declarations.
2. Determine how the current deployment directory and Compose project name affect generated volume names.
3. Implement stable, explicit volume naming for the API split.
4. Document the migration and validation steps so production does not silently bind to a fresh volume.

Required inputs to inspect:

- docker-compose.yml
- docker-compose.api.yml
- any deploy scripts or runbooks that start Compose stacks

Implementation requirements:

1. Introduce explicit, stable volume names for the Postgres data volume and the event archives volume. Use a clear, production-safe naming convention such as checkcheck_pgdata and checkcheck_event_archives, or document a justified equivalent.
2. If external volumes are the safest option, implement them explicitly and document the one-time provisioning path.
3. Update the API deployment logic so the split repository never creates an unintended fresh database volume because the working directory changed from /root/checkcheck to /root/checking_api.
4. Add a validation step that inspects the bound volume names before and after deploy.
5. Add rollback steps that preserve the same volume bindings.

Validation requirements:

1. The compose configuration must show explicit volume ownership.
2. The deployment runbook must instruct the operator to confirm that the expected named volumes are mounted.
3. The solution must preserve the existing database and event archive data path.

Do not:

- rely on implicit Compose-generated volume names;
- rename volumes in production without a documented migration path;
- accept “the app started” as proof that the correct storage was mounted.

Definition of done:

- the API split cannot accidentally point production at new empty persisted storage because of a directory-name or project-name change.
```

## 5. Implement API Deployment Automation With Full Environment Rehydration, Health Gates, And Rollback

```text
You are the implementation agent responsible for creating the production deployment workflow for the future checking_api repository.

Your mission is to make API deployment self-sufficient, reversible, and safe for production.

Work in this order:

1. Use the existing root deployment workflow as the behavioral baseline.
2. Port only the backend-relevant pieces into the split API repository.
3. Add missing safeguards for environment rehydration, named volumes, forms-worker health, and Transport AI smoke validation.

Required secret inventory to document and wire:

- OCEAN_HOST
- OCEAN_USER
- OCEAN_PORT
- OCEAN_SSH_KEY
- OCEAN_HOST_FINGERPRINT
- OCEAN_APP_DIR
- OCEAN_APP_ENV_B64
- CHECKCHECK_API_IMAGE
- COMPOSE_PROJECT_NAME
- CHECKCHECK_PGDATA_VOLUME
- CHECKCHECK_EVENT_ARCHIVES_VOLUME
- any API smoke credentials required for validation

Implementation requirements:

1. Trigger on push to main and workflow_dispatch.
2. Use a dedicated OCEAN_APP_DIR for the API repository.
3. Materialize or refresh .env from OCEAN_APP_ENV_B64 on the host during deploy.
4. Pull and restart db, migrate, api, and forms-worker as appropriate for the API stack.
5. Validate /api/health and /api/health/ready.
6. Validate forms-worker health.
7. Validate at least one Transport AI endpoint and one /assets fetch to prove backend ownership remains intact.
8. Record the deployed release identifier on the host.
9. Add rollback instructions and, when feasible, an automated rollback path to the previously known-good image.
10. Use a concurrency group dedicated to API production deploys.

Validation requirements:

1. A failed deploy must fail loudly before public cutover is assumed complete.
2. The workflow must prove that the host has a .env file, the correct named volumes, and healthy services.
3. The workflow must never rely on an undocumented manual host tweak.

Do not:

- assume .env already exists forever;
- omit forms-worker from post-deploy validation;
- validate only a container start while skipping endpoint health.

Definition of done:

- the API repository can deploy itself to production safely, validate the full backend scope, and roll back in a controlled way.
```

## 6. Review And Rewrite docs/acesso_repositórios_github.md As The Complete Operational Safety Manual

```text
You are the implementation agent responsible for rewriting docs/acesso_repositórios_github.md so it becomes the authoritative operational manual for safe commit, push, deploy, and AI-agent behavior across the current monolith and the future split repositories.

Your mission is to make the document complete enough that another AI agent can execute operational Git and deploy work safely, step by step, without guessing.

This task is mandatory and must be done with production safety in mind.

Required scope for the document:

1. Current repository ownership map for checkcheck, checking_app_flutter, and the future split repositories.
2. Exact conditions under which a push to the root repository triggers production deployment.
3. Exact preflight checks before any stage, commit, or push.
4. Safe PowerShell command sequences for root, Flutter, and any future split repositories.
5. Explicit stop conditions when the repository owner, branch, remote, or deploy ownership is ambiguous.
6. A dedicated section for AI agents describing safe operational behavior, forbidden shortcuts, and required validation steps.
7. A complete credential and secret inventory by identifier, not by plaintext secret value.

The credential and secret inventory section must include all required keys, codes, passwords, and secrets in safe form:

- exact GitHub Actions secret names;
- exact repository variables;
- exact host-side file paths that must exist;
- exact environment variable names required by the API runtime;
- exact Docker image names;
- exact remote directories;
- exact smoke account identifiers and where their passwords are stored;
- exact owner of each credential;
- exact retrieval procedure for each credential;
- exact validation procedure proving the credential is present and correctly wired.

At minimum, document all identifiers related to:

- OCEAN_HOST
- OCEAN_USER
- OCEAN_PORT
- OCEAN_SSH_KEY
- OCEAN_HOST_FINGERPRINT
- OCEAN_APP_DIR
- OCEAN_APP_ENV_B64
- CHECKCHECK_API_IMAGE
- CHECKCHECK_ADMIN_WEB_IMAGE
- CHECKCHECK_USER_WEB_IMAGE
- CHECKCHECK_TRANSPORT_WEB_IMAGE
- COMPOSE_PROJECT_NAME
- CHECKCHECK_PGDATA_VOLUME
- CHECKCHECK_EVENT_ARCHIVES_VOLUME
- DATABASE_URL
- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD
- ADMIN_SESSION_SECRET
- BOOTSTRAP_ADMIN_KEY
- BOOTSTRAP_ADMIN_NAME
- BOOTSTRAP_ADMIN_PASSWORD
- DEVICE_SHARED_KEY
- MOBILE_APP_SHARED_KEY
- PROVIDER_SHARED_KEY
- HERE_API_KEY
- TRANSPORT_AI_ENABLED
- TRANSPORT_AI_AGENT_MODE
- TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY
- TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE
- any smoke-test usernames and password storage references

Security rule:

- Do not commit live secret values, plaintext passwords, private SSH key bodies, or raw production tokens into the document.
- Instead, document the source of truth, the retrieval workflow, the operator with access, and the validation command.

Implementation requirements:

1. Rewrite the document so it is structured by decision point, not by scattered notes.
2. Add a production-safe commit/push/deploy flow for the current root repository.
3. Add a future-state flow for checking_api, checking_admin, checking_webapplication, and checking_transport, clearly marked as inactive until extraction is complete.
4. Add a section explaining that root push-to-main is production-sensitive and why.
5. Add a section explaining how an AI agent must confirm the correct repository owner before staging files.
6. Add a section explaining which secrets exist only as identifiers in documentation and where the live values are stored.
7. Add a final “do not proceed” checklist for ambiguous operational states.

Validation requirements:

1. The document must be actionable without external tribal knowledge.
2. The document must not leak live secrets into version control.
3. A reviewer must be able to follow the document and determine the correct safe path for commit, push, and deploy in the current and future repository topology.

Definition of done:

- docs/acesso_repositórios_github.md becomes the complete operational safety manual, including a full secret inventory by identifier and source-of-truth, while keeping live secret values out of Git.
```

## 7. Extract And Deploy The Admin Website As An Independent Static Production Unit

```text
You are the implementation agent responsible for extracting the admin static site into the future checking_admin repository and deploying it independently without breaking its dependency on the API and shared assets.

Your mission is to create a safe first frontend split with the lowest possible behavioral risk.

Work in this order:

1. Extract the admin frontend scope and only the operational files it needs.
2. Create a self-contained static-site Docker image and Compose stack.
3. Add deploy automation, local smoke validation, and public smoke validation.
4. Verify that the admin site still talks to /api and /assets correctly.

Required inputs to inspect:

- sistema/app/static/admin/
- deploy/docker/Dockerfile.admin-web
- deploy/nginx/static-site.conf
- docker-compose.websites.yml
- any admin smoke or browser validation helpers already in the repository

Implementation requirements:

1. The new repository must contain only the admin static site and the minimum operational files required to build and deploy it.
2. The deploy directory on the host must be dedicated to checking_admin.
3. The deploy workflow must build and publish a dedicated admin image.
4. The deploy workflow must validate local port 18081 and the public /checking/admin URL.
5. The validation must prove the page shell loads and that requests to /api and /assets still succeed.

Validation requirements:

1. The independent admin deploy must not require an API redeploy when no backend contract changed.
2. The admin site must still work against the API repository as the backend owner.
3. The public route must match the split edge topology.

Do not:

- duplicate backend assets into the admin repository beyond what the static shell truly owns;
- change public URL shapes unnecessarily;
- deploy into a shared rsync target with another repository.

Definition of done:

- checking_admin can be built, deployed, validated, and rolled back independently.
```

## 8. Extract And Deploy The Checking Web Application As An Independent Static Production Unit

```text
You are the implementation agent responsible for extracting the Checking Web frontend into the future checking_webapplication repository and deploying it independently without breaking its dependency on the API and shared assets.

Your mission is to create the user-web split with the same safety standards used for the admin split.

Work in this order:

1. Extract the static frontend scope and its minimum operational files.
2. Create a self-contained static-site Docker image and Compose stack.
3. Add deploy automation, local smoke validation, and public smoke validation.
4. Verify that the web app still talks to /api/web and /assets correctly.

Required inputs to inspect:

- sistema/app/static/check/
- deploy/docker/Dockerfile.user-web
- deploy/nginx/static-site.conf
- docker-compose.websites.yml
- any user-web smoke validation helpers already in the repository

Implementation requirements:

1. The new repository must contain only the user-web static site and the operational files required to build and deploy it.
2. The deploy directory on the host must be dedicated to checking_webapplication.
3. The deploy workflow must build and publish a dedicated user-web image.
4. The deploy workflow must validate local port 18082 and the public /checking/user URL.
5. The validation must prove the page shell loads and that requests to /api/web and /assets still succeed.

Validation requirements:

1. The independent user-web deploy must not require an API redeploy when no backend contract changed.
2. The public route must match the split edge topology.
3. The smoke validation must fail if the page shell loads but the backend dependencies are broken.

Do not:

- assume shell HTML is enough proof of correctness;
- deploy into a shared remote directory;
- change route prefixes without explicit migration planning.

Definition of done:

- checking_webapplication can be built, deployed, validated, and rolled back independently.
```

## 9. Extract And Deploy The Transport Dashboard Last, With Explicit AI Compatibility Gates

```text
You are the implementation agent responsible for extracting the Transport dashboard into the future checking_transport repository and deploying it independently without breaking Transport AI behavior.

This is the highest-risk frontend split. Treat this task as production-sensitive.

Your mission is to split the static Transport shell while preserving the backend API as the owner of Transport AI runtime, persisted settings, encryption behavior, and approval gates.

Work in this order:

1. Extract the static dashboard scope and only the operational files it needs.
2. Preserve existing API and assets URL assumptions unless there is an approved migration.
3. Add contract-aware validation that blocks a dashboard deploy if the current API does not satisfy the dashboard’s expectations.
4. Add dedicated Transport AI smoke validation before the deploy is considered healthy.

Required inputs to inspect:

- sistema/app/static/transport/
- sistema/app/static/transport/app.js
- deploy/docker/Dockerfile.transport-web
- deploy/nginx/static-site.conf
- docker-compose.websites.yml
- Transport AI backend routes and tests in the backend scope
- any existing browser tests or transport page tests

Critical implementation requirements:

1. Keep the dashboard dependent on /api/transport, /api/transport/ai, and /assets, unless a separate approved migration explicitly changes those paths.
2. Add a compatibility gate that fails deployment if the dashboard requires a backend contract that the live API does not yet expose.
3. Add post-deploy validation for local port 18083 and the public /checking/transport URL.
4. Add authenticated smoke validation for the dashboard.
5. Add Transport AI smoke validation that verifies settings retrieval, route calculation flow or equivalent safe diagnostic flow, status polling, and visible error handling.
6. Ensure the workflow surfaces failures such as missing persisted LLM settings, missing HERE API key, missing approval evidence, or encryption-key mismatches.
7. Document the mandatory deployment order when both API and dashboard contracts change: API first, dashboard second, removal of old contracts only in a later wave.

Validation requirements:

1. The workflow must fail if the dashboard loads but Transport AI is functionally broken.
2. The workflow must prove that the split dashboard still works against the live API owner.
3. The rollback procedure must be documented and must support rolling back only the dashboard when the backend remains healthy.

Do not:

- move Transport AI backend logic into the dashboard repository;
- rotate TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY during the same rollout window;
- publish a dashboard that requires an unshipped backend contract.

Definition of done:

- checking_transport can be deployed independently while preserving the API as the owner of Transport AI runtime and configuration.
```

## 10. Implement And Verify The Split Nginx Edge Cutover

```text
You are the implementation agent responsible for making the split edge routing real, verifiable, and version-controlled on the production host.

Your mission is to eliminate ambiguity between the monolithic upstream and the split upstream topology.

Work in this order:

1. Compare the live host nginx configuration with the versioned split edge configuration.
2. Reconcile any drift.
3. Apply the split edge routing in a controlled way.
4. Add verification that proves the public routes now map to the intended split ports.

Required inputs to inspect:

- deploy/nginx/checking-edge-routes.conf
- deploy/nginx/checking-edge-http.conf if applicable
- deploy/nginx/verify_checking_edge_cutover.sh
- any existing nginx management or capture scripts under deploy/nginx/ and deploy/maintenance/

Implementation requirements:

1. Ensure /api and /assets route to 127.0.0.1:18080.
2. Ensure /checking/admin routes to 127.0.0.1:18081.
3. Ensure /checking/user routes to 127.0.0.1:18082.
4. Ensure /checking/transport routes to 127.0.0.1:18083.
5. Add or update a cutover script that validates nginx syntax before reload.
6. Add or update a verification script that checks both local upstreams and public URLs.
7. Document the exact rollback path back to the last known-good edge configuration.

Validation requirements:

1. The verification script must fail if any public route still points to the wrong upstream.
2. The public routes and local ports must agree.
3. The final report must explicitly state that production no longer depends on the monolithic upstream path for these routes.

Do not:

- assume the versioned nginx file is already live;
- reload nginx without a syntax check;
- treat a partial cutover as acceptable.

Definition of done:

- production routing is explicitly on the split topology and verifiably matches the versioned configuration.
```

## 11. Create A Shared Cross-Repository Smoke And Go/No-Go Validation Layer

```text
You are the implementation agent responsible for creating the final validation layer that proves the split system works as one production surface even when each repository deploys independently.

Your mission is to prevent false-positive deploys where one component is green in isolation but the public system is broken.

Work in this order:

1. Inventory existing smoke scripts and health checks.
2. Create a shared cross-repository smoke suite that can be run after any repository deploy.
3. Define go/no-go failure criteria that block rollout completion.

Required coverage:

1. GET /api/health
2. GET /api/health/ready
3. public /checking/admin
4. public /checking/user
5. public /checking/transport
6. asset retrieval from /assets
7. at least one authenticated admin path or equivalent admin shell dependency
8. at least one user-web path or equivalent core user flow dependency
9. at least one Transport dashboard authenticated path
10. at least one Transport AI diagnostic or smoke path

Implementation requirements:

1. The smoke suite must be runnable after API deploys and after static-site deploys.
2. The smoke suite must clearly identify which repository likely caused a failure.
3. The smoke suite must fail if public routing, backend health, assets, or Transport AI behavior is broken.
4. The smoke suite must produce concise evidence suitable for deployment logs and longer evidence suitable for a runbook.

Validation requirements:

1. The suite must be documented.
2. The suite must use stable test accounts or stable diagnostics.
3. The suite must become a required post-deploy gate for the split rollout.

Do not:

- validate only container readiness;
- skip Transport AI coverage;
- leave failure triage entirely manual.

Definition of done:

- after any deploy, the team has one shared go/no-go layer that proves the production surface still works end to end.
```

## 12. Build The Flutter Repository Pipeline As An Artifact Publication Flow, Not A Website Deploy

```text
You are the implementation agent responsible for hardening the checking_app_flutter repository as an independent mobile artifact pipeline.

Your mission is to separate the Flutter repository operationally without pretending it owns the production web/API surface.

Work in this order:

1. Confirm the Flutter repository ownership and scope.
2. Add CI for analysis, tests, and builds.
3. Add a deploy workflow that publishes artifacts to a dedicated remote directory on the DigitalOcean host.
4. Add manifest and checksum generation so builds are auditable.

Required implementation requirements:

1. Run flutter analyze.
2. Run flutter test.
3. Build flutter build apk --debug.
4. Build flutter build appbundle --release.
5. Upload the artifacts to a dedicated remote path such as /root/checking_app_flutter_artifacts.
6. Publish a manifest containing repository SHA, build timestamp, artifact file names, and checksums.
7. Maintain a latest pointer only after a successful upload.

Validation requirements:

1. The workflow must prove the artifacts exist remotely after upload.
2. The workflow must not touch API, nginx, or the website deployment stack.
3. The release manifest must be deterministic and auditable.

Do not:

- claim that this pipeline deploys the public website;
- share the remote directory with any website or API repository;
- skip artifact integrity validation.

Definition of done:

- checking_app_flutter becomes an independent, auditable mobile artifact pipeline.
```

## 13. Rehearse Rollback For Every Repository Before Declaring The Split Safe

```text
You are the implementation agent responsible for making rollback a first-class deliverable for the split architecture.

Your mission is to ensure that no repository gains production deploy rights until its rollback path has been implemented, documented, and rehearsed.

Work in this order:

1. Define rollback for checking_api.
2. Define rollback for checking_admin.
3. Define rollback for checking_webapplication.
4. Define rollback for checking_transport.
5. Define rollback for checking_app_flutter artifacts.
6. Add explicit host-side markers for last-known-good release identifiers.

Required implementation requirements:

1. API rollback must preserve the same database and event archive volumes.
2. API rollback must include api and forms-worker together when they are coupled to the same release.
3. Static-site rollback must support rolling back a single site without forcing API rollback.
4. Transport rollback must distinguish “UI-only rollback” from “paired UI/API rollback” when contract mismatches exist.
5. Flutter rollback must support re-pointing the latest artifact pointer.
6. Each rollback path must list the exact commands, expected evidence, and post-rollback smoke tests.

Validation requirements:

1. Rollback instructions must be executable by another engineer or AI agent.
2. Each rollback must include a verification section proving the service is healthy again.
3. Rollback documentation must identify the data that must never be replaced during rollback, especially database volumes and Transport AI encryption state.

Do not:

- describe rollback only at a high level;
- rely on memory for last-good release selection;
- change secrets during rollback.

Definition of done:

- every repository has a documented and testable rollback path before it is considered safe for independent production deploys.
```

## 14. Add A Final Cutover Readiness Gate And Refuse Production Split Until Every Prior Prompt Is Green

```text
You are the implementation agent responsible for creating the final go/no-go gate that decides whether the repository partition is safe to activate in production.

Your mission is to ensure the split does not become “partially live” with unresolved ownership, missing secrets, broken routing, or degraded Transport AI behavior.

Work in this order:

1. Aggregate the outputs of all previous prompts.
2. Build a final readiness checklist under docs/ that is written for operators and AI agents.
3. Make the readiness gate objective, binary, and evidence-backed.

The final readiness gate must block production cutover if any of the following is true:

1. the live nginx topology is still ambiguous or mixed;
2. the root repository can still accidentally deploy production by push when split ownership is active;
3. the API split still lacks explicit named volumes;
4. forms-worker is not included or not healthy in the API split;
5. any repository still shares a remote directory with another repository;
6. docs/acesso_repositórios_github.md is incomplete or still relies on tribal knowledge;
7. the Transport dashboard split lacks AI compatibility gates or AI smoke validation;
8. rollback paths are missing or untested;
9. the cross-repository smoke suite is not green;
10. credential ownership and retrieval paths are undocumented.

Validation requirements:

1. The readiness report must cite evidence for every gate.
2. The readiness report must name the blocking issue, the owner, and the next required action when the gate is red.
3. The readiness report must state, in one final summary sentence, whether production cutover is approved or rejected.

Do not:

- approve cutover because the code “looks ready”;
- ignore missing evidence;
- wave through ambiguous secret handling.

Definition of done:

- there is one explicit production cutover decision backed by evidence, and no split activation happens until the gate is green.
```