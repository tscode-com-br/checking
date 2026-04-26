from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path

import httpx
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[1]
PREVIEW_DB_PATH = ROOT / "preview_phase6_homologation.db"
REPORT_PATH = ROOT / "docs" / "temp_008_phase6_report.json"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8766
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
ADMIN_CHAVE = "HR70"
ADMIN_SENHA = "eAcacdLe2"
LOCATION_THRESHOLD_METERS = 30
LOCATION_LATITUDE = 1.255936
LOCATION_LONGITUDE = 103.611066
DEFAULT_LOCATION_LABEL = "Escritório Principal"
FALLBACK_LOCATION_LABEL = "Precisao Insuficiente"
P80_LOCATION = DEFAULT_LOCATION_LABEL
P82_LOCATION = "Portaria"

SCENARIOS = (
    {
        "name": "scenario_a_toggle_off_with_default_location",
        "chave": "T8A1",
        "senha": "abc123",
        "project": "P80",
        "persisted_automatic": False,
        "expected_automatic": False,
        "expected_default": DEFAULT_LOCATION_LABEL,
        "expected_state_local": DEFAULT_LOCATION_LABEL,
        "sequence": [42, 39, 35],
        "grant_permission": True,
        "persist_permission_flag": True,
    },
    {
        "name": "scenario_b_toggle_off_with_synthetic_fallback",
        "chave": "T8B2",
        "senha": "abc123",
        "project": "P82",
        "persisted_automatic": False,
        "expected_automatic": False,
        "expected_default": FALLBACK_LOCATION_LABEL,
        "expected_state_local": FALLBACK_LOCATION_LABEL,
        "sequence": [42, 39, 35],
        "grant_permission": True,
        "persist_permission_flag": True,
    },
    {
        "name": "scenario_c_toggle_on_with_default_location",
        "chave": "T8C3",
        "senha": "abc123",
        "project": "P80",
        "persisted_automatic": False,
        "expected_automatic": True,
        "expected_default": DEFAULT_LOCATION_LABEL,
        "expected_state_local": DEFAULT_LOCATION_LABEL,
        "sequence": [42, 39, 35],
        "grant_permission": True,
        "persist_permission_flag": True,
    },
    {
        "name": "scenario_d_toggle_on_with_synthetic_fallback",
        "chave": "T8D4",
        "senha": "abc123",
        "project": "P82",
        "persisted_automatic": False,
        "expected_automatic": True,
        "expected_default": FALLBACK_LOCATION_LABEL,
        "expected_state_local": FALLBACK_LOCATION_LABEL,
        "sequence": [42, 39, 35],
        "grant_permission": True,
        "persist_permission_flag": True,
    },
    {
        "name": "scenario_e_no_permission_flow_preserved",
        "chave": "T8E5",
        "senha": "abc123",
        "project": "P82",
        "persisted_automatic": False,
        "expected_automatic": False,
        "expected_default": P82_LOCATION,
        "expected_state_local": P82_LOCATION,
        "sequence": [
            {
                "delay_ms": 250,
                "error": {
                    "code": 1,
                    "message": "Permission denied",
                },
            }
        ],
        "grant_permission": False,
        "persist_permission_flag": True,
    },
)


def build_rectangle_coordinates(
    latitude: float,
    longitude: float,
    *,
    latitude_delta: float = 0.0002,
    longitude_delta: float = 0.0002,
) -> list[dict[str, float]]:
    return [
        {"latitude": latitude, "longitude": longitude},
        {"latitude": latitude + latitude_delta, "longitude": longitude},
        {"latitude": latitude + latitude_delta, "longitude": longitude + longitude_delta},
        {"latitude": latitude, "longitude": longitude + longitude_delta},
    ]


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_accuracy_sequence(*accuracy_values: int, delay_step_ms: int = 900) -> list[dict[str, object]]:
    sequence: list[dict[str, object]] = []
    for index, accuracy in enumerate(accuracy_values, start=1):
        sequence.append(
            {
                "delay_ms": delay_step_ms * index,
                "position": {
                    "latitude": LOCATION_LATITUDE + 0.00005,
                    "longitude": LOCATION_LONGITUDE + 0.00005,
                    "accuracy": accuracy,
                },
            }
        )
    return sequence


def normalize_sequence(sequence: list[int] | list[dict[str, object]]) -> list[dict[str, object]]:
    if not sequence:
        return []
    if isinstance(sequence[0], dict):
        return [dict(item) for item in sequence]  # type: ignore[arg-type]
    return build_accuracy_sequence(*[int(value) for value in sequence])


def build_init_script(
    *,
    chave: str,
    senha: str,
    project: str,
    automatic_enabled: bool,
    initial_sequence: list[dict[str, object]],
    persist_permission_flag: bool,
) -> str:
    persisted_settings = {
        chave: {
            "project": project,
            "automaticActivitiesEnabled": automatic_enabled,
        }
    }
    persisted_passwords = {chave: senha}

    return f"""
(() => {{
  const persistedChave = {json.dumps(chave)};
  const persistedPasswordMap = {json.dumps(persisted_passwords)};
  const persistedSettingsMap = {json.dumps(persisted_settings)};
  const initialSequence = {json.dumps(initial_sequence)};
  const persistPermissionFlag = {json.dumps(persist_permission_flag)};
  const geoStorageKey = '__temp008_geo_sequence__';

  window.localStorage.setItem('checking.web.user.chave', persistedChave);
  window.localStorage.setItem('checking.web.user.password.by-chave', JSON.stringify(persistedPasswordMap));
  window.localStorage.setItem('checking.web.user.settings.by-chave', JSON.stringify(persistedSettingsMap));
  if (persistPermissionFlag) {{
    window.localStorage.setItem('checking.web.user.location.permission-granted', '1');
  }} else {{
    window.localStorage.removeItem('checking.web.user.location.permission-granted');
  }}
  window.localStorage.setItem(geoStorageKey, JSON.stringify(initialSequence));

  function readSequence() {{
    try {{
      const raw = window.localStorage.getItem(geoStorageKey);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    }} catch {{
      return [];
    }}
  }}

  function createPosition(position) {{
    const payload = position || {{}};
    return {{
      coords: {{
        latitude: Number(payload.latitude),
        longitude: Number(payload.longitude),
        accuracy: Number(payload.accuracy),
      }},
      timestamp: Date.now(),
    }};
  }}

  function createErrorPayload(error) {{
    const payload = error || {{}};
    return {{
      code: Number.isFinite(payload.code) ? Number(payload.code) : 2,
      message: String(payload.message || 'Mocked geolocation error'),
    }};
  }}

  function queueSequence(sequence, onSuccess, onError) {{
    const timers = [];
    for (const entry of Array.isArray(sequence) ? sequence : []) {{
      const delayMs = Number.isFinite(entry && entry.delay_ms) ? Math.max(0, Number(entry.delay_ms)) : 0;
      const timerId = window.setTimeout(() => {{
        if (entry && entry.error) {{
          onError(createErrorPayload(entry.error));
          return;
        }}
        onSuccess(createPosition(entry && entry.position));
      }}, delayMs);
      timers.push(timerId);
    }}
    return timers;
  }}

  const geoState = {{
    nextWatchId: 1,
    activeTimers: new Map(),
  }};

  const geoMock = {{
    setSequence(sequence) {{
      window.localStorage.setItem(geoStorageKey, JSON.stringify(sequence || []));
    }},
    getSequence() {{
      return readSequence();
    }},
    getCurrentPosition(onSuccess, onError) {{
      const sequence = readSequence();
      const firstEntry = sequence[0] || null;
      const delayMs = Number.isFinite(firstEntry && firstEntry.delay_ms) ? Math.max(0, Number(firstEntry.delay_ms)) : 0;
      window.setTimeout(() => {{
        if (firstEntry && firstEntry.error) {{
          onError(createErrorPayload(firstEntry.error));
          return;
        }}
        onSuccess(createPosition(firstEntry && firstEntry.position));
      }}, delayMs);
    }},
    watchPosition(onSuccess, onError) {{
      const watchId = geoState.nextWatchId++;
      const timers = queueSequence(readSequence(), onSuccess, onError);
      geoState.activeTimers.set(watchId, timers);
      return watchId;
    }},
    clearWatch(watchId) {{
      const timers = geoState.activeTimers.get(watchId) || [];
      for (const timerId of timers) {{
        window.clearTimeout(timerId);
      }}
      geoState.activeTimers.delete(watchId);
    }},
  }};

  Object.defineProperty(navigator, 'geolocation', {{
    configurable: true,
    value: {{
      getCurrentPosition: geoMock.getCurrentPosition.bind(geoMock),
      watchPosition: geoMock.watchPosition.bind(geoMock),
      clearWatch: geoMock.clearWatch.bind(geoMock),
    }},
  }});

  window.__temp008GeoMock__ = geoMock;
}})();
"""


async def wait_for_health(timeout_seconds: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=2.0) as client:
        while time.monotonic() < deadline:
            try:
                response = await client.get("/api/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.25)
    raise TimeoutError("Timed out waiting for the local preview server to become healthy")


async def seed_preview_data() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=10.0) as admin_client:
        login_response = await admin_client.post(
            "/api/admin/auth/login",
            json={"chave": ADMIN_CHAVE, "senha": ADMIN_SENHA},
        )
        login_response.raise_for_status()

        settings_response = await admin_client.post(
            "/api/admin/locations/settings",
            json={"location_accuracy_threshold_meters": LOCATION_THRESHOLD_METERS},
        )
        settings_response.raise_for_status()

        for local_name, project in ((P80_LOCATION, "P80"), (P82_LOCATION, "P82")):
            create_location_response = await admin_client.post(
                "/api/admin/locations",
                json={
                    "local": local_name,
                    "coordinates": build_rectangle_coordinates(LOCATION_LATITUDE, LOCATION_LONGITUDE),
                    "projects": [project],
                    "tolerance_meters": 150,
                },
            )
            create_location_response.raise_for_status()

    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=10.0) as web_client:
        for scenario in SCENARIOS:
            register_response = await web_client.post(
                "/api/web/auth/register-user",
                json={
                    "chave": scenario["chave"],
                    "nome": f"Homologacao {scenario['name']}",
                    "projeto": scenario["project"],
                    "email": "",
                    "senha": scenario["senha"],
                    "confirmar_senha": scenario["senha"],
                },
            )
            register_response.raise_for_status()


async def create_authenticated_page(browser, scenario: dict[str, object]):
    context = await browser.new_context(base_url=BASE_URL, viewport={"width": 430, "height": 932})
    if bool(scenario["grant_permission"]):
        await context.grant_permissions(["geolocation"], origin=BASE_URL)
    await context.add_init_script(
        build_init_script(
            chave=str(scenario["chave"]),
            senha=str(scenario["senha"]),
            project=str(scenario["project"]),
            automatic_enabled=bool(scenario["persisted_automatic"]),
            initial_sequence=normalize_sequence(scenario["sequence"]),
            persist_permission_flag=bool(scenario["persist_permission_flag"]),
        )
    )
    page = await context.new_page()
    await page.goto(f"{BASE_URL}/user", wait_until="domcontentloaded")
    await ensure_authenticated_session(page, chave=str(scenario["chave"]), senha=str(scenario["senha"]))
    await page.reload(wait_until="domcontentloaded")
    return context, page


async def ensure_authenticated_session(page, *, chave: str, senha: str) -> None:
    result = await page.evaluate(
        """async ({ chave, senha }) => {
          const response = await fetch('/api/web/auth/login', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'application/json',
            },
            body: JSON.stringify({ chave, senha }),
          });
          const payload = await response.json().catch(() => ({}));
          return {
            ok: response.ok,
            status: response.status,
            payload,
          };
        }""",
        {"chave": chave, "senha": senha},
    )
    if not result.get("ok"):
        raise RuntimeError(f"Unable to authenticate browser session for {chave}: {result}")


async def wait_for_authenticated_ui_ready(page, *, timeout_ms: float = 15000) -> None:
    await page.wait_for_function(
        """() => {
          const projectSelect = document.querySelector('#projectSelect');
          const passwordInput = document.querySelector('#passwordInput');
          const submitButton = document.querySelector('#submitButton');
          return Boolean(
            projectSelect
            && projectSelect.options.length > 0
            && passwordInput
            && passwordInput.value.length >= 3
            && submitButton
          );
        }""",
        timeout=timeout_ms,
    )


async def read_manual_select_state(page) -> dict[str, object]:
    return await page.evaluate(
        """() => {
          const projectField = document.querySelector('#projectField');
          const locationField = document.querySelector('#locationSelectField');
          const projectSelect = document.querySelector('#projectSelect');
          const manualLocationSelect = document.querySelector('#manualLocationSelect');
          const submitButton = document.querySelector('#submitButton');
          const toggle = document.querySelector('#automaticActivitiesToggle');
          const actionInputs = Array.from(document.querySelectorAll('input[name="action"]'));
          const headerTitle = document.querySelector('.header-logo-text');
          return {
            locationValue: (document.querySelector('#locationValue')?.textContent || '').trim(),
            projectHidden: Boolean(projectField?.classList.contains('is-hidden')),
            locationHidden: Boolean(locationField?.classList.contains('is-hidden')),
            projectDisabled: Boolean(projectSelect?.disabled),
            manualLocationDisabled: Boolean(manualLocationSelect?.disabled),
            manualLocationValue: manualLocationSelect ? manualLocationSelect.value : '',
            manualLocationOptions: manualLocationSelect
              ? Array.from(manualLocationSelect.options).map((option) => option.value)
              : [],
            submitDisabled: Boolean(submitButton?.disabled),
            actionDisabled: actionInputs.map((input) => Boolean(input.disabled)),
            automaticChecked: Boolean(toggle?.checked),
            headerTitle: (headerTitle?.textContent || '').trim(),
          };
        }"""
    )


async def wait_for_accuracy_too_low_state(page, *, expected_default: str, automatic_enabled: bool) -> dict[str, object]:
    await page.wait_for_function(
        """({ expectedDefault, automaticEnabled }) => {
          const projectField = document.querySelector('#projectField');
          const locationField = document.querySelector('#locationSelectField');
          const projectSelect = document.querySelector('#projectSelect');
          const manualLocationSelect = document.querySelector('#manualLocationSelect');
          const submitButton = document.querySelector('#submitButton');
          const toggle = document.querySelector('#automaticActivitiesToggle');
          const actionInputs = Array.from(document.querySelectorAll('input[name="action"]'));
          const locationValue = (document.querySelector('#locationValue')?.textContent || '').trim();
          return (
            locationValue === 'Precisao insuficiente'
            && projectField
            && !projectField.classList.contains('is-hidden')
            && locationField
            && !locationField.classList.contains('is-hidden')
            && projectSelect
            && !projectSelect.disabled
            && manualLocationSelect
            && !manualLocationSelect.disabled
            && manualLocationSelect.value === expectedDefault
            && submitButton
            && !submitButton.disabled
            && actionInputs.length > 0
            && actionInputs.every((input) => !input.disabled)
            && toggle
            && toggle.checked === automaticEnabled
          );
        }""",
        arg={"expectedDefault": expected_default, "automaticEnabled": automatic_enabled},
        timeout=15000,
    )
    return await read_manual_select_state(page)


async def wait_for_no_permission_state(page) -> dict[str, object]:
    await page.wait_for_function(
        """() => {
          const manualLocationSelect = document.querySelector('#manualLocationSelect');
          const locationValue = (document.querySelector('#locationValue')?.textContent || '').trim();
          const options = manualLocationSelect
            ? Array.from(manualLocationSelect.options).map((option) => option.value)
            : [];
          return (
            locationValue === 'Sem Permissão'
            && manualLocationSelect
            && !manualLocationSelect.disabled
            && options.includes('Portaria')
            && !options.includes('Precisao Insuficiente')
          );
        }""",
        timeout=15000,
    )
    return await read_manual_select_state(page)


async def wait_for_state_local(page, chave: str, expected_local: str, *, timeout_seconds: float = 15.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        payload = await page.evaluate(
            """async (chave) => {
              const response = await fetch(`/api/web/check/state?chave=${encodeURIComponent(chave)}`);
              if (!response.ok) {
                return null;
              }
              return response.json();
            }""",
            chave,
        )
        if isinstance(payload, dict) and payload.get("current_local") == expected_local:
            return payload
        await asyncio.sleep(0.25)

    raise TimeoutError(f"Timed out waiting for current_local={expected_local!r} on chave={chave}")


async def submit_current_selection(page, *, expected_local: str, chave: str) -> dict[str, object]:
    await page.locator("#submitButton").click()
    return await wait_for_state_local(page, chave, expected_local)


async def run_accuracy_scenario(browser, scenario: dict[str, object]) -> dict[str, object]:
    context, page = await create_authenticated_page(browser, scenario)
    try:
        print(f"[temp_008_phase6] start {scenario['name']}", flush=True)
        await wait_for_authenticated_ui_ready(page)
        print(f"[temp_008_phase6] ui_ready {scenario['name']}", flush=True)
        await page.evaluate(
            """(sequence) => {
              window.__temp008GeoMock__.setSequence(sequence);
            }""",
            normalize_sequence(scenario["sequence"]),
        )
        await page.locator("#refreshLocationButton").click()
        print(f"[temp_008_phase6] refresh_clicked {scenario['name']}", flush=True)
        ui_state = await wait_for_accuracy_too_low_state(
            page,
            expected_default=str(scenario["expected_default"]),
            automatic_enabled=False,
        )
        print(f"[temp_008_phase6] accuracy_ready {scenario['name']}", flush=True)
        if bool(scenario["expected_automatic"]):
            await page.evaluate(
                """(sequence) => {
                  window.__temp008GeoMock__.setSequence(sequence);
                }""",
                normalize_sequence(scenario["sequence"]),
            )
            await page.locator("#automaticActivitiesToggle").check()
            print(f"[temp_008_phase6] automatic_checked {scenario['name']}", flush=True)
            ui_state = await wait_for_accuracy_too_low_state(
                page,
                expected_default=str(scenario["expected_default"]),
                automatic_enabled=True,
            )
            print(f"[temp_008_phase6] automatic_override_ready {scenario['name']}", flush=True)
        history_state = await submit_current_selection(
            page,
            expected_local=str(scenario["expected_state_local"]),
            chave=str(scenario["chave"]),
        )
        print(f"[temp_008_phase6] submit_ok {scenario['name']}", flush=True)
        assert_condition(ui_state["headerTitle"] == "Checking Weblink", f"Unexpected header title: {ui_state['headerTitle']}")
        return {
            "scenario": scenario["name"],
            "automatic_enabled": scenario["expected_automatic"],
            "ui_state": ui_state,
            "history_state": history_state,
        }
    finally:
        await context.close()


async def run_no_permission_scenario(browser, scenario: dict[str, object]) -> dict[str, object]:
    context, page = await create_authenticated_page(browser, scenario)
    try:
        print(f"[temp_008_phase6] start {scenario['name']}", flush=True)
        await wait_for_authenticated_ui_ready(page)
        print(f"[temp_008_phase6] ui_ready {scenario['name']}", flush=True)
        await page.evaluate(
            """(sequence) => {
              window.__temp008GeoMock__.setSequence(sequence);
            }""",
            normalize_sequence(scenario["sequence"]),
        )
        await page.locator("#refreshLocationButton").click()
        print(f"[temp_008_phase6] refresh_clicked {scenario['name']}", flush=True)
        ui_state = await wait_for_no_permission_state(page)
        print(f"[temp_008_phase6] no_permission_ready {scenario['name']}", flush=True)
        history_state = await submit_current_selection(
            page,
            expected_local=str(scenario["expected_state_local"]),
            chave=str(scenario["chave"]),
        )
        print(f"[temp_008_phase6] submit_ok {scenario['name']}", flush=True)
        assert_condition(ui_state["headerTitle"] == "Checking Weblink", f"Unexpected header title: {ui_state['headerTitle']}")
        return {
            "scenario": scenario["name"],
            "automatic_enabled": scenario["expected_automatic"],
            "ui_state": ui_state,
            "history_state": history_state,
        }
    finally:
        await context.close()


async def run_homologation() -> dict[str, object]:
    if PREVIEW_DB_PATH.exists():
        PREVIEW_DB_PATH.unlink()

    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "development",
            "DATABASE_URL": f"sqlite:///./{PREVIEW_DB_PATH.name}",
            "FORMS_QUEUE_ENABLED": "false",
            "EVENT_ARCHIVES_DIR": str(ROOT / "preview_event_archives"),
            "ADMIN_SESSION_SECRET": "phase6-preview-secret",
        }
    )

    server_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "sistema.app.main:app",
            "--host",
            SERVER_HOST,
            "--port",
            str(SERVER_PORT),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        print("[temp_008_phase6] waiting_for_health", flush=True)
        await wait_for_health()
        print("[temp_008_phase6] seeding_preview_data", flush=True)
        await seed_preview_data()
        print("[temp_008_phase6] seed_complete", flush=True)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                results = [
                    await run_accuracy_scenario(browser, scenario)
                    for scenario in SCENARIOS[:4]
                ]
                results.append(await run_no_permission_scenario(browser, SCENARIOS[4]))
            finally:
                await browser.close()

        report = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "base_url": BASE_URL,
            "preview_db": str(PREVIEW_DB_PATH),
            "location_threshold_meters": LOCATION_THRESHOLD_METERS,
            "results": results,
        }
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    except PlaywrightError as error:
        message = str(error)
        if "Executable doesn't exist" in message:
            raise RuntimeError(
                "Playwright Chromium is not installed in this environment. Run `python -m playwright install chromium`."
            ) from error
        raise
    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait(timeout=10)


def main() -> None:
    report = asyncio.run(run_homologation())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()