from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import threading
import time
from contextlib import closing, contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import uvicorn
from playwright.async_api import Page, async_playwright
from sqlalchemy import select


ROOT = Path(__file__).resolve().parents[1]
PREVIEW_DB_PATH = ROOT / "preview_phase13_homologation.db"
REPORT_PATH = ROOT / "docs" / "temp_005_phase13_report.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TARGET_ADMIN_KEY = "A130"
TARGET_ADMIN_PASSWORD = "scope123"
PENDING_REQUEST_KEY = "A133"
RESTRICTED_REWRITE_KEY = "A131"
FALLBACK_REWRITE_KEY = "A132"
NEW_PROJECT_NAME = "P91"
NEW_PROJECT_COUNTRY_CODE = "SG"
NEW_PROJECT_COUNTRY_NAME = "Singapura"
NEW_PROJECT_TIMEZONE_NAME = "Asia/Singapore"


def configure_preview_environment() -> None:
    os.environ.setdefault("APP_ENV", "development")
    os.environ["DATABASE_URL"] = f"sqlite:///./{PREVIEW_DB_PATH.name}"
    os.environ["FORMS_QUEUE_ENABLED"] = "false"
    os.environ["EVENT_ARCHIVES_DIR"] = str(ROOT / "preview_event_archives")
    os.environ["ADMIN_SESSION_SECRET"] = "phase13-preview-secret"


configure_preview_environment()

from sistema.app.database import SessionLocal, engine  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import AdminAccessRequest, Base, Project, User  # noqa: E402
from sistema.app.services.admin_auth import seed_default_admin  # noqa: E402
from sistema.app.services.admin_project_scope import dump_admin_monitored_projects  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402
from sistema.app.services.project_catalog import seed_default_projects  # noqa: E402


def now_sgt() -> datetime:
    return datetime.now(ZoneInfo("Asia/Singapore"))


def reserve_tcp_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


@contextmanager
def live_app_server() -> str:
    port = reserve_tcp_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if getattr(server, "started", False):
            break
        try:
            with closing(socket.create_connection(("127.0.0.1", port), timeout=0.2)):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Timed out waiting for the preview admin server to start.")

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def reset_preview_database() -> None:
    if PREVIEW_DB_PATH.exists():
        PREVIEW_DB_PATH.unlink()
    Base.metadata.create_all(bind=engine)
    seed_default_projects()
    seed_default_admin()


def seed_phase13_fixtures() -> None:
    current_time = now_sgt()
    recent_time = current_time - timedelta(hours=1)
    stale_time = current_time - timedelta(hours=26)

    with SessionLocal() as db:
        db.add(
            User(
                rfid=None,
                chave=TARGET_ADMIN_KEY,
                senha=hash_password(TARGET_ADMIN_PASSWORD),
                perfil=1,
                nome="Admin Homologacao Fase 13",
                projeto="P80",
                local=None,
                checkin=None,
                time=None,
                last_active_at=current_time,
                inactivity_days=0,
                admin_monitored_projects_json=None,
            )
        )
        db.add(
            AdminAccessRequest(
                chave=PENDING_REQUEST_KEY,
                nome_completo="Admin Pendente Fase 13",
                password_hash=hash_password("abc123"),
                requested_profile=1,
                requested_at=current_time,
            )
        )
        db.add_all(
            [
                User(
                    rfid=None,
                    chave="I800",
                    nome="Checkin P80",
                    projeto="P80",
                    local="Porta 80",
                    checkin=True,
                    time=recent_time,
                    last_active_at=recent_time,
                    inactivity_days=0,
                ),
                User(
                    rfid=None,
                    chave="I820",
                    nome="Checkin P82",
                    projeto="P82",
                    local="Porta 82",
                    checkin=True,
                    time=recent_time,
                    last_active_at=recent_time,
                    inactivity_days=0,
                ),
                User(
                    rfid=None,
                    chave="I830",
                    nome="Checkin P83",
                    projeto="P83",
                    local="Porta 83",
                    checkin=True,
                    time=recent_time,
                    last_active_at=recent_time,
                    inactivity_days=0,
                ),
                User(
                    rfid=None,
                    chave="O800",
                    nome="Checkout P80",
                    projeto="P80",
                    local="Saida 80",
                    checkin=False,
                    time=recent_time,
                    last_active_at=recent_time,
                    inactivity_days=0,
                ),
                User(
                    rfid=None,
                    chave="O820",
                    nome="Checkout P82",
                    projeto="P82",
                    local="Saida 82",
                    checkin=False,
                    time=recent_time,
                    last_active_at=recent_time,
                    inactivity_days=0,
                ),
                User(
                    rfid=None,
                    chave="O830",
                    nome="Checkout P83",
                    projeto="P83",
                    local="Saida 83",
                    checkin=False,
                    time=recent_time,
                    last_active_at=recent_time,
                    inactivity_days=0,
                ),
                User(
                    rfid=None,
                    chave="N800",
                    nome="Inativo P80",
                    projeto="P80",
                    local="Inativo 80",
                    checkin=True,
                    time=stale_time,
                    last_active_at=stale_time,
                    inactivity_days=1,
                ),
                User(
                    rfid=None,
                    chave="N820",
                    nome="Inativo P82",
                    projeto="P82",
                    local="Inativo 82",
                    checkin=False,
                    time=stale_time,
                    last_active_at=stale_time,
                    inactivity_days=1,
                ),
                User(
                    rfid=None,
                    chave="N830",
                    nome="Inativo P83",
                    projeto="P83",
                    local="Inativo 83",
                    checkin=False,
                    time=stale_time,
                    last_active_at=stale_time,
                    inactivity_days=1,
                ),
            ]
        )
        db.commit()


def seed_new_project_visibility_fixture() -> None:
    recent_time = now_sgt() - timedelta(hours=1)
    with SessionLocal() as db:
        db.add(
            User(
                rfid=None,
                chave="I910",
                nome="Checkin P91",
                projeto=NEW_PROJECT_NAME,
                local="Porta 91",
                checkin=True,
                time=recent_time,
                last_active_at=recent_time,
                inactivity_days=0,
            )
        )
        db.commit()


def seed_project_removal_scope_fixtures() -> None:
    current_time = now_sgt()
    with SessionLocal() as db:
        db.add_all(
            [
                User(
                    rfid=None,
                    chave=RESTRICTED_REWRITE_KEY,
                    senha=hash_password("scope123"),
                    perfil=1,
                    nome="Admin Rewrite Restrito",
                    projeto="P80",
                    local=None,
                    checkin=None,
                    time=None,
                    last_active_at=current_time,
                    inactivity_days=0,
                    admin_monitored_projects_json=dump_admin_monitored_projects(["P80", NEW_PROJECT_NAME]),
                ),
                User(
                    rfid=None,
                    chave=FALLBACK_REWRITE_KEY,
                    senha=hash_password("scope123"),
                    perfil=1,
                    nome="Admin Rewrite Fallback",
                    projeto="P80",
                    local=None,
                    checkin=None,
                    time=None,
                    last_active_at=current_time,
                    inactivity_days=0,
                    admin_monitored_projects_json=dump_admin_monitored_projects([NEW_PROJECT_NAME]),
                ),
            ]
        )
        db.commit()


def remove_new_project_visibility_fixture() -> None:
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.chave == "I910")).scalar_one_or_none()
        if user is not None:
            db.delete(user)
            db.commit()


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def find_browser_executable() -> str | None:
    candidates = [
        os.environ.get("CHECKING_CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


async def wait_for_health(base_url: str, timeout_seconds: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    async with httpx.AsyncClient(base_url=base_url, timeout=2.0) as client:
        while time.monotonic() < deadline:
            try:
                response = await client.get("/api/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.2)
    raise TimeoutError("Timed out waiting for the preview server health check.")


async def login_api_client(base_url: str, chave: str, senha: str) -> httpx.AsyncClient:
    client = httpx.AsyncClient(base_url=base_url, follow_redirects=True, timeout=10.0)
    response = await client.post("/api/admin/auth/login", json={"chave": chave, "senha": senha})
    response.raise_for_status()
    return client


async def wait_for_admin_shell(page: Page) -> None:
    await page.wait_for_function(
        """() => {
          const authShell = document.getElementById("authShell");
          const adminShell = document.getElementById("adminShell");
          return authShell && adminShell && authShell.classList.contains("hidden") && !adminShell.classList.contains("hidden");
        }""",
        timeout=15000,
    )


async def login_in_ui(page: Page, chave: str, senha: str) -> None:
    await page.goto("/admin", wait_until="domcontentloaded")
    await page.locator("#loginChave").wait_for(timeout=15000)
    await page.fill("#loginChave", chave)
    await page.fill("#loginSenha", senha)
    await page.click("#loginButton")
    await wait_for_admin_shell(page)
    await page.wait_for_function(
        """() => {
          const body = document.getElementById("checkinBody");
          return Boolean(body && body.textContent && body.textContent.trim().length > 0);
        }""",
        timeout=15000,
    )


async def reload_logged_page(page: Page) -> None:
    await page.reload(wait_until="domcontentloaded")
    await wait_for_admin_shell(page)
    await page.wait_for_function(
        """() => {
          const body = document.getElementById("checkinBody");
          return Boolean(body && body.textContent && body.textContent.trim().length > 0);
        }""",
        timeout=15000,
    )


async def switch_tab(page: Page, tab_name: str) -> None:
    await page.click(f'.tabs button[data-tab="{tab_name}"]')
    await page.wait_for_function(
        """(tab) => {
          const section = document.getElementById(`tab-${tab}`);
          return Boolean(section && section.classList.contains("active"));
        }""",
        arg=tab_name,
        timeout=10000,
    )


async def wait_for_body_text(page: Page, body_selector: str, text: str) -> None:
    await page.wait_for_function(
        """([selector, expectedText]) => {
          const body = document.querySelector(selector);
          return Boolean(body && body.textContent && body.textContent.includes(expectedText));
        }""",
        arg=[body_selector, text],
        timeout=15000,
    )


async def get_body_text(page: Page, body_selector: str) -> str:
    return await page.locator(body_selector).inner_text()


async def get_admin_row(page: Page, admin_key: str):
    row = page.locator("#administratorsBody tr").filter(has_text=admin_key).first
    await row.wait_for(state="attached", timeout=15000)
    return row


async def get_checked_projects(page: Page, admin_key: str) -> list[str]:
    row = await get_admin_row(page, admin_key)
    values = await row.locator('input[data-admin-project-option]').evaluate_all(
        "nodes => nodes.filter((node) => node.checked).map((node) => node.value).sort()"
    )
    return [str(value) for value in values]


async def set_admin_scope(page: Page, admin_key: str, expected_projects: list[str]) -> None:
    await switch_tab(page, "cadastro")
    row = await get_admin_row(page, admin_key)
    checkboxes = row.locator('input[data-admin-project-option]')
    count = await checkboxes.count()
    assert_condition(count > 0, f"Expected project checkboxes for admin {admin_key}.")
    for index in range(count):
        checkbox = checkboxes.nth(index)
        value = await checkbox.get_attribute("value")
        if value in expected_projects:
            await checkbox.check()
        else:
            await checkbox.uncheck()
    await row.locator('button[data-admin-profile-save]').click()
    await page.wait_for_function(
        """([chave, projects]) => {
          const row = [...document.querySelectorAll("#administratorsBody tr")].find((candidate) => candidate.textContent.includes(chave));
          if (!row) {
            return false;
          }
          const checked = [...row.querySelectorAll('input[data-admin-project-option]')]
            .filter((input) => input.checked)
            .map((input) => input.value)
            .sort();
          const expected = [...projects].sort();
          return JSON.stringify(checked) === JSON.stringify(expected);
        }""",
        arg=[admin_key, expected_projects],
        timeout=15000,
    )
    await reload_logged_page(page)


async def assert_request_row_readonly(page: Page) -> dict[str, Any]:
    await switch_tab(page, "cadastro")
    row = await get_admin_row(page, PENDING_REQUEST_KEY)
    body_text = await row.inner_text()
    checkbox_count = await row.locator('input[data-admin-project-option]').count()
    assert_condition(
        "Defina os projetos apos aprovar o administrador." in body_text,
        "Pending request row should keep the readonly helper copy.",
    )
    assert_condition(checkbox_count == 0, "Pending request row should not render editable project checkboxes.")
    return {
        "scenario": "pending_request_readonly",
        "row_text": body_text.strip(),
        "checkbox_count": checkbox_count,
    }


async def assert_presence_scope(
    page: Page,
    *,
    scenario_name: str,
    expected_checkin: list[str],
    excluded_checkin: list[str],
    expected_checkout: list[str],
    excluded_checkout: list[str],
    expected_inactive: list[str],
    excluded_inactive: list[str],
) -> dict[str, Any]:
    await switch_tab(page, "checkin")
    await wait_for_body_text(page, "#checkinBody", expected_checkin[0])
    checkin_text = await get_body_text(page, "#checkinBody")
    for value in expected_checkin:
        assert_condition(value in checkin_text, f"Expected {value} in Check-In for {scenario_name}.")
    for value in excluded_checkin:
        assert_condition(value not in checkin_text, f"Did not expect {value} in Check-In for {scenario_name}.")

    await switch_tab(page, "checkout")
    await wait_for_body_text(page, "#checkoutBody", expected_checkout[0])
    checkout_text = await get_body_text(page, "#checkoutBody")
    for value in expected_checkout:
        assert_condition(value in checkout_text, f"Expected {value} in Check-Out for {scenario_name}.")
    for value in excluded_checkout:
        assert_condition(value not in checkout_text, f"Did not expect {value} in Check-Out for {scenario_name}.")

    await switch_tab(page, "inactive")
    await wait_for_body_text(page, "#inactiveBody", expected_inactive[0])
    inactive_text = await get_body_text(page, "#inactiveBody")
    for value in expected_inactive:
        assert_condition(value in inactive_text, f"Expected {value} in Inativos for {scenario_name}.")
    for value in excluded_inactive:
        assert_condition(value not in inactive_text, f"Did not expect {value} in Inativos for {scenario_name}.")

    return {
        "scenario": scenario_name,
        "checkin_matches": expected_checkin,
        "checkout_matches": expected_checkout,
        "inactive_matches": expected_inactive,
    }


async def create_project_via_api(client: httpx.AsyncClient, project_name: str) -> dict[str, Any]:
    response = await client.post(
        "/api/admin/projects",
        json={
            "name": project_name,
            "country_code": NEW_PROJECT_COUNTRY_CODE,
            "country_name": NEW_PROJECT_COUNTRY_NAME,
            "timezone_name": NEW_PROJECT_TIMEZONE_NAME,
        },
    )
    response.raise_for_status()
    return response.json()


async def delete_project_via_api(client: httpx.AsyncClient, project_id: int) -> None:
    response = await client.delete(f"/api/admin/projects/{project_id}")
    response.raise_for_status()


async def validate_new_project_all_mode(page: Page, client: httpx.AsyncClient) -> dict[str, Any]:
    project_payload = await create_project_via_api(client, NEW_PROJECT_NAME)
    seed_new_project_visibility_fixture()
    await reload_logged_page(page)
    checked_projects = await get_checked_projects(page, TARGET_ADMIN_KEY)
    assert_condition(NEW_PROJECT_NAME in checked_projects, "All-mode admin should automatically include the newly created project.")
    await switch_tab(page, "checkin")
    await wait_for_body_text(page, "#checkinBody", "Checkin P91")
    checkin_text = await get_body_text(page, "#checkinBody")
    assert_condition("Checkin P91" in checkin_text, "All-mode admin should see the newly created project in Check-In.")
    return {
        "scenario": "new_project_all_mode",
        "project_name": NEW_PROJECT_NAME,
        "project_id": project_payload["id"],
        "checked_projects": checked_projects,
        "checkin_contains": "Checkin P91",
    }


async def validate_project_removal_scope_rewrite(page: Page, client: httpx.AsyncClient, project_id: int) -> dict[str, Any]:
    seed_project_removal_scope_fixtures()
    await reload_logged_page(page)
    await switch_tab(page, "cadastro")
    before_restricted = await get_checked_projects(page, RESTRICTED_REWRITE_KEY)
    before_fallback = await get_checked_projects(page, FALLBACK_REWRITE_KEY)
    assert_condition(before_restricted == ["P80", NEW_PROJECT_NAME], "Restricted rewrite admin should start with P80 + new project.")
    assert_condition(before_fallback == [NEW_PROJECT_NAME], "Fallback rewrite admin should start only with the new project.")

    remove_new_project_visibility_fixture()
    await delete_project_via_api(client, project_id)
    await reload_logged_page(page)
    await switch_tab(page, "cadastro")
    restricted_after = await get_checked_projects(page, RESTRICTED_REWRITE_KEY)
    fallback_after = await get_checked_projects(page, FALLBACK_REWRITE_KEY)
    target_after = await get_checked_projects(page, TARGET_ADMIN_KEY)
    assert_condition(restricted_after == ["P80"], "Restricted rewrite admin should keep only P80 after project removal.")
    assert_condition(fallback_after == ["P80", "P82", "P83"], "Fallback rewrite admin should reset to all remaining projects after project removal.")
    assert_condition(target_after == ["P80", "P82", "P83"], "All-mode admin should continue seeing all remaining projects after project removal.")
    return {
        "scenario": "project_removal_scope_rewrite",
        "removed_project": NEW_PROJECT_NAME,
        "restricted_before": before_restricted,
        "fallback_before": before_fallback,
        "restricted_after": restricted_after,
        "fallback_after": fallback_after,
        "target_after": target_after,
    }


async def run_homologation() -> dict[str, Any]:
    reset_preview_database()
    seed_phase13_fixtures()

    with live_app_server() as base_url:
        await wait_for_health(base_url)
        api_client = await login_api_client(base_url, TARGET_ADMIN_KEY, TARGET_ADMIN_PASSWORD)
        try:
            browser_kwargs: dict[str, Any] = {"headless": True}
            browser_path = find_browser_executable()
            if browser_path is not None:
                browser_kwargs["executable_path"] = browser_path

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(**browser_kwargs)
                try:
                    context = await browser.new_context(base_url=base_url)
                    page = await context.new_page()
                    await login_in_ui(page, TARGET_ADMIN_KEY, TARGET_ADMIN_PASSWORD)

                    results: list[dict[str, Any]] = []
                    results.append(await assert_request_row_readonly(page))

                    await set_admin_scope(page, TARGET_ADMIN_KEY, ["P80"])
                    results.append(
                        await assert_presence_scope(
                            page,
                            scenario_name="scope_p80_only",
                            expected_checkin=["Checkin P80"],
                            excluded_checkin=["Checkin P82", "Checkin P83"],
                            expected_checkout=["Checkout P80"],
                            excluded_checkout=["Checkout P82", "Checkout P83"],
                            expected_inactive=["Inativo P80"],
                            excluded_inactive=["Inativo P82", "Inativo P83"],
                        )
                    )

                    await set_admin_scope(page, TARGET_ADMIN_KEY, ["P80", "P83"])
                    results.append(
                        await assert_presence_scope(
                            page,
                            scenario_name="scope_p80_p83",
                            expected_checkin=["Checkin P80", "Checkin P83"],
                            excluded_checkin=["Checkin P82"],
                            expected_checkout=["Checkout P80", "Checkout P83"],
                            excluded_checkout=["Checkout P82"],
                            expected_inactive=["Inativo P80", "Inativo P83"],
                            excluded_inactive=["Inativo P82"],
                        )
                    )

                    await set_admin_scope(page, TARGET_ADMIN_KEY, ["P80", "P82", "P83"])
                    results.append(
                        await assert_presence_scope(
                            page,
                            scenario_name="scope_all_projects",
                            expected_checkin=["Checkin P80", "Checkin P82", "Checkin P83"],
                            excluded_checkin=[],
                            expected_checkout=["Checkout P80", "Checkout P82", "Checkout P83"],
                            excluded_checkout=[],
                            expected_inactive=["Inativo P80", "Inativo P82", "Inativo P83"],
                            excluded_inactive=[],
                        )
                    )

                    new_project_result = await validate_new_project_all_mode(page, api_client)
                    results.append(new_project_result)
                    results.append(
                        await validate_project_removal_scope_rewrite(page, api_client, int(new_project_result["project_id"]))
                    )

                    await context.close()
                finally:
                    await browser.close()
        finally:
            await api_client.aclose()

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preview_db": str(PREVIEW_DB_PATH),
        "project_catalog_baseline": ["P80", "P82", "P83"],
        "target_admin": TARGET_ADMIN_KEY,
        "pending_request": PENDING_REQUEST_KEY,
        "new_project": NEW_PROJECT_NAME,
        "results": results,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = asyncio.run(run_homologation())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()