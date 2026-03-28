from pathlib import Path
from time import monotonic
from typing import Literal

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from ..core.config import settings


FIELD_SEARCH_TIMEOUT_SECONDS = 10
SUCCESS_SEARCH_TIMEOUT_SECONDS = 20


class FormsStepTimeoutError(Exception):
    def __init__(self, step_name: str, timeout_seconds: int) -> None:
        self.step_name = step_name
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Step '{step_name}' not found within {timeout_seconds} seconds")


class FormsWorker:
    def __init__(self, assets_dir: Path) -> None:
        self.assets_dir = assets_dir

    def load_xpath(self, name: str) -> str:
        path = self.assets_dir / "xpath" / name
        return path.read_text(encoding="utf-8").strip()

    def _wait_for_step(self, page, xpath: str, step_name: str, timeout_seconds: int):
        deadline = monotonic() + timeout_seconds
        selector = f"xpath={xpath}"

        while monotonic() < deadline:
            remaining_ms = int(max(0, min(500, (deadline - monotonic()) * 1000)))
            if remaining_ms <= 0:
                break
            try:
                page.wait_for_selector(selector, state="visible", timeout=remaining_ms)
                return page.locator(selector)
            except PlaywrightTimeoutError:
                continue

        raise FormsStepTimeoutError(step_name=step_name, timeout_seconds=timeout_seconds)

    def _fill_step(self, page, xpath: str, value: str, step_name: str) -> None:
        self._wait_for_step(page, xpath, step_name, FIELD_SEARCH_TIMEOUT_SECONDS).fill(value)

    def _click_step(self, page, xpath: str, step_name: str) -> None:
        self._wait_for_step(page, xpath, step_name, FIELD_SEARCH_TIMEOUT_SECONDS).click()

    def _audit(self, audit_events: list[dict], status: str, message: str, details: str | None = None) -> None:
        audit_events.append(
            {
                "source": "forms",
                "action": "forms",
                "status": status,
                "message": message,
                "details": details,
            }
        )

    def _submit_once(self, action: Literal["checkin", "checkout"], chave: str, projeto: str | None) -> dict:
        audit_events: list[dict] = []
        digitar_chave = self.load_xpath("digitar_chave.txt")
        confirmar_chave = self.load_xpath("confirmar_chave.txt")
        botao_normal = self.load_xpath("botao_normal.txt")
        botao_checkin = self.load_xpath("botao_checkin.txt")
        botao_checkout = self.load_xpath("botao_checkout.txt")
        botao_enviar = self.load_xpath("botao_enviar.txt")
        sucesso = self.load_xpath("sucesso.txt")

        projeto_xpath_map = {
            "P80": self.load_xpath("botao_projeto_P80.txt"),
            "P83": self.load_xpath("botao_projeto_P83.txt"),
        }

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                self._audit(audit_events, "attempt", "Opening Microsoft Forms")
                page.goto(settings.forms_url, timeout=settings.forms_timeout_seconds * 1000)
                self._audit(audit_events, "success", "Microsoft Forms opened")

                self._audit(audit_events, "attempt", "Filling Petrobras key")
                self._fill_step(page, digitar_chave, chave, "digitar_chave")
                self._audit(audit_events, "success", "Petrobras key filled")

                self._audit(audit_events, "attempt", "Confirming Petrobras key")
                self._fill_step(page, confirmar_chave, chave, "confirmar_chave")
                self._audit(audit_events, "success", "Petrobras key confirmed")

                self._audit(audit_events, "attempt", "Selecting normal inform type")
                self._click_step(page, botao_normal, "botao_normal")
                self._audit(audit_events, "success", "Normal inform type selected")

                if action == "checkin":
                    self._audit(audit_events, "attempt", "Selecting check-in")
                    self._click_step(page, botao_checkin, "botao_checkin")
                    self._audit(audit_events, "success", "Check-in selected")
                    if projeto not in projeto_xpath_map:
                        raise ValueError("Projeto invalido para check-in")
                    self._audit(audit_events, "attempt", f"Selecting project {projeto}")
                    self._click_step(page, projeto_xpath_map[projeto], f"botao_projeto_{projeto}")
                    self._audit(audit_events, "success", f"Project {projeto} selected")
                else:
                    self._audit(audit_events, "attempt", "Selecting check-out")
                    self._click_step(page, botao_checkout, "botao_checkout")
                    self._audit(audit_events, "success", "Check-out selected")

                self._audit(audit_events, "attempt", "Submitting Microsoft Forms")
                self._click_step(page, botao_enviar, "botao_enviar")
                self._audit(audit_events, "success", "Submit button clicked")

                self._audit(audit_events, "attempt", "Waiting for success confirmation")
                self._wait_for_step(page, sucesso, "sucesso", SUCCESS_SEARCH_TIMEOUT_SECONDS)
                self._audit(audit_events, "success", "Success confirmation found")
            finally:
                browser.close()

        return {"success": True, "message": "Form submitted successfully", "audit_events": audit_events}

    def submit_with_retries(self, action: Literal["checkin", "checkout"], chave: str, projeto: str | None) -> dict:
        last_error = ""
        for attempt in range(1, settings.forms_max_retries + 1):
            try:
                result = self._submit_once(action=action, chave=chave, projeto=projeto)
                result["retry_count"] = attempt - 1
                return result
            except FormsStepTimeoutError as exc:
                return {
                    "success": False,
                    "message": str(exc),
                    "retry_count": attempt - 1,
                    "error_code": "forms_step_timeout",
                    "failed_step": exc.step_name,
                    "audit_events": [
                        {
                            "source": "forms",
                            "action": "forms",
                            "status": "failed",
                            "message": "Forms step timeout",
                            "details": f"step={exc.step_name}; timeout={exc.timeout_seconds}",
                        }
                    ],
                }
            except ValueError as exc:
                return {
                    "success": False,
                    "message": str(exc),
                    "retry_count": attempt - 1,
                    "error_code": "forms_validation_error",
                    "audit_events": [
                        {
                            "source": "forms",
                            "action": "forms",
                            "status": "failed",
                            "message": "Forms validation error",
                            "details": str(exc),
                        }
                    ],
                }
            except PlaywrightTimeoutError as exc:
                last_error = str(exc)

        return {
            "success": False,
            "message": f"Form submission failed: {last_error or 'unknown error'}",
            "retry_count": settings.forms_max_retries,
            "error_code": "forms_runtime_error",
            "audit_events": [
                {
                    "source": "forms",
                    "action": "forms",
                    "status": "failed",
                    "message": "Forms runtime error",
                    "details": last_error or "unknown error",
                }
            ],
        }
