from pathlib import Path
from time import monotonic
from typing import Literal

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from ..core.config import settings


FIELD_SEARCH_TIMEOUT_SECONDS = 10
SUCCESS_SEARCH_TIMEOUT_SECONDS = 20
PRE_SUBMIT_SUCCESS_CHECK_MS = 500
STEP_CONFIRM_TIMEOUT_SECONDS = 10


class FormsStepTimeoutError(Exception):
    def __init__(self, step_name: str, timeout_seconds: int) -> None:
        self.step_name = step_name
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Step '{step_name}' not found within {timeout_seconds} seconds")


class FormsStepValidationError(Exception):
    def __init__(self, step_name: str, details: str) -> None:
        self.step_name = step_name
        self.details = details
        super().__init__(f"Step '{step_name}' validation failed: {details}")


class FormsWorker:
    def __init__(self, assets_dir: Path) -> None:
        self.assets_dir = assets_dir

    def load_xpath(self, name: str) -> str:
        path = self.assets_dir / "xpath" / name
        return path.read_text(encoding="utf-8").strip()

    def _build_xpath_literal(self, value: str) -> str:
        if '"' not in value:
            return f'"{value}"'
        if "'" not in value:
            return f"'{value}'"
        parts = value.split('"')
        return "concat(" + ", '\"', ".join(f'"{part}"' for part in parts) + ")"

    def _build_project_xpath_map(self) -> dict[str, str]:
        xpath_dir = self.assets_dir / "xpath"
        project_xpath_map: dict[str, str] = {}
        for path in sorted(xpath_dir.glob("botao_projeto_*.txt")):
            project_name = path.stem.replace("botao_projeto_", "").strip().upper()
            if not project_name:
                continue
            project_xpath_map[project_name] = path.read_text(encoding="utf-8").strip()
        return project_xpath_map

    def _build_generic_project_xpath(self, project_name: str) -> str:
        project_literal = self._build_xpath_literal(project_name.strip())
        return (
            f"//*[@id='question-list']//span[normalize-space()={project_literal}]"
            "/ancestor::div[contains(@class, 'office-form-question-choice') or .//label][1]//label/span[1]/input"
        )

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

    def _wait_for_step_confirmation(self, step_name: str, predicate, timeout_seconds: int, failure_details: str) -> None:
        deadline = monotonic() + timeout_seconds

        while monotonic() < deadline:
            if predicate():
                return

        raise FormsStepValidationError(step_name=step_name, details=failure_details)

    def _is_step_visible(self, page, xpath: str, timeout_ms: int = PRE_SUBMIT_SUCCESS_CHECK_MS) -> bool:
        selector = f"xpath={xpath}"
        try:
            page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    def _normalize_detail_value(self, value: str) -> str:
        sanitized = value.replace("\n", " ").replace("\r", " ").strip()
        return " ".join(sanitized.split())

    def _fill_step(self, page, xpath: str, value: str, step_name: str) -> None:
        locator = self._wait_for_step(page, xpath, step_name, FIELD_SEARCH_TIMEOUT_SECONDS)
        locator.fill(value)
        expected_value = value.strip()
        self._wait_for_step_confirmation(
            step_name=step_name,
            predicate=lambda: self._normalize_detail_value(locator.input_value()) == expected_value,
            timeout_seconds=STEP_CONFIRM_TIMEOUT_SECONDS,
            failure_details=f"expected_value={expected_value}",
        )

    def _click_step(self, page, xpath: str, step_name: str) -> None:
        self._wait_for_step(page, xpath, step_name, FIELD_SEARCH_TIMEOUT_SECONDS).click()

    def _click_checked_step(self, page, xpath: str, step_name: str) -> None:
        locator = self._wait_for_step(page, xpath, step_name, FIELD_SEARCH_TIMEOUT_SECONDS)
        locator.click()
        self._wait_for_step_confirmation(
            step_name=step_name,
            predicate=lambda: locator.is_checked(),
            timeout_seconds=STEP_CONFIRM_TIMEOUT_SECONDS,
            failure_details="expected_checked=true",
        )

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

    def _submit_once(self, action: Literal["checkin", "checkout"], chave: str, projeto: str | None, ontime: bool) -> dict:
        audit_events: list[dict] = []
        completed_steps: list[str] = []
        digitar_chave = self.load_xpath("digitar_chave.txt")
        confirmar_chave = self.load_xpath("confirmar_chave.txt")
        botao_normal = self.load_xpath("botao_normal.txt")
        botao_retroativo = self.load_xpath("botao_retroativo.txt")
        botao_checkin = self.load_xpath("botao_checkin.txt")
        botao_checkout = self.load_xpath("botao_checkout.txt")
        botao_enviar = self.load_xpath("botao_enviar.txt")
        sucesso = self.load_xpath("sucesso.txt")

        projeto_xpath_map = self._build_project_xpath_map()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(settings.forms_url, timeout=settings.forms_timeout_seconds * 1000)
                self._audit(audit_events, "opened", "Microsoft Forms opened")

                self._fill_step(page, digitar_chave, chave, "digitar_chave")
                completed_steps.append("digitar_chave:filled+verified")
                self._fill_step(page, confirmar_chave, chave, "confirmar_chave")
                completed_steps.append("confirmar_chave:filled+verified")
                informe_xpath = botao_normal if ontime else botao_retroativo
                informe_step_name = "botao_normal" if ontime else "botao_retroativo"
                self._click_checked_step(page, informe_xpath, informe_step_name)
                completed_steps.append(f"{informe_step_name}:clicked+verified")

                if action == "checkin":
                    self._click_checked_step(page, botao_checkin, "botao_checkin")
                    completed_steps.append("botao_checkin:clicked+verified")
                    if projeto is None:
                        raise ValueError("Projeto invalido para check-in")
                    project_xpath = projeto_xpath_map.get(projeto) or self._build_generic_project_xpath(projeto)
                    self._click_checked_step(page, project_xpath, f"botao_projeto_{projeto}")
                    completed_steps.append(f"botao_projeto_{projeto}:clicked+verified")
                else:
                    self._click_checked_step(page, botao_checkout, "botao_checkout")
                    completed_steps.append("botao_checkout:clicked+verified")

                if self._is_step_visible(page, sucesso):
                    raise ValueError("XPath de sucesso ja estava visivel antes do envio")

                submit_started_at = monotonic()
                self._click_step(page, botao_enviar, "botao_enviar")
                completed_steps.append("botao_enviar:clicked")
                success_locator = self._wait_for_step(page, sucesso, "sucesso", SUCCESS_SEARCH_TIMEOUT_SECONDS)
                completed_steps.append("sucesso:visible")
                submit_elapsed_ms = int((monotonic() - submit_started_at) * 1000)
                success_text = self._normalize_detail_value(success_locator.inner_text())
                completed_details = (
                    f"steps={','.join(completed_steps)}; "
                    f"ontime={ontime}; "
                    "success_xpath_visible=true; "
                    f"submit_to_success_ms={submit_elapsed_ms}; "
                    f"success_text={success_text or '-'}"
                )
                self._audit(audit_events, "completed", "Microsoft Forms completed", completed_details)
            finally:
                browser.close()

        return {"success": True, "message": "Form submitted successfully", "audit_events": audit_events}

    def submit_with_retries(self, action: Literal["checkin", "checkout"], chave: str, projeto: str | None, ontime: bool = True) -> dict:
        last_error = ""
        for attempt in range(1, settings.forms_max_retries + 1):
            try:
                result = self._submit_once(action=action, chave=chave, projeto=projeto, ontime=ontime)
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
            except FormsStepValidationError as exc:
                return {
                    "success": False,
                    "message": str(exc),
                    "retry_count": attempt - 1,
                    "error_code": "forms_step_validation_failed",
                    "failed_step": exc.step_name,
                    "audit_events": [
                        {
                            "source": "forms",
                            "action": "forms",
                            "status": "failed",
                            "message": "Forms step validation failed",
                            "details": f"step={exc.step_name}; {exc.details}",
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
