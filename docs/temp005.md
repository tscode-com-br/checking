# Fire-and-Poll Architecture for Transport AI Route Calculations

## Context

The Transport AI route calculation feature (`POST /api/transport/ai/route-calculations`) currently
runs the entire AI agent synchronously inside the HTTP request. The request only completes — and
the HTTP response is only sent — after the agent has finished (which can take anywhere from 2 to
30+ minutes). This causes severe problems:

- **Browsers** close idle connections after 2–5 minutes regardless of server-side timeouts.
- **Mobile networks and proxies** drop long-lived TCP connections unpredictably.
- **nginx** enforces `proxy_read_timeout`; even at 1860 s, a 100-user simultaneous test may
  exhaust this.
- **When the client gets a 504**, the agent is still running in the background but the client has
  no way to reconnect and learn the result.
- **With 100 simultaneous users**, Python's default thread pool (~6 threads) queues most requests,
  so users at the back of the line wait 80+ minutes before their calculation even starts.

The solution is the **fire-and-poll pattern**:

1. `POST /api/transport/ai/route-calculations` does all the fast setup work (validate, check
   concurrency, capture baseline, reset passengers, build planning input) and returns
   **HTTP 202 Accepted** in under 5 seconds, carrying the `run_key`.
2. The actual AI agent execution happens in a **background thread** with its own database session.
3. The client **polls** `GET /api/transport/ai/route-calculations/{run_key}` every few seconds.
   This endpoint already exists and already returns the run status. Polling continues until
   `suggestion_ready: true` or an error state.

The polling infrastructure already exists in both the backend (`GET /route-calculations/{run_key}`
at `sistema/app/routers/transport_ai.py:3332`) and the frontend (`pollAiRouteRun()` at
`sistema/app/static/transport/app.js:9590`). This plan wires them together correctly.

---

## Architecture: Before and After

### Before (synchronous)

```
Browser                nginx              FastAPI (1 thread)        AI Agent
  |                      |                      |                       |
  |-- POST /route-calc -->|-- forward ---------->|                       |
  |                      |                      |-- run_agent() ------->|
  |                      |                      |   (blocks 2-30 min)   |
  |                      |                      |<-- result ------------|
  |<-- 504 (timeout) ----|                      |                       |
  |    (client lost)     |<-- HTTP 201 ---------|  (too late, dropped)  |
```

### After (fire-and-poll)

```
Browser                nginx              FastAPI (request thread)   Background thread
  |                      |                      |                         |
  |-- POST /route-calc -->|-- forward ---------->|                         |
  |                      |                      |-- setup (< 5 s) ------->|  thread spawned
  |<-- HTTP 202 ---------|<-- HTTP 202 ----------|                         |
  |   { run_key: "..." } |                      |                         |-- run_agent()
  |                      |                      |                         |   (runs freely)
  |-- GET /route-calc/{key} every 5 s --------->|                         |
  |<-- { status: "running", suggestion_ready: false } -------------------|
  |-- GET /route-calc/{key} (again) ----------->|                         |
  |<-- { status: "proposed", suggestion_ready: true } --- (AI done) -----|
  |   (open review modal)
```

---

## Codebase Reference Map

Before reading the implementation steps, keep these locations in mind:

| What | File | Line |
|---|---|---|
| POST endpoint `start_transport_ai_route_calculation` | `sistema/app/routers/transport_ai.py` | 3875 |
| GET status endpoint `get_transport_ai_route_calculation_status` | `sistema/app/routers/transport_ai.py` | 3332 |
| `run_transport_ai_agent()` (sync AI runner) | `sistema/app/services/transport_ai_agent.py` | 2364 |
| `count_transport_ai_active_runs()` (concurrency check) | `sistema/app/services/transport_ai_runtime.py` | 758 |
| `SessionLocal` and `get_db()` | `sistema/app/database.py` | 422 / 495 |
| `TransportAIRun` model (all columns, status enum) | `sistema/app/models.py` | 420 |
| `TransportAgentRunStartResponse` schema | `sistema/app/schemas.py` | 1965 |
| `TransportAgentRunStatusResponse` schema | `sistema/app/schemas.py` | (near 1965) |
| `Settings` / transport_ai_* settings | `sistema/app/core/config.py` | 62 |
| Frontend: `requestAiRoutes()` | `sistema/app/static/transport/app.js` | ~9669 |
| Frontend: `pollAiRouteRun()` | `sistema/app/static/transport/app.js` | 9590 |
| Frontend: `shouldContinuePollingAiRouteRun()` | `sistema/app/static/transport/app.js` | ~9620 |
| Frontend: `hasRenderableTransportAiReview()` | `sistema/app/static/transport/app.js` | ~9650 |

---

## Current Endpoint Flow (detailed)

`start_transport_ai_route_calculation` (lines 3875–4268) executes in this order:

### SETUP PHASE (fast, ~1–5 s) — stays in the HTTP request

1. **Runtime preflight** (line ~3880): Validates global Transport AI config. Returns `409` if not ready.
2. **Concurrency check** (line ~3892): Queries `TransportAIRun` for rows with
   `status IN ('requested', 'baseline_saved', 'passengers_reset', 'running')`. Returns `409` if
   count ≥ `settings.transport_ai_max_concurrent_runs`.
3. **Actor resolution** (line ~3909): Gets or creates the admin user record for audit trail.
4. **Settings and scope resolution** (line ~3915): Fetches transport pricing settings, resolves
   project names from `payload.dashboard_scope`.
5. **TransportAIRun creation** (line ~3924): Inserts a new `TransportAIRun` with
   `status="requested"`, `run_key="transport-ai-run:{uuid}"`, service_date, route_kind, LLM model,
   etc. Calls `db.flush()` so the row gets an `id` (not yet committed).
6. **Lifecycle event** (line ~3971): Records a `run_created` event in the audit trail.
7. **Baseline capture** (line ~3987): Snapshots current transport state (vehicle assignments,
   passenger assignments) into the run's `baseline_snapshot_json` / `baseline_assignments_json`
   columns. Transitions run status to `"baseline_saved"`.
8. **Passenger reset** (line ~4015): Resets affected transport requests to pending status.
   Transitions run status to `"passengers_reset"`. Returns `500` on failure.
9. **Planning input build** (line ~4067): Builds the planning problem description, resolves LLM
   runtime settings, validates input, saves `planning_input_json` and `planning_input_hash` to run.
10. **Validation check** (line ~4140): Checks for blocking validation issues or empty request set.
    On failure: restores baseline, returns `409`.

### EXECUTION PHASE (slow, 2–30+ min) — must move to background thread

11. **Agent execution** (line ~4186): Calls `run_transport_ai_agent(db=db, run=run, ...)`.
    This is the long-running part. Inside it, run status transitions to `"running"` and eventually
    to `"proposed"` (success) or `"failed"`.
12. **Suggestion creation** (line ~4221): Creates a `TransportAISuggestion` row (`status="shown"`).
13. **Event emission** (line ~4232): Calls `notify_admin_data_changed()` and
    `emit_transport_reevaluation_event()` to push SSE updates.
14. **Commit** (line ~4258): Single `db.commit()` — commits everything at once.
15. **Response** (line ~4260): Returns `HTTP 201` with `TransportAgentRunStartResponse`.

---

## Implementation Plan

### Step 1 — Create `_execute_transport_ai_run_in_background()`

**File:** `sistema/app/routers/transport_ai.py`

Extract the execution phase (steps 11–15 above) into a new private function that:

- Accepts `run_key: str` and `settings_obj: Settings`.
- Opens its own `db = SessionLocal()` session (NEVER reuses the request session — it will be
  closed by the time this thread runs).
- Loads the `TransportAIRun` row by `run_key`.
- Calls `run_transport_ai_agent(db=db, run=run, settings_obj=settings_obj)`.
- On success: creates the `TransportAISuggestion`, emits SSE events, commits.
- On agent failure: marks run as `"failed"`, saves `error_code` / `error_message`, attempts
  baseline restoration, commits.
- On unexpected exception: rolls back, marks run as `"failed"` in a separate transaction, commits,
  logs full traceback.
- Always: closes the session in a `finally` block.

The function signature:

```python
def _execute_transport_ai_run_in_background(run_key: str, settings_obj: Settings) -> None:
```

### Step 2 — Modify `start_transport_ai_route_calculation`

**File:** `sistema/app/routers/transport_ai.py` (lines 3875–4268)

After the validation check at step 10 passes (currently line ~4184), instead of calling
`run_transport_ai_agent()`:

1. Call `db.commit()` — persists all setup changes (run record, baseline, resets, planning input).
   This is crucial: the background thread opens a new session, so the data must be committed
   before the thread starts or it will not see the rows.
2. Spawn a `threading.Thread` targeting `_execute_transport_ai_run_in_background`, passing
   `run.run_key` and `settings`. Set `daemon=True` so the thread doesn't block server shutdown.
   Give it a descriptive name like `f"transport-ai-{run.run_key}"`.
3. Call `thread.start()`.
4. Build and return an **HTTP 202 Accepted** response using the existing
   `_build_transport_ai_start_response()` helper, with:
   - `ok=True`
   - `run_key=run.run_key`
   - `suggestion_key=None` (not created yet)
   - `suggestion_ready=False`
   - `status_value=run.status` (will be `"passengers_reset"` at this point)
   - A user-facing message indicating the calculation has started and results will be ready shortly.

Change the HTTP status code from `201 Created` to `202 Accepted` by wrapping the response in a
`JSONResponse(status_code=202, content=...)` or by using a `Response` with `status_code=202`.

### Step 3 — Verify the GET status endpoint handles all intermediate statuses

**File:** `sistema/app/routers/transport_ai.py` (lines 3332–3361)

`get_transport_ai_route_calculation_status` is called by the client every few seconds. It must
return a clean, predictable response for ALL possible run statuses:

| Run status | Expected `suggestion_ready` | Expected `review_state` |
|---|---|---|
| `requested` | `false` | `unavailable` |
| `baseline_saved` | `false` | `unavailable` |
| `passengers_reset` | `false` | `unavailable` |
| `running` | `false` | `unavailable` |
| `proposed` | `true` | `review_ready` or `review_with_exceptions` |
| `failed` | `false` | `fatal_error` |
| `cancelled` | `false` | `unavailable` |

Review the function to ensure it does not raise an exception or return malformed data for
`"requested"`, `"baseline_saved"`, or `"passengers_reset"` statuses. These are new intermediate
states that were previously invisible to the client (the endpoint never returned while the run was
in these states).

### Step 4 — Update the frontend POST handler

**File:** `sistema/app/static/transport/app.js` — function `requestAiRoutes()` (~line 9669)

Currently this function `await`s the POST, receives a fully completed response (`status="proposed"`,
`suggestion_ready=true`), and either opens the review modal immediately or polls.

After the backend change, the POST returns in seconds with `status="passengers_reset"` and
`suggestion_ready=false`. The frontend must:

1. Accept HTTP `202` as a success response (not an error). Currently it may only treat `200`/`201`
   as success.
2. Extract `run_key` from the response body.
3. Immediately call `pollAiRouteRun(run_key)` to begin the polling cycle.
4. Show a **persistent "calculating" UI state** so the user knows the AI is working. This state
   must persist across the entire polling cycle (minutes), not just while the POST is in flight.

### Step 5 — Update the frontend polling to show status-aware progress

**File:** `sistema/app/static/transport/app.js` — functions near lines 9590–9667

The existing `pollAiRouteRun()` already handles the success and failure cases. Verify and extend:

1. `shouldContinuePollingAiRouteRun(response)` must return `true` for statuses
   `"requested"`, `"baseline_saved"`, `"passengers_reset"`, and `"running"`.
2. Show a user-facing label that reflects the current status, e.g.:
   - `"requested"` / `"baseline_saved"` / `"passengers_reset"` → "Preparando..."
   - `"running"` → "Calculando rotas..."
   - Completion → opens review modal.
3. Confirm that `hasRenderableTransportAiReview(response)` returns `true` only when
   `suggestion_ready === true` and `review_state` is `"review_ready"` or
   `"review_with_exceptions"`.
4. Confirm error handling: when `status === "failed"`, polling stops and the UI shows the
   `error_code` / `message` from the response.

### Step 6 — Handle the "calculating" persistent UI state

**File:** `sistema/app/static/transport/app.js` and `sistema/app/static/transport/index.html`

Currently the loading indicator is shown only while the POST request is in flight. After the change,
the loading state must survive the POST response and persist during the polling cycle.

- Introduce (or reuse) a state variable like `state.aiRouteRunKey` that is set when the 202
  response is received and cleared when polling ends (success or failure).
- The "Calcular Rotas" button should be disabled and show a spinner/label while
  `state.aiRouteRunKey` is set.
- On page reload or navigation away: the `state.aiRouteRunKey` is lost, but the run continues in
  the background. The user can check the status by returning to the page — the existing
  "latest suggestion" logic (`GET /suggestions/latest`) may handle this.

---

## Critical Implementation Details

### Database session isolation (most important)

The request-scoped `db` session is created by `get_db()` and **closed automatically when the
request returns**. The background thread MUST NOT use this session after the request completes.

```python
# WRONG — session will be closed before the thread uses it
thread = threading.Thread(target=lambda: run_agent(db=db, run=run))

# RIGHT — thread creates its own session
def _execute_transport_ai_run_in_background(run_key: str, ...) -> None:
    db = SessionLocal()          # new, independent session
    try:
        run = db.query(TransportAIRun).filter_by(run_key=run_key).first()
        ...
    finally:
        db.close()               # always closed, even on exception
```

### Commit before spawning the thread

The background thread's new session will only see data that has been committed. If the endpoint
spawns the thread before calling `db.commit()`, the thread will open its session, query for the
run by `run_key`, and find nothing.

```python
# Correct order in the endpoint:
db.commit()                      # 1. persist setup work
thread = threading.Thread(...)   # 2. create thread
thread.start()                   # 3. start thread
return JSONResponse(status_code=202, ...)  # 4. return to client
```

### Error handling in the background thread

The background thread must be fault-tolerant. Any unhandled exception must:

1. Roll back the current transaction.
2. Open a **fresh mini-transaction** to mark the run as `"failed"` with a generic `error_code`.
3. Log the full traceback.
4. Not crash the entire server process.

```python
def _execute_transport_ai_run_in_background(run_key: str, settings_obj: Settings) -> None:
    db = SessionLocal()
    try:
        run = db.query(TransportAIRun).filter_by(run_key=run_key).first()
        if run is None:
            logger.error("Background thread: run_key %s not found", run_key)
            return
        # ... agent execution ...
        db.commit()
    except Exception:
        logger.error("Background transport AI run failed: %s", run_key, exc_info=True)
        db.rollback()
        try:
            run.status = "failed"
            run.error_code = "transport_ai_agent_execution_failed"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            logger.error("Could not mark run as failed: %s", run_key, exc_info=True)
    finally:
        db.close()
```

### Thread naming and daemon flag

```python
thread = threading.Thread(
    target=_execute_transport_ai_run_in_background,
    args=(run.run_key, settings),
    daemon=True,                   # does not block clean server shutdown
    name=f"transport-ai-{run.run_key}",  # visible in thread dumps / logs
)
thread.start()
```

`daemon=True` means if Gunicorn restarts a worker, the thread is killed. This is acceptable:
the run will remain in `"running"` status in the database. A future admin operation or server
restart can detect and mark stale `"running"` runs as `"failed"`.

### HTTP 202 vs HTTP 201

The POST endpoint currently returns `HTTP 201 Created`. In the fire-and-poll pattern, the resource
(the `TransportAISuggestion`) has NOT been created yet — only the `TransportAIRun` has been
created. `HTTP 202 Accepted` is the semantically correct status: "the request has been accepted
for processing, but processing has not been completed."

The existing `TransportAgentRunStartResponse` schema already accommodates this:
- `ok: bool` → `True`
- `run_key: str` → the run key (so client can poll)
- `suggestion_key: str | None` → `None` (not created yet)
- `suggestion_ready: bool` → `False`
- `status: str | None` → `"passengers_reset"` (the status at handoff)
- `message: str` → user-facing "calculating" message

No new schema is needed.

### Nginx timeouts after this change

After this change, the POST request returns in under 5 seconds. The `proxy_read_timeout 1860s`
configured for `/api/transport/ai/route-calculations` in
`deploy/nginx/checking-edge-routes.conf` is now irrelevant for the POST (it completes in seconds).
The GET polling endpoint (`/api/transport/ai/route-calculations/{run_key}`) is served by the
generic `/api/` location with `proxy_read_timeout 60s`, which is perfectly sufficient for a
sub-second status query. No nginx changes are needed.

---

## AI Agent Implementation Prompts

The following prompts are self-contained instructions for an AI coding agent to implement each
step of the plan. Each prompt includes all the context the agent needs.

---

### PROMPT 1 — Create the background execution function

```
You are implementing the fire-and-poll conversion for the Transport AI route calculation feature
in a FastAPI application. Your task in this prompt is ONLY to create the background execution
function. Do not modify the existing endpoint yet.

## What you are building

Create a new private function `_execute_transport_ai_run_in_background(run_key: str, settings_obj: Settings) -> None`
in `sistema/app/routers/transport_ai.py`.

This function will be called in a background thread after the HTTP request has already returned
a 202 Accepted response. It must create its own database session, load the TransportAIRun by
run_key, execute the AI agent, handle the result, and always close the session when done.

## Why a new session is mandatory

The request that spawns this thread has already returned and the request-scoped database session
(`db`) has been closed by the FastAPI dependency injection system. If this function tried to reuse
that session, it would get errors like "Session is closed" or data integrity violations.

The `SessionLocal` class (at `sistema/app/database.py:422`) is the SQLAlchemy sessionmaker
configured for this application. Import it at the top of the router file if not already imported:
`from sistema.app.database import SessionLocal`

## What currently happens in the endpoint (lines 4186–4268 of transport_ai.py)

After the setup phase completes, the endpoint currently:
1. Calls `run_transport_ai_agent(db=db, run=run, settings_obj=settings_obj)` — this is the slow
   AI computation that takes 2–30+ minutes. It modifies `run.status` to "running" then to
   "proposed" (success) or "failed". It returns a `TransportAIAgentRunResult` dataclass.
2. If the result has an error: restores baseline via helper functions, marks run as failed.
3. If the result is successful: creates a `TransportAISuggestion` row, emits SSE events via
   `notify_admin_data_changed()` and `emit_transport_reevaluation_event()`.
4. Calls `db.commit()` to persist everything.

Your new function must replicate this logic exactly, using the new session instead of `db`.

## Exact implementation requirements

```python
def _execute_transport_ai_run_in_background(run_key: str, settings_obj: Settings) -> None:
    """
    Executes the Transport AI agent for an already-set-up run.
    Must be called in a background thread. Creates its own DB session.
    """
    db = SessionLocal()
    try:
        # 1. Load the run. It must exist and be in "passengers_reset" status.
        run = db.query(TransportAIRun).filter(TransportAIRun.run_key == run_key).first()
        if run is None:
            logger.error(
                "transport_ai_background: run not found for run_key=%s", run_key
            )
            return

        # 2. Execute the AI agent (slow — 2 to 30+ minutes).
        #    This call internally changes run.status to "running" (at start) and
        #    to "proposed" or "failed" (at end). It uses the db session we pass.
        agent_result = run_transport_ai_agent(
            db=db,
            run=run,
            settings_obj=settings_obj,
        )

        # 3. Handle the result.
        #    Copy the logic that currently lives in start_transport_ai_route_calculation
        #    after the run_transport_ai_agent() call (lines 4190–4258 of transport_ai.py).
        #    This includes:
        #    - Checking agent_result.error_code: if set, mark run as failed,
        #      restore baseline, set error_code and error_message on run.
        #    - If successful: create TransportAISuggestion, link it to the run,
        #      call notify_admin_data_changed() and emit_transport_reevaluation_event().
        #    - Call db.commit() once at the end.
        #
        #    Do NOT return a JSONResponse here — this is not an HTTP handler.
        #    All side effects are through the database and SSE events.

        # [Copy the relevant logic from lines 4190–4258 here, replacing `db` with the
        # local db variable — it's the same name so no rename is needed.]

    except Exception:
        logger.error(
            "transport_ai_background: unhandled exception for run_key=%s",
            run_key,
            exc_info=True,
        )
        db.rollback()
        # Attempt to mark the run as failed in a fresh mini-transaction.
        try:
            run_to_fail = (
                db.query(TransportAIRun)
                .filter(TransportAIRun.run_key == run_key)
                .first()
            )
            if run_to_fail is not None and run_to_fail.status not in (
                "proposed", "saved", "applied", "cancelled", "failed"
            ):
                run_to_fail.status = "failed"
                run_to_fail.error_code = "transport_ai_agent_execution_failed"
                run_to_fail.error_message = "Unexpected error in background executor."
                run_to_fail.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            logger.error(
                "transport_ai_background: could not mark run as failed: %s",
                run_key,
                exc_info=True,
            )
    finally:
        db.close()
```

## Where to place it

Place this function immediately above `start_transport_ai_route_calculation` in the file. Both
functions are in the same router file (`sistema/app/routers/transport_ai.py`). The function is
private (prefix `_`) because it is not a FastAPI route handler and should not be called from
outside this module.

## Imports to add

Add these imports at the top of `transport_ai.py` if not already present:
- `import threading`
- `from sistema.app.database import SessionLocal`
- `from datetime import datetime, timezone` (if not already imported)

## What NOT to do

- Do not remove or modify `start_transport_ai_route_calculation` in this prompt.
- Do not add any HTTP routing decorators to this function.
- Do not create new schemas or models.
- Do not modify any other file.
```

---

### PROMPT 2 — Modify the POST endpoint to be non-blocking

```
You are implementing the fire-and-poll conversion for the Transport AI route calculation feature
in a FastAPI application. PROMPT 1 has already been completed: the function
`_execute_transport_ai_run_in_background(run_key, settings_obj)` now exists in
`sistema/app/routers/transport_ai.py` just above `start_transport_ai_route_calculation`.

Your task in this prompt is to modify `start_transport_ai_route_calculation` so that it:
1. Commits the setup work to the database.
2. Spawns `_execute_transport_ai_run_in_background` in a background thread.
3. Returns HTTP 202 Accepted immediately (not 201, not 200).

## The current endpoint structure (lines 3875–4268 of transport_ai.py)

The endpoint has two logical phases:

SETUP PHASE (fast, ~1–5 s) — lines 3875–4184:
  - Preflight validation → 409 if fails
  - Concurrency check → 409 if at limit
  - Creates TransportAIRun with status="requested", db.flush() (not committed yet)
  - Captures baseline, changes status to "baseline_saved"
  - Resets passengers, changes status to "passengers_reset"
  - Builds planning input, saves to run
  - Validates planning input → 409 if invalid (also restores baseline)

EXECUTION PHASE (slow) — lines 4186–4268:
  - Calls run_transport_ai_agent() — THIS MUST MOVE TO THE BACKGROUND THREAD
  - Creates suggestion
  - Emits SSE events
  - db.commit()
  - Returns HTTP 201

## The exact change

Replace EVERYTHING from the line that calls `run_transport_ai_agent()` (line ~4186) to the end of
the function (line ~4268) with the following logic:

```python
        # --- FIRE-AND-POLL: commit setup, spawn background executor, return 202 ---

        # Commit all setup work so the background thread can see it in its own session.
        # This is mandatory: the background thread opens a new SessionLocal() and will
        # not see rows that have not been committed.
        db.commit()

        # Spawn the background thread. daemon=True so it doesn't block server shutdown.
        thread = threading.Thread(
            target=_execute_transport_ai_run_in_background,
            args=(run.run_key, settings),
            daemon=True,
            name=f"transport-ai-{run.run_key}",
        )
        thread.start()

        # Return 202 Accepted immediately. The agent is now running in the background.
        # The client will poll GET /api/transport/ai/route-calculations/{run_key} for status.
        return JSONResponse(
            status_code=202,
            content=_build_transport_ai_start_response(
                ok=True,
                run_key=run.run_key,
                suggestion_key=None,
                suggestion_ready=False,
                status_value=run.status,   # "passengers_reset" at this point
                message="Cálculo iniciado. Os resultados estarão disponíveis em alguns minutos.",
                message_key="ai.routeCalculationStarted",
                message_params={},
                error_code=None,
                failure_category=None,
                review_state="unavailable",
                issues=preflight_issues,
                can_cancel_restore=True,
            ).model_dump(),
        )
```

## Important notes about the commit

The current endpoint has a SINGLE `db.commit()` at the very end (line ~4258). By moving the
commit to just before the thread spawn, you are committing the setup work early. This is
intentional and safe because:

- The setup work (run creation, baseline, passenger resets, planning input) is complete and valid
  by the time we reach this point — the validation check has already passed.
- The execution phase (agent, suggestion, events) now happens in a separate transaction managed by
  the background thread.
- If the background thread fails, the run will be marked as "failed" by the thread's error
  handler — no data is lost.

## The variable `preflight_issues`

Look for where `preflight_issues` is built in the setup phase (it is populated from the planning
input validation, stored in the run's `preflight_issues_json`, and typically an empty list or
list of `TransportAIPreflightIssue` objects). Use whatever variable holds this list. If the
existing code calls it something different (e.g., `validation_preflight_issues`), use that name.

## The `_build_transport_ai_start_response` helper

This helper already exists in the file. Look for its definition (search for
`def _build_transport_ai_start_response`) and check its parameter names — use them exactly.
If the parameter is called `status_value`, pass `status_value=run.status`.

## What NOT to do

- Do not remove the setup phase (lines 3875–4184) — it stays exactly as is.
- Do not import `JSONResponse` if it is already imported (check existing imports at the top of
  the router file).
- Do not modify `_execute_transport_ai_run_in_background`.
- Do not modify any schema, model, or other file.
- Do not add `async` to the function — it is and must remain a sync `def`.
```

---

### PROMPT 3 — Verify and harden the GET status endpoint

```
You are implementing the fire-and-poll conversion for the Transport AI route calculation feature.
PROMPTS 1 and 2 are complete: the POST endpoint now returns 202 immediately and spawns a background
thread. Clients will now call the GET status endpoint frequently (every 5–10 seconds) while the
AI is running.

Your task is to review and harden the GET status endpoint to make sure it handles ALL possible
run statuses without errors or misleading responses.

## The endpoint to review

File: `sistema/app/routers/transport_ai.py`
Function: `get_transport_ai_route_calculation_status` (line 3332)
URL: `GET /api/transport/ai/route-calculations/{run_key}`

This endpoint is called by the frontend's `pollAiRouteRun()` function every few seconds.

## The new intermediate statuses it must handle

Before this fire-and-poll change, clients never saw the endpoint return while the run was in
"requested", "baseline_saved", or "passengers_reset" status — the HTTP request was still open.

Now, the client will poll immediately after receiving the 202, so the GET endpoint will be called
with the run in these intermediate statuses. Verify the endpoint handles them correctly.

## Expected response contract per status

For EVERY status, the response must:
- NOT raise an exception (HTTP 500).
- Return a valid `TransportAgentRunStatusResponse` (or equivalent schema).
- Set `suggestion_ready: false` for all non-terminal states.
- Set `suggestion_ready: true` only when `status == "proposed"` and a suggestion exists.

Required behavior per status:

| status           | suggestion_ready | review_state          | can_save | can_apply |
|------------------|------------------|-----------------------|----------|-----------|
| requested        | false            | unavailable           | false    | false     |
| baseline_saved   | false            | unavailable           | false    | false     |
| passengers_reset | false            | unavailable           | false    | false     |
| running          | false            | unavailable           | false    | false     |
| proposed         | true             | review_ready OR       | true     | true      |
|                  |                  | review_with_exceptions|          |           |
| failed           | false            | fatal_error           | false    | false     |
| cancelled        | false            | unavailable           | false    | false     |

## What to look for and fix

1. Does the function try to access `run.suggestion` or a related suggestion object when the run
   might not have one yet? If so, guard with `if run.suggestion is not None`.

2. Does the function call any helper that assumes the run is in a terminal state ("proposed",
   "failed")? If so, add early-return branches for intermediate states.

3. Does the function correctly return `suggestion_ready=False` when `run.status` is not in the
   terminal success states? Verify the condition.

4. If the function calls `db.query(TransportAISuggestion).filter_by(run_id=run.id).first()` to
   find the suggestion, this will return `None` for intermediate states — make sure that `None`
   is handled gracefully (does not cause a NoneType error downstream).

## Authentication note

Verify whether this GET endpoint requires authentication (a `Depends(require_transport_session)`
parameter). If it does, the frontend polling calls must include the session cookie — confirm this
is the case in the frontend's `pollAiRouteRun()` function (it should use `fetch()` with
`credentials: "include"` or `credentials: "same-origin"`).

If the GET endpoint does NOT require authentication, document this explicitly in a comment — it
means anyone with a `run_key` can poll for status. This may be intentional (run keys are UUIDs),
but it should be noted.

## What NOT to do

- Do not change the URL path of this endpoint.
- Do not change the response schema (add fields only if strictly needed for the polling UI).
- Do not modify the POST endpoint or background function.
- Make only the minimal changes needed to prevent errors for intermediate statuses.
```

---

### PROMPT 4 — Update the frontend POST handler

```
You are implementing the fire-and-poll conversion for the Transport AI route calculation feature.
The backend changes (PROMPTS 1, 2, 3) are complete. The POST endpoint now returns HTTP 202 in
under 5 seconds with a JSON body containing `run_key`, `suggestion_ready: false`, and
`status: "passengers_reset"`. The GET polling endpoint handles all statuses correctly.

Your task is to update the frontend JavaScript so it correctly handles the new 202 response and
immediately begins polling.

## File to modify

`sistema/app/static/transport/app.js`

## The function to modify: `requestAiRoutes()` (approximately line 9669)

Read this function carefully before changing anything. It currently:
1. POSTs to `/api/transport/ai/route-calculations` with the payload.
2. Awaits the response — which currently takes 2–30 minutes because the backend was synchronous.
3. Reads the response JSON.
4. If `response.ok` is false OR the response body has an error: shows error UI.
5. If `suggestion_ready` is true in the body: calls `openAiChangesModal(result)` immediately.
6. If `suggestion_ready` is false: calls `pollAiRouteRun(result.run_key)` to begin polling.

After the backend change, case 6 is now the NORMAL case. Case 5 (immediate success) will never
happen for a fresh POST — it only happens when polling resolves.

## The specific change needed

The problem is that the POST response status code is now 202, not 200 or 201. Depending on how
`response.ok` is evaluated, 202 is already truthy (fetch's `response.ok` is true for any 2xx
code). Verify this is the case.

The main logic change: when the POST responds with `suggestion_ready: false` and a valid `run_key`,
the function should immediately start the polling cycle WITHOUT showing an error.

Look for any code like:
```javascript
if (!result.ok) { /* show error */ return; }
if (result.suggestion_ready) { openAiChangesModal(result); return; }
pollAiRouteRun(result.run_key);
```

This existing structure should already work for the new 202 response as long as:
- `result.run_key` is present in the 202 body (it is — backend sends it).
- `result.suggestion_ready` is `false` (it is).
- `pollAiRouteRun` is called with the `run_key` string (verify the variable name).

If the structure already works: add a comment explaining that the 202 case is now the primary
flow, to help future developers understand why there is no "else" branch for "if suggestion_ready".

## The loading state problem

Currently, the loading indicator (spinner, disabled button, etc.) is shown only while the POST
fetch is in flight. After the POST resolves in <5 seconds, the loading state is cleared — even
though the AI is still running in the background and polling has just started.

Find where the loading state is set and cleared. It will look something like:
```javascript
setAiRoutesLoading(true);    // before fetch
// ... fetch ...
setAiRoutesLoading(false);   // after fetch, WRONG — polling still happening
```

Change the loading state management so:
1. Loading is set to `true` BEFORE the POST fetch (as today).
2. Loading is NOT cleared when the POST resolves with 202 and `suggestion_ready: false`.
3. Loading is cleared only when polling ends — either on success (before opening the modal)
   or on error (when showing the error message).

Find the place in `pollAiRouteRun()` or in its success/error callbacks where the modal is opened
or the error is shown, and ensure `setAiRoutesLoading(false)` (or equivalent) is called there.

## What NOT to do

- Do not modify `pollAiRouteRun()` itself (that is PROMPT 5's job).
- Do not change any backend file.
- Do not change the URL of the POST request.
- Do not add new state variables unless strictly necessary — reuse existing ones.
- Do not change the `openAiChangesModal()` function.
```

---

### PROMPT 5 — Update the frontend polling to show status-aware progress

```
You are implementing the fire-and-poll conversion for the Transport AI route calculation feature.
PROMPTS 1–4 are complete. The POST returns 202 immediately, the client starts polling, and the
loading state persists during polling.

Your task is to update the polling logic and UI to correctly handle the new intermediate run
statuses and provide a good user experience during the wait.

## File to modify

`sistema/app/static/transport/app.js`

## Function to review: `pollAiRouteRun(runKey)` (approximately line 9590)

Read this function carefully. It:
1. GETs `/api/transport/ai/route-calculations/{runKey}`.
2. Calls `shouldContinuePollingAiRouteRun(response)` to decide whether to poll again.
3. Calls `hasRenderableTransportAiReview(response)` to decide whether to open the modal.
4. On success: opens the review modal.
5. On error: shows error UI.
6. On "continue": schedules next poll via `queueAiRouteRunPoll()` with exponential backoff.

## Change 1: ensure `shouldContinuePollingAiRouteRun` handles new statuses

Find `shouldContinuePollingAiRouteRun(response)`. It currently returns `true` (keep polling) for
some statuses and `false` (stop) for others.

Make sure it returns `true` (keep polling) for ALL of these statuses:
  - `"requested"`
  - `"baseline_saved"`
  - `"passengers_reset"`
  - `"running"`

And returns `false` (stop polling) for terminal statuses:
  - `"proposed"` — success, open modal
  - `"failed"` — error, show message
  - `"cancelled"` — cancelled, show message
  - `"saved"`, `"applied"` — already acted on

The simplest correct implementation:
```javascript
function shouldContinuePollingAiRouteRun(response) {
  const terminalStatuses = ["proposed", "saved", "applied", "cancelled", "failed"];
  return !terminalStatuses.includes(response && response.status);
}
```

## Change 2: show a status-aware label during polling

Find where the loading/progress message is displayed to the user during the polling cycle.
It might be a text node, an element's `textContent`, or a CSS class toggle.

Replace the single "loading" message with a status-aware message that changes as the run
progresses through the pipeline:

```javascript
function getAiRoutePollingStatusLabel(status) {
  switch (status) {
    case "requested":
    case "baseline_saved":
      return "Preparando dados...";
    case "passengers_reset":
      return "Inicializando cálculo...";
    case "running":
      return "Calculando rotas com IA...";
    default:
      return "Aguardando resultado...";
  }
}
```

Call this function inside the polling loop where the response is received, and update the UI
element text accordingly.

## Change 3: confirm `hasRenderableTransportAiReview` works correctly

Find `hasRenderableTransportAiReview(response)`. It should return `true` ONLY when:
- `response.suggestion_ready === true` AND
- `response.review_state === "review_ready"` OR `response.review_state === "review_with_exceptions"`

Verify this is the case. If the function also checks HTTP status code (e.g., only returns true
for 200), remove that check — the polling GET will always return 200 for any found run.

## Change 4: handle the "failed" status gracefully

When `shouldContinuePollingAiRouteRun` returns `false` and `hasRenderableTransportAiReview`
returns `false`, the run has ended without a usable suggestion (failed, cancelled, or unexpected).

Find the error display code in `pollAiRouteRun`. Make sure it uses `response.message` (the
user-facing message from the backend) rather than a hardcoded generic message. The backend
already populates `message` (and `message_key` for i18n) in the `TransportAgentRunStatusResponse`
for failed runs.

## What NOT to do

- Do not modify `requestAiRoutes()` (that was PROMPT 4's job).
- Do not change any backend file.
- Do not change the polling interval logic (`queueAiRouteRunPoll` and its backoff) unless
  there is a clear bug. The existing backoff is intentional.
- Do not add new API endpoints.
- Keep changes minimal and focused on correctness and user feedback.
```

---

## Testing Checklist

After all five prompts are implemented, verify the following scenarios:

### Single user — happy path
1. User clicks "Calcular Rotas".
2. The button becomes disabled/loading within 1 second.
3. Within 5 seconds, the POST responds 202 and polling begins.
4. The status label changes: "Preparando dados..." → "Calculando rotas com IA...".
5. When the AI finishes (2–30 min), the review modal opens automatically.
6. The run's final status in the database is "proposed".

### Single user — network disconnect during calculation
1. User clicks "Calcular Rotas", gets 202, polling starts.
2. User closes the browser tab.
3. The background thread continues running on the server.
4. User reopens the tab: the "latest suggestion" endpoint (`GET /suggestions/latest`) returns
   the completed suggestion if it exists. The UI shows the result.
5. The run's status in the database is "proposed" regardless of browser disconnect.

### Single user — AI agent fails
1. User clicks "Calcular Rotas", gets 202, polling starts.
2. The background thread encounters an error.
3. Run status in database changes to "failed" with an `error_code`.
4. Polling detects `status === "failed"`, stops, shows the `message` from the response.
5. The UI is no longer stuck in loading state.

### Concurrent users (100 simultaneous)
1. 100 users click "Calcular Rotas" at the same time.
2. Users within `TRANSPORT_AI_MAX_CONCURRENT_RUNS` get 202 and enter polling.
3. Users beyond the concurrency limit get 409 immediately with a clear message.
4. The server is not blocked — it can serve other requests (health checks, other endpoints)
   during the long AI calculations.

### Server restart during calculation
1. User starts a calculation, gets 202, polls.
2. Before the calculation completes, Gunicorn restarts the worker (e.g., due to `--max-requests`).
3. The background thread is killed (daemon=True).
4. The run remains in "running" status in the database indefinitely.
5. The polling client eventually times out or detects the stale state.
6. **Known limitation**: a stale "running" run blocks the concurrency limit until manually
   resolved. Future improvement: add a stale-run detection job that marks runs older than
   `transport_ai_max_runtime_seconds * 2` as "failed" if still in "running" status.
