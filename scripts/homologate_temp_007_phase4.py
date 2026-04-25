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
PREVIEW_DB_PATH = ROOT / "preview_phase4_homologation.db"
REPORT_PATH = ROOT / "docs" / "temp_007_phase4_report.json"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
ADMIN_CHAVE = "HR70"
ADMIN_SENHA = "eAcacdLe2"
WEB_USER_CHAVE = "H401"
WEB_USER_SENHA = "abc123"
WEB_USER_PROJECT = "P82"
WEB_USER_NAME = "Homologacao Temp 007"
LOCATION_LOCAL = "Homologacao Fase 4 P82"
LOCATION_LATITUDE = 1.255936
LOCATION_LONGITUDE = 103.611066
LOCATION_THRESHOLD_METERS = 30


def build_rectangle_coordinates(
    latitude: float,
    longitude: float,
    *,
    latitude_delta: float = 0.0002,
    longitude_delta: float = 0.0002,
) -> list[dict[str, float]]:
    base_latitude = float(latitude)
    base_longitude = float(longitude)
    return [
        {"latitude": base_latitude, "longitude": base_longitude},
        {"latitude": base_latitude + latitude_delta, "longitude": base_longitude},
        {"latitude": base_latitude + latitude_delta, "longitude": base_longitude + longitude_delta},
        {"latitude": base_latitude, "longitude": base_longitude + longitude_delta},
    ]


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_init_script(initial_sequence: list[dict[str, object]]) -> str:
    persisted_settings = {
        WEB_USER_CHAVE: {
            "project": WEB_USER_PROJECT,
            "automaticActivitiesEnabled": False,
        }
    }
    persisted_passwords = {
        WEB_USER_CHAVE: WEB_USER_SENHA,
    }

    return f"""
(() => {{
  const persistedChave = {json.dumps(WEB_USER_CHAVE)};
  const persistedPasswordMap = {json.dumps(persisted_passwords)};
  const persistedSettingsMap = {json.dumps(persisted_settings)};
  const initialSequence = {json.dumps(initial_sequence)};
  const geoStorageKey = '__phase4_geo_sequence__';
  const uiLog = [];
  let lastUiSnapshot = null;

  window.localStorage.setItem('checking.web.user.chave', persistedChave);
  window.localStorage.setItem('checking.web.user.password.by-chave', JSON.stringify(persistedPasswordMap));
  window.localStorage.setItem('checking.web.user.settings.by-chave', JSON.stringify(persistedSettingsMap));
  window.localStorage.setItem('checking.web.location.measurement.enabled', '1');
    if (!window.localStorage.getItem(geoStorageKey)) {{
        window.localStorage.setItem(geoStorageKey, JSON.stringify(initialSequence));
    }}

  function readSequence() {{
    try {{
      const raw = window.localStorage.getItem(geoStorageKey);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    }} catch {{
      return [];
    }}
  }}

  function cloneEntry(entry) {{
    return entry ? JSON.parse(JSON.stringify(entry)) : entry;
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
      code: Number.isFinite(payload.code) ? payload.code : 2,
      message: String(payload.message || 'Mocked geolocation error'),
    }};
  }}

  function queueSequence(sequence, onSuccess, onError) {{
    const timers = [];
    const entries = Array.isArray(sequence) ? sequence : [];
    for (const entry of entries) {{
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
      return cloneEntry(readSequence());
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

  function recordUiSnapshot() {{
    const locationValue = document.getElementById('locationValue');
    const locationAccuracy = document.getElementById('locationAccuracy');
    if (!locationValue || !locationAccuracy) {{
      return;
    }}

    const nextSnapshot = {{
      at: Date.now(),
      locationValue: (locationValue.textContent || '').trim(),
      locationAccuracy: (locationAccuracy.textContent || '').trim(),
    }};
    if (
      lastUiSnapshot
      && lastUiSnapshot.locationValue === nextSnapshot.locationValue
      && lastUiSnapshot.locationAccuracy === nextSnapshot.locationAccuracy
    ) {{
      return;
    }}
    uiLog.push(nextSnapshot);
    lastUiSnapshot = nextSnapshot;
  }}

  window.__phase4GeoMock__ = geoMock;
  window.__phase4UiLog__ = uiLog;
  window.__phase4ResetUiLog__ = () => {{
    uiLog.length = 0;
    lastUiSnapshot = null;
    recordUiSnapshot();
  }};

  document.addEventListener('DOMContentLoaded', () => {{
    const locationValue = document.getElementById('locationValue');
    const locationAccuracy = document.getElementById('locationAccuracy');
    if (!locationValue || !locationAccuracy) {{
      return;
    }}
    const observer = new MutationObserver(recordUiSnapshot);
    observer.observe(locationValue, {{ childList: true, characterData: true, subtree: true }});
    observer.observe(locationAccuracy, {{ childList: true, characterData: true, subtree: true }});
    recordUiSnapshot();
  }});
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

        create_location_response = await admin_client.post(
            "/api/admin/locations",
            json={
                "local": LOCATION_LOCAL,
                "coordinates": build_rectangle_coordinates(LOCATION_LATITUDE, LOCATION_LONGITUDE),
                "projects": [WEB_USER_PROJECT],
                "tolerance_meters": 150,
            },
        )
        create_location_response.raise_for_status()

    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=10.0) as web_client:
        register_response = await web_client.post(
            "/api/web/auth/register-user",
            json={
                "chave": WEB_USER_CHAVE,
                "nome": WEB_USER_NAME,
                "projeto": WEB_USER_PROJECT,
                "email": "",
                "senha": WEB_USER_SENHA,
                "confirmar_senha": WEB_USER_SENHA,
            },
        )
        register_response.raise_for_status()


async def create_authenticated_page(browser, initial_sequence: list[dict[str, object]]):
    context = await browser.new_context(base_url=BASE_URL, viewport={"width": 430, "height": 932})
    await context.grant_permissions(["geolocation"], origin=BASE_URL)
    await context.add_init_script(build_init_script(initial_sequence))
    page = await context.new_page()
    await page.goto(f"{BASE_URL}/user", wait_until="domcontentloaded")
    return context, page


async def wait_for_authenticated_ui_ready(page, *, timeout_ms: float = 15000) -> None:
        await page.wait_for_function(
                """() => {
                    const submitButton = document.querySelector('#submitButton');
                    const passwordInput = document.querySelector('#passwordInput');
                    const projectSelect = document.querySelector('#projectSelect');
                    const locationValue = document.querySelector('#locationValue');
                    const locationAccuracy = document.querySelector('#locationAccuracy');
                    return Boolean(
                        window.CheckingWebLocationMeasurement
                        && window.__phase4GeoMock__
                        && submitButton
                        && submitButton.disabled === false
                        && passwordInput
                        && passwordInput.value.length >= 3
                        && projectSelect
                        && projectSelect.options.length > 0
                        && locationValue
                        && locationAccuracy
                        && (
                            (locationValue.textContent || '').trim() !== 'Aguardando localização.'
                            || (locationAccuracy.textContent || '').trim() !== '--'
                        )
                    );
                }""",
                timeout=timeout_ms,
        )


async def wait_for_finished_trigger_session(page, trigger: str, *, timeout_ms: float = 15000):
    await page.wait_for_function(
        """(expectedTrigger) => {
          const sessions = window.CheckingWebLocationMeasurement?.getSessions?.() || [];
          const filtered = sessions.filter((session) => session.trigger === expectedTrigger);
          if (!filtered.length) {
            return false;
          }
          const latest = filtered[filtered.length - 1];
          return latest.finished_at_ms !== null ? latest : false;
        }""",
        arg=trigger,
        timeout=timeout_ms,
    )
    return await page.evaluate(
        """(expectedTrigger) => {
          const sessions = window.CheckingWebLocationMeasurement.getSessions().filter(
            (session) => session.trigger === expectedTrigger
          );
          return sessions[sessions.length - 1];
        }""",
        trigger,
    )


async def reset_measurement_state(page) -> None:
    await page.evaluate(
        """() => {
          window.CheckingWebLocationMeasurement.clear();
          if (typeof window.__phase4ResetUiLog__ === 'function') {
            window.__phase4ResetUiLog__();
          }
        }"""
    )


async def set_geo_sequence(page, sequence: list[dict[str, object]]) -> None:
    await page.evaluate(
        """(nextSequence) => {
          window.__phase4GeoMock__.setSequence(nextSequence);
        }""",
        sequence,
    )


async def read_ui_log(page) -> list[dict[str, object]]:
    return await page.evaluate("() => window.__phase4UiLog__ || []")


def unique_progress_texts(ui_log: list[dict[str, object]]) -> list[str]:
    values: list[str] = []
    for entry in ui_log:
        accuracy_text = str(entry.get("locationAccuracy") or "").strip()
        if accuracy_text.startswith("Precisão atual ") and accuracy_text not in values:
            values.append(accuracy_text)
    return values


def build_sample_sequence(*accuracy_values: int, delay_step_ms: int = 400) -> list[dict[str, object]]:
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


def assert_final_ui_restored(location_accuracy_text: str) -> None:
    assert_condition(
        not location_accuracy_text.startswith("Precisão atual "),
        f"Expected the final locationAccuracy slot to leave progress mode, got: {location_accuracy_text}",
    )


async def run_startup_scenario(browser) -> dict[str, object]:
    startup_sequence = build_sample_sequence(42, 18, delay_step_ms=550)
    context, page = await create_authenticated_page(browser, startup_sequence)
    try:
        startup_session = await wait_for_finished_trigger_session(page, "startup")
        ui_log = await read_ui_log(page)
        final_location_accuracy = await page.locator("#locationAccuracy").inner_text()
        final_location_value = await page.locator("#locationValue").inner_text()

        progress_values = unique_progress_texts(ui_log)
        assert_condition(
            progress_values[:2] == [
                "Precisão atual 42 m / Limite 30 m",
                "Precisão atual 18 m / Limite 30 m",
            ],
            f"Unexpected startup progress values: {progress_values}",
        )
        assert_condition(
            startup_session["termination_reason"] == "match_response",
            f"Unexpected startup termination reason: {startup_session['termination_reason']}",
        )
        assert_condition(
            startup_session["final_status"] == "matched",
            f"Unexpected startup final status: {startup_session['final_status']}",
        )
        assert_condition(
            startup_session["best_accuracy_meters"] == 18,
            f"Unexpected startup best accuracy: {startup_session['best_accuracy_meters']}",
        )
        assert_condition(
            startup_session["duration_ms"] < 5000,
            f"Startup should finish before 5000 ms when threshold is reached: {startup_session['duration_ms']}",
        )
        assert_final_ui_restored(final_location_accuracy.strip())

        return {
            "scenario": "startup_initial_load",
            "trigger": "startup",
            "session": startup_session,
            "progress_values": progress_values,
            "final_location_accuracy": final_location_accuracy.strip(),
            "final_location_value": final_location_value.strip(),
        }
    finally:
        await context.close()


async def run_lifecycle_event_scenarios_on_page(page) -> list[dict[str, object]]:
    results = []
    results.append(
        await run_lifecycle_event_scenario(
            page,
            "visibility",
            "() => document.dispatchEvent(new Event('visibilitychange'))",
        )
    )
    results.append(
        await run_lifecycle_event_scenario(
            page,
            "focus",
            "() => window.dispatchEvent(new Event('focus'))",
        )
    )
    results.append(
        await run_lifecycle_event_scenario(
            page,
            "pageshow",
            "() => window.dispatchEvent(new Event('pageshow'))",
        )
    )
    return results


async def run_refresh_and_lifecycle_scenarios(browser) -> tuple[dict[str, object], list[dict[str, object]]]:
    context, page = await create_authenticated_page(browser, build_sample_sequence(10, delay_step_ms=100))
    try:
        await wait_for_finished_trigger_session(page, "startup")
        await reset_measurement_state(page)
        await page.wait_for_timeout(1300)
        await set_geo_sequence(page, build_sample_sequence(42, 39, 35, delay_step_ms=1400))
        await page.reload(wait_until="domcontentloaded")

        refresh_session = await wait_for_finished_trigger_session(page, "startup")
        ui_log = await read_ui_log(page)
        final_location_accuracy = await page.locator("#locationAccuracy").inner_text()
        final_location_value = await page.locator("#locationValue").inner_text()

        progress_values = unique_progress_texts(ui_log)
        assert_condition(
            progress_values[:3] == [
                "Precisão atual 42 m / Limite 30 m",
                "Precisão atual 39 m / Limite 30 m",
                "Precisão atual 35 m / Limite 30 m",
            ],
            f"Unexpected refresh progress values: {progress_values}",
        )
        assert_condition(
            refresh_session["final_status"] == "accuracy_too_low",
            f"Unexpected refresh final status: {refresh_session['final_status']}",
        )
        assert_condition(
            refresh_session["best_accuracy_meters"] == 35,
            f"Unexpected refresh best accuracy: {refresh_session['best_accuracy_meters']}",
        )
        assert_condition(
            refresh_session["duration_ms"] >= 5000,
            f"Refresh should hold until the 5000 ms ceiling when threshold is not reached: {refresh_session['duration_ms']}",
        )
        assert_final_ui_restored(final_location_accuracy.strip())

        refresh_result = {
            "scenario": "browser_refresh",
            "trigger": "startup",
            "session": refresh_session,
            "progress_values": progress_values,
            "final_location_accuracy": final_location_accuracy.strip(),
            "final_location_value": final_location_value.strip(),
        }
        lifecycle_results = await run_lifecycle_event_scenarios_on_page(page)
        return refresh_result, lifecycle_results
    finally:
        await context.close()


async def run_lifecycle_event_scenario(page, trigger: str, event_expression: str) -> dict[str, object]:
    await reset_measurement_state(page)
    await page.wait_for_timeout(1300)
    await set_geo_sequence(page, build_sample_sequence(15, delay_step_ms=180))
    await page.evaluate(event_expression)

    session = await wait_for_finished_trigger_session(page, trigger)
    ui_log = await read_ui_log(page)
    progress_values = unique_progress_texts(ui_log)
    final_location_accuracy = await page.locator("#locationAccuracy").inner_text()

    assert_condition(
        progress_values[:1] == ["Precisão atual 15 m / Limite 30 m"],
        f"Unexpected {trigger} progress values: {progress_values}",
    )
    assert_condition(
        session["final_status"] == "matched",
        f"Unexpected {trigger} final status: {session['final_status']}",
    )
    assert_condition(
        session["duration_ms"] < 5000,
        f"Expected {trigger} to finish before the 5000 ms ceiling: {session['duration_ms']}",
    )
    assert_final_ui_restored(final_location_accuracy.strip())

    return {
        "scenario": f"{trigger}_lifecycle_event",
        "trigger": trigger,
        "session": session,
        "progress_values": progress_values,
        "final_location_accuracy": final_location_accuracy.strip(),
    }


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
            "ADMIN_SESSION_SECRET": "phase4-preview-secret",
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
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        await wait_for_health()
        await seed_preview_data()

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                startup_result = await run_startup_scenario(browser)
                refresh_result, lifecycle_results = await run_refresh_and_lifecycle_scenarios(browser)
            finally:
                await browser.close()

        report = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "base_url": BASE_URL,
            "preview_db": str(PREVIEW_DB_PATH),
            "location_threshold_meters": LOCATION_THRESHOLD_METERS,
            "location_local": LOCATION_LOCAL,
            "mode": "chromium_playwright_local_instrumentation",
            "results": [startup_result, refresh_result, *lifecycle_results],
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

        if server_process.stdout is not None:
            with suppress(Exception):
                output = server_process.stdout.read().strip()
                if output:
                    print(output)


def main() -> None:
    report = asyncio.run(run_homologation())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()