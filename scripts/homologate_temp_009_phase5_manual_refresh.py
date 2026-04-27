from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PREVIEW_DB_PATH = ROOT / "preview_phase5_manual_refresh.db"
REPORT_PATH = ROOT / "docs" / "temp_009_phase5_manual_refresh_report.json"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8767
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
ADMIN_CHAVE = "HR70"
ADMIN_SENHA = "eAcacdLe2"
LOCATION_THRESHOLD_METERS = 25

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", f"sqlite:///./{PREVIEW_DB_PATH.name}")
os.environ.setdefault("FORMS_QUEUE_ENABLED", "false")
os.environ.setdefault("EVENT_ARCHIVES_DIR", str(ROOT / "preview_event_archives"))
os.environ.setdefault("ADMIN_SESSION_SECRET", "phase5-preview-secret")
os.environ.setdefault("BOOTSTRAP_ADMIN_KEY", ADMIN_CHAVE)
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", ADMIN_SENHA)
os.environ.setdefault("BOOTSTRAP_ADMIN_NAME", "Tamer Salmem")

from sqlalchemy import select

from sistema.app.database import SessionLocal
from sistema.app.models import Project


CHANGED_PROJECT = "H95"
CHECKOUT_PROJECT = "H97"
NEARBY_PROJECT = "H98"

CHANGED_BASE_LABEL = "Phase5 Sit6 Base"
CHANGED_PORTARIA_LABEL = "Phase5 Sit6 Portaria"
CHECKOUT_BASE_LABEL = "Phase5 Checkout Base"
CHECKOUT_ZONE_LABEL = "Zona de CheckOut"
CHECKOUT_ZONE_UI_LABEL = "Zona de Check-Out"
NEARBY_BASE_LABEL = "Phase5 Nearby Base"
UNREGISTERED_LABEL = "Localização não Cadastrada"
OUTSIDE_WORKPLACE_LABEL = "Fora do Ambiente de Trabalho"

CHANGED_BASE_COORDS = (1.265936, 103.621066)
CHANGED_PORTARIA_COORDS = (1.275936, 103.631066)
CHECKOUT_BASE_COORDS = (1.285936, 103.641066)
CHECKOUT_ZONE_COORDS = (1.255936, 103.611066)
NEARBY_BASE_COORDS = (1.305936, 103.651066)
NEARBY_OUTSIDE_POINT = (1.307186, 103.652316)

SCENARIOS = (
    {
        "name": "manual_refresh_changed_location_triggers_new_checkin",
        "chave": "T9A1",
        "senha": "abc123",
        "project": CHANGED_PROJECT,
        "seed_local": CHANGED_BASE_LABEL,
        "startup_point": CHANGED_BASE_COORDS,
        "refresh_point": CHANGED_PORTARIA_COORDS,
        "expected_action": "checkin",
        "expected_local": CHANGED_PORTARIA_LABEL,
        "expected_label": CHANGED_PORTARIA_LABEL,
        "expect_timestamp_change": True,
    },
    {
        "name": "manual_refresh_same_location_does_not_duplicate_checkin",
        "chave": "T9B2",
        "senha": "abc123",
        "project": CHANGED_PROJECT,
        "seed_local": CHANGED_BASE_LABEL,
        "startup_point": CHANGED_BASE_COORDS,
        "refresh_point": CHANGED_BASE_COORDS,
        "expected_action": "checkin",
        "expected_local": CHANGED_BASE_LABEL,
        "expected_label": CHANGED_BASE_LABEL,
        "expect_timestamp_change": False,
    },
    {
        "name": "manual_refresh_checkout_zone_triggers_checkout",
        "chave": "T9C3",
        "senha": "abc123",
        "project": CHECKOUT_PROJECT,
        "seed_local": CHECKOUT_BASE_LABEL,
        "startup_point": CHECKOUT_BASE_COORDS,
        "refresh_point": CHECKOUT_ZONE_COORDS,
        "expected_action": "checkout",
        "expected_local": CHECKOUT_ZONE_LABEL,
        "expected_label": CHECKOUT_ZONE_UI_LABEL,
        "expect_timestamp_change": True,
    },
    {
        "name": "manual_refresh_nearby_unregistered_keeps_existing_checkin",
        "chave": "T9D4",
        "senha": "abc123",
        "project": NEARBY_PROJECT,
        "seed_local": NEARBY_BASE_LABEL,
        "startup_point": NEARBY_BASE_COORDS,
        "refresh_point": NEARBY_OUTSIDE_POINT,
        "expected_action": "checkin",
        "expected_local": NEARBY_BASE_LABEL,
        "expected_label": UNREGISTERED_LABEL,
        "accepted_labels": [UNREGISTERED_LABEL, OUTSIDE_WORKPLACE_LABEL],
        "expect_timestamp_change": False,
        "expect_unregistered_ui": True,
    },
)


def ensure_project_exists(project_name: str) -> None:
    normalized_name = str(project_name).strip().upper()
    with SessionLocal() as db:
        existing = db.execute(select(Project).where(Project.name == normalized_name)).scalar_one_or_none()
        if existing is not None:
            return
        db.add(
            Project(
                name=normalized_name,
                country_code="SG",
                country_name="Singapore",
                timezone_name="Asia/Singapore",
            )
        )
        db.commit()


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


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


def build_point_inside(base_coords: tuple[float, float]) -> tuple[float, float]:
    return (base_coords[0] + 0.00005, base_coords[1] + 0.00005)


def build_sequence(latitude: float, longitude: float) -> list[dict[str, object]]:
    return [
        {
            "delay_ms": 900,
            "position": {"latitude": latitude, "longitude": longitude, "accuracy": 42},
        },
        {
            "delay_ms": 1800,
            "position": {"latitude": latitude, "longitude": longitude, "accuracy": 18},
        },
        {
            "delay_ms": 3300,
            "position": {"latitude": latitude, "longitude": longitude, "accuracy": 8},
        },
    ]


def build_init_script(
    *,
    chave: str,
    senha: str,
    project: str,
    automatic_enabled: bool,
    initial_sequence: list[dict[str, object]],
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
  const geoStorageKey = '__temp009_geo_sequence__';

  window.localStorage.setItem('checking.web.user.chave', persistedChave);
  window.localStorage.setItem('checking.web.user.password.by-chave', JSON.stringify(persistedPasswordMap));
  window.localStorage.setItem('checking.web.user.settings.by-chave', JSON.stringify(persistedSettingsMap));
  window.localStorage.setItem('checking.web.user.location.permission-granted', '1');
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

  window.__temp009GeoMock__ = geoMock;
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


async def login_admin_client() -> httpx.AsyncClient:
    client = httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=10.0)
    response = await client.post(
        "/api/admin/auth/login",
        json={"chave": ADMIN_CHAVE, "senha": ADMIN_SENHA},
    )
    response.raise_for_status()
    return client


async def create_location(
    client: httpx.AsyncClient,
    *,
    local: str,
    project: str,
    base_coords: tuple[float, float],
    tolerance_meters: int,
) -> None:
    response = await client.post(
        "/api/admin/locations",
        json={
            "local": local,
            "coordinates": build_rectangle_coordinates(*base_coords),
            "projects": [project],
            "tolerance_meters": tolerance_meters,
        },
    )
    response.raise_for_status()


async def create_web_user_with_initial_checkin(
    *,
    chave: str,
    senha: str,
    projeto: str,
    local: str,
) -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True, timeout=10.0) as client:
        register_response = await client.post(
            "/api/web/auth/register-user",
            json={
                "chave": chave,
                "nome": f"Homologacao {chave}",
                "projeto": projeto,
                "email": "",
                "senha": senha,
                "confirmar_senha": senha,
            },
        )
        register_response.raise_for_status()

        login_response = await client.post(
            "/api/web/auth/login",
            json={"chave": chave, "senha": senha},
        )
        login_response.raise_for_status()

        submit_response = await client.post(
            "/api/web/check",
            json={
                "chave": chave,
                "projeto": projeto,
                "action": "checkin",
                "local": local,
                "informe": "normal",
                "event_time": datetime.now(timezone.utc).isoformat(),
                "client_event_id": f"seed-{chave.lower()}-{int(time.time() * 1000)}",
            },
        )
        submit_response.raise_for_status()


async def seed_preview_data() -> None:
    for project in (CHANGED_PROJECT, CHECKOUT_PROJECT, NEARBY_PROJECT):
        ensure_project_exists(project)

    admin_client = await login_admin_client()
    try:
        settings_response = await admin_client.post(
            "/api/admin/locations/settings",
            json={"location_accuracy_threshold_meters": LOCATION_THRESHOLD_METERS},
        )
        settings_response.raise_for_status()

        await create_location(
            admin_client,
            local=CHANGED_BASE_LABEL,
            project=CHANGED_PROJECT,
            base_coords=CHANGED_BASE_COORDS,
            tolerance_meters=90,
        )
        await create_location(
            admin_client,
            local=CHANGED_PORTARIA_LABEL,
            project=CHANGED_PROJECT,
            base_coords=CHANGED_PORTARIA_COORDS,
            tolerance_meters=90,
        )
        await create_location(
            admin_client,
            local=CHECKOUT_BASE_LABEL,
            project=CHECKOUT_PROJECT,
            base_coords=CHECKOUT_BASE_COORDS,
            tolerance_meters=120,
        )
        await create_location(
            admin_client,
            local=CHECKOUT_ZONE_LABEL,
            project=CHECKOUT_PROJECT,
            base_coords=CHECKOUT_ZONE_COORDS,
            tolerance_meters=20,
        )
        await create_location(
            admin_client,
            local=NEARBY_BASE_LABEL,
            project=NEARBY_PROJECT,
            base_coords=NEARBY_BASE_COORDS,
            tolerance_meters=90,
        )
    finally:
        await admin_client.aclose()

    for scenario in SCENARIOS:
        await create_web_user_with_initial_checkin(
            chave=str(scenario["chave"]),
            senha=str(scenario["senha"]),
            projeto=str(scenario["project"]),
            local=str(scenario["seed_local"]),
        )


async def create_authenticated_page(browser, scenario: dict[str, object]):
    startup_point = build_point_inside(tuple(scenario["startup_point"]))
    context = await browser.new_context(base_url=BASE_URL, viewport={"width": 430, "height": 932})
    await context.grant_permissions(["geolocation"], origin=BASE_URL)
    await context.add_init_script(
        build_init_script(
            chave=str(scenario["chave"]),
            senha=str(scenario["senha"]),
            project=str(scenario["project"]),
            automatic_enabled=True,
            initial_sequence=build_sequence(*startup_point),
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


async def wait_for_authenticated_ui_ready(page, *, expected_location: str, timeout_ms: float = 20000) -> None:
    await page.wait_for_function(
        """(expectedLocation) => {
          const projectSelect = document.querySelector('#projectSelect');
          const passwordInput = document.querySelector('#passwordInput');
          const submitButton = document.querySelector('#submitButton');
          const toggle = document.querySelector('#automaticActivitiesToggle');
          const refreshButton = document.querySelector('#refreshLocationButton');
          const locationValue = (document.querySelector('#locationValue')?.textContent || '').trim();
          return Boolean(
            projectSelect
            && projectSelect.options.length > 0
            && passwordInput
            && passwordInput.value.length >= 3
            && submitButton
            && toggle
            && toggle.checked === true
            && refreshButton
            && refreshButton.getAttribute('aria-busy') === 'false'
            && locationValue === expectedLocation
          );
        }""",
        arg=expected_location,
        timeout=timeout_ms,
    )


async def set_browser_sequence(page, point: tuple[float, float]) -> None:
    await page.evaluate(
        """(sequence) => {
          window.__temp009GeoMock__.setSequence(sequence);
        }""",
        build_sequence(*point),
    )


async def trigger_manual_refresh(page, point: tuple[float, float]) -> None:
    await set_browser_sequence(page, point)
    await page.locator("#refreshLocationButton").click()
    await page.wait_for_function(
        """() => document.querySelector('#refreshLocationButton')?.getAttribute('aria-busy') === 'true'""",
        timeout=5000,
    )


async def wait_for_refresh_idle(page, *, timeout_ms: float = 15000) -> None:
    await page.wait_for_function(
        """() => document.querySelector('#refreshLocationButton')?.getAttribute('aria-busy') === 'false'""",
        timeout=timeout_ms,
    )


async def fetch_state(page, chave: str) -> dict[str, object]:
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
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unable to fetch state for {chave}")
    return payload


async def wait_for_state(page, chave: str, predicate, *, timeout_seconds: float = 15.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        payload = await fetch_state(page, chave)
        if predicate(payload):
            return payload
        await asyncio.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for state condition on chave={chave}")


async def read_ui_state(page) -> dict[str, object]:
    return await page.evaluate(
        """() => ({
          locationValue: (document.querySelector('#locationValue')?.textContent || '').trim(),
          automaticChecked: Boolean(document.querySelector('#automaticActivitiesToggle')?.checked),
          statusPrimary: (document.querySelector('#notificationLinePrimary')?.textContent || '').trim(),
          statusSecondary: (document.querySelector('#notificationLineSecondary')?.textContent || '').trim(),
        })"""
    )


async def run_manual_refresh_scenario(browser, scenario: dict[str, object]) -> dict[str, object]:
    context, page = await create_authenticated_page(browser, scenario)
    try:
        expected_startup_location = str(scenario["seed_local"])
        await wait_for_authenticated_ui_ready(page, expected_location=expected_startup_location)

        initial_state = await fetch_state(page, str(scenario["chave"]))
        initial_checkin_at = initial_state.get("last_checkin_at")
        initial_checkout_at = initial_state.get("last_checkout_at")

        await trigger_manual_refresh(page, tuple(scenario["refresh_point"]))

        if bool(scenario.get("expect_unregistered_ui")):
            await page.wait_for_function(
                                """(acceptedLabels) => {
                  const locationValue = (document.querySelector('#locationValue')?.textContent || '').trim();
                  const refreshBusy = document.querySelector('#refreshLocationButton')?.getAttribute('aria-busy');
                                    return Array.isArray(acceptedLabels) && acceptedLabels.includes(locationValue) && refreshBusy === 'false';
                }""",
                                arg=list(scenario.get("accepted_labels") or [str(scenario["expected_label"])]),
                timeout=15000,
            )
            await asyncio.sleep(1.0)
            final_state = await fetch_state(page, str(scenario["chave"]))
        elif str(scenario["expected_action"]) == "checkout":
            final_state = await wait_for_state(
                page,
                str(scenario["chave"]),
                lambda payload: payload.get("current_action") == "checkout"
                and payload.get("current_local") == scenario["expected_local"]
                and payload.get("last_checkout_at") != initial_checkout_at,
            )
        elif bool(scenario["expect_timestamp_change"]):
            final_state = await wait_for_state(
                page,
                str(scenario["chave"]),
                lambda payload: payload.get("current_action") == "checkin"
                and payload.get("current_local") == scenario["expected_local"]
                and payload.get("last_checkin_at") != initial_checkin_at,
            )
        else:
            await wait_for_refresh_idle(page)
            await asyncio.sleep(1.0)
            final_state = await fetch_state(page, str(scenario["chave"]))

        ui_state = await read_ui_state(page)

        assert_condition(ui_state["automaticChecked"] is True, f"Automatic toggle should stay enabled on {scenario['name']}")
        assert_condition(ui_state["locationValue"] == scenario["expected_label"], f"Unexpected location label on {scenario['name']}: {ui_state['locationValue']}")
        assert_condition(final_state.get("current_action") == scenario["expected_action"], f"Unexpected current_action on {scenario['name']}: {final_state}")
        assert_condition(final_state.get("current_local") == scenario["expected_local"], f"Unexpected current_local on {scenario['name']}: {final_state}")

        if bool(scenario["expect_timestamp_change"]):
            if str(scenario["expected_action"]) == "checkout":
                assert_condition(final_state.get("last_checkout_at") != initial_checkout_at, f"Expected checkout timestamp change on {scenario['name']}")
            else:
                assert_condition(final_state.get("last_checkin_at") != initial_checkin_at, f"Expected checkin timestamp change on {scenario['name']}")
        else:
            assert_condition(final_state.get("last_checkin_at") == initial_checkin_at, f"Unexpected duplicate checkin on {scenario['name']}")
            assert_condition(final_state.get("last_checkout_at") == initial_checkout_at, f"Unexpected checkout change on {scenario['name']}")

        return {
            "scenario": scenario["name"],
            "initial_state": initial_state,
            "final_state": final_state,
            "ui_state": ui_state,
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
            "ADMIN_SESSION_SECRET": "phase5-preview-secret",
            "BOOTSTRAP_ADMIN_KEY": ADMIN_CHAVE,
            "BOOTSTRAP_ADMIN_PASSWORD": ADMIN_SENHA,
            "BOOTSTRAP_ADMIN_NAME": "Tamer Salmem",
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
        await wait_for_health()
        await seed_preview_data()

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                results = [
                    await run_manual_refresh_scenario(browser, scenario)
                    for scenario in SCENARIOS
                ]
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