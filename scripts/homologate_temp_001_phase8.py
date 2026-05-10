from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, async_playwright


BASE_URL = os.getenv("CHECKCHECK_TRANSPORT_URL", "http://127.0.0.1:8010/transport/")
TRANSPORT_KEY = os.getenv("CHECKCHECK_TRANSPORT_KEY", "HR70")
TRANSPORT_PASSWORD = os.getenv("CHECKCHECK_TRANSPORT_PASSWORD", "eAcacdLe2")


def dashboard_response_match(response: Any) -> bool:
    request = response.request
    return "/api/transport/dashboard?" in response.url and request.method == "GET"


async def wait_for_dashboard_paint(page: Page) -> None:
    await page.wait_for_function(
        """
        () => {
          const routeInput = document.querySelector('[data-route-time-input]');
          const regularDeparture = document.querySelector('#transportVehicleScopeRegular .transport-vehicle-departure, #transportVehicleScopeRegular .transport-vehicle-management-time');
          const weekendDeparture = document.querySelector('#transportVehicleScopeWeekend .transport-vehicle-departure, #transportVehicleScopeWeekend .transport-vehicle-management-time');
          return Boolean(routeInput && !routeInput.disabled && regularDeparture && weekendDeparture);
        }
        """
    )


async def reload_dashboard(page: Page) -> None:
    async with page.expect_response(dashboard_response_match):
        await page.evaluate(
            """
            () => window.CheckingTransportPageController.loadDashboard(new Date(), { announce: false })
            """
        )
    await wait_for_dashboard_paint(page)


async def read_grid_labels(page: Page) -> dict[str, str]:
    return await page.evaluate(
        """
        () => ({
          regular: document.querySelector('#transportVehicleScopeRegular .transport-vehicle-departure')?.textContent?.trim() || '',
          weekend: document.querySelector('#transportVehicleScopeWeekend .transport-vehicle-departure')?.textContent?.trim() || '',
          regularTitle: document.querySelector('#transportVehicleScopeRegular .transport-vehicle-button')?.getAttribute('title') || '',
          weekendTitle: document.querySelector('#transportVehicleScopeWeekend .transport-vehicle-button')?.getAttribute('title') || '',
        })
        """
    )


async def read_table_labels(page: Page) -> dict[str, str]:
    return await page.evaluate(
        """
        () => ({
          regular: document.querySelector('#transportVehicleScopeRegular .transport-vehicle-management-time')?.textContent?.trim() || '',
          weekend: document.querySelector('#transportVehicleScopeWeekend .transport-vehicle-management-time')?.textContent?.trim() || '',
        })
        """
    )


def require_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: esperado {expected!r}, obtido {actual!r}")


def require_contains(actual: str, expected_fragment: str, message: str) -> None:
    if expected_fragment not in actual:
        raise AssertionError(
            f"{message}: esperado conter {expected_fragment!r}, obtido {actual!r}"
        )


async def measure_preference_label_wrapping(page: Page) -> dict[int, list[dict[str, float | str | bool]]]:
    wrapping_report: dict[int, list[dict[str, float | str | bool]]] = {}
    for width in (1200, 1024, 961):
        await page.set_viewport_size({"width": width, "height": 1100})
        await page.wait_for_timeout(100)
        metrics = await page.evaluate(
            """
            () => Array.from(document.querySelectorAll('.transport-settings-section-preferences .transport-settings-label')).map((element) => {
              const style = window.getComputedStyle(element);
              const height = element.getBoundingClientRect().height;
              const lineHeight = Number.parseFloat(style.lineHeight);
              return {
                text: element.textContent.trim(),
                height,
                lineHeight,
                wraps: Number.isFinite(lineHeight) && lineHeight > 0 ? height > (lineHeight * 1.35) : false,
              };
            })
            """
        )
        wrapped = [item for item in metrics if item.get("wraps")]
        if wrapped:
            raise AssertionError(
                f"Labels do bloco Preferences quebraram linha antes do breakpoint mobile em {width}px: {wrapped}"
            )
        wrapping_report[width] = metrics
    return wrapping_report


async def main() -> None:
    forced_dashboard_generated_at: str | None = None
    report: dict[str, Any] = {"base_url": BASE_URL}

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1280, "height": 1100})
            page = await context.new_page()

            async def handle_dashboard_route(route: Any) -> None:
                response = await route.fetch()
                payload = await response.json()
                if forced_dashboard_generated_at:
                    payload["dashboard_generated_at"] = forced_dashboard_generated_at
                await route.fulfill(response=response, json=payload)

            await page.route("**/api/transport/dashboard?*", handle_dashboard_route)

            await page.goto(BASE_URL, wait_until="networkidle")
            await page.locator("[data-transport-auth-key]").fill(TRANSPORT_KEY)
            await page.locator("[data-transport-auth-password]").fill(TRANSPORT_PASSWORD)
            async with page.expect_response(
                lambda response: "/api/transport/auth/verify" in response.url
                and response.request.method == "POST"
            ):
                await page.locator("[data-transport-auth-password]").blur()
            await wait_for_dashboard_paint(page)

            await page.locator("[data-open-settings-modal]").click()
            await page.locator("[data-settings-modal]").wait_for(state="visible")
            arrive_at_work_time = await page.locator("[data-settings-arrive-at-work-time]").input_value()
            work_to_home_time = await page.locator("[data-settings-work-to-home-time]").input_value()
            inline_work_to_home_time = await page.locator("[data-route-time-input]").input_value()
            require_equal(arrive_at_work_time, "07:45", "Default Arrive at Work")
            require_equal(work_to_home_time, "16:45", "Default Work to Home Time")
            require_equal(inline_work_to_home_time, "16:45", "Default topbar Work to Home Time")
            report["defaults"] = {
                "arrive_at_work_time": arrive_at_work_time,
                "work_to_home_time": work_to_home_time,
                "topbar_work_to_home_time": inline_work_to_home_time,
            }
            await page.locator(".transport-modal-close[data-close-settings-modal]").click()
            await page.locator("[data-settings-modal]").wait_for(state="hidden")

            forced_dashboard_generated_at = "2026-05-07T14:00:00+08:00"
            await reload_dashboard(page)
            daytime_labels = await read_grid_labels(page)
            require_equal(daytime_labels["regular"], "ETD 16:45h", "Label REGULAR em horario diurno")
            require_equal(daytime_labels["weekend"], "ETD 16:45h", "Label WEEKEND em horario diurno")
            require_contains(daytime_labels["regularTitle"], "ETD 16:45h", "Title REGULAR em horario diurno")
            require_contains(daytime_labels["weekendTitle"], "ETD 16:45h", "Title WEEKEND em horario diurno")
            report["daytime"] = daytime_labels

            forced_dashboard_generated_at = "2026-05-07T05:00:00+08:00"
            await reload_dashboard(page)
            nighttime_labels = await read_grid_labels(page)
            require_equal(nighttime_labels["regular"], "ETA 07:45h", "Label REGULAR em horario noturno")
            require_equal(nighttime_labels["weekend"], "ETA 07:45h", "Label WEEKEND em horario noturno")
            require_contains(nighttime_labels["regularTitle"], "ETA 07:45h", "Title REGULAR em horario noturno")
            require_contains(nighttime_labels["weekendTitle"], "ETA 07:45h", "Title WEEKEND em horario noturno")
            report["nighttime"] = nighttime_labels

            forced_dashboard_generated_at = "2026-05-07T14:00:00+08:00"
            async with page.expect_response(
                lambda response: "/api/transport/date-settings" in response.url
                and response.request.method == "PUT"
            ), page.expect_response(dashboard_response_match):
                await page.locator("[data-route-time-input]").evaluate(
                    """
                    (input, nextValue) => {
                      input.value = nextValue;
                      input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    """,
                    "18:10",
                )
            await wait_for_dashboard_paint(page)
            inline_override_daytime = await read_grid_labels(page)
            require_equal(
                inline_override_daytime["regular"],
                "ETD 18:10h",
                "Label REGULAR apos override inline em horario diurno",
            )
            require_equal(
                inline_override_daytime["weekend"],
                "ETD 18:10h",
                "Label WEEKEND apos override inline em horario diurno",
            )
            require_equal(
                await page.locator("[data-route-time-input]").input_value(),
                "18:10",
                "Valor do campo inline apos override",
            )

            forced_dashboard_generated_at = "2026-05-07T05:00:00+08:00"
            await reload_dashboard(page)
            inline_override_nighttime = await read_grid_labels(page)
            require_equal(
                inline_override_nighttime["regular"],
                "ETA 07:45h",
                "Label REGULAR apos override inline em horario noturno",
            )
            require_equal(
                inline_override_nighttime["weekend"],
                "ETA 07:45h",
                "Label WEEKEND apos override inline em horario noturno",
            )
            report["inline_override"] = {
                "daytime": inline_override_daytime,
                "nighttime": inline_override_nighttime,
                "topbar_value": await page.locator("[data-route-time-input]").input_value(),
            }

            forced_dashboard_generated_at = "2026-05-07T14:00:00+08:00"
            await reload_dashboard(page)
            await page.locator('[data-toggle-vehicle-view="regular"]').click()
            await page.locator('[data-toggle-vehicle-view="weekend"]').click()
            await page.locator("#transportVehicleScopeRegular .transport-vehicle-management-table").wait_for()
            await page.locator("#transportVehicleScopeWeekend .transport-vehicle-management-table").wait_for()
            table_daytime = await read_table_labels(page)
            require_equal(table_daytime["regular"], "ETD 18:10h", "Tabela REGULAR em horario diurno")
            require_equal(table_daytime["weekend"], "ETD 18:10h", "Tabela WEEKEND em horario diurno")

            forced_dashboard_generated_at = "2026-05-07T05:00:00+08:00"
            await reload_dashboard(page)
            table_nighttime = await read_table_labels(page)
            require_equal(table_nighttime["regular"], "ETA 07:45h", "Tabela REGULAR em horario noturno")
            require_equal(table_nighttime["weekend"], "ETA 07:45h", "Tabela WEEKEND em horario noturno")
            report["table_view"] = {
                "daytime": table_daytime,
                "nighttime": table_nighttime,
            }

            await page.locator('[data-toggle-vehicle-view="regular"]').click()
            await page.locator('[data-toggle-vehicle-view="weekend"]').click()
            await page.locator("#transportVehicleScopeRegular .transport-vehicle-button").wait_for()
            await page.locator("#transportVehicleScopeWeekend .transport-vehicle-button").wait_for()

            await page.locator("[data-open-settings-modal]").click()
            await page.locator("[data-settings-modal]").wait_for(state="visible")
            report["desktop_preferences_labels"] = await measure_preference_label_wrapping(page)

            await browser.close()
    except PlaywrightError as error:
        error_message = str(error)
        if "Executable doesn't exist" in error_message or "browserType.launch" in error_message:
            raise RuntimeError(
                "Playwright Chromium nao esta disponivel neste ambiente. Execute `python -m playwright install chromium`."
            ) from error
        raise

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())