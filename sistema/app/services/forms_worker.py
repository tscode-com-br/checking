from pathlib import Path
from typing import Literal

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from ..core.config import settings


class FormsWorker:
    def __init__(self, assets_dir: Path) -> None:
        self.assets_dir = assets_dir

    def load_xpath(self, name: str) -> str:
        path = self.assets_dir / "xpath" / name
        return path.read_text(encoding="utf-8").strip()

    def _submit_once(self, action: Literal["checkin", "checkout"], chave: str, projeto: str | None) -> dict:
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
            page = browser.new_page()
            page.goto(settings.forms_url, timeout=settings.forms_timeout_seconds * 1000)

            page.locator(f"xpath={digitar_chave}").fill(chave)
            page.locator(f"xpath={confirmar_chave}").fill(chave)
            page.locator(f"xpath={botao_normal}").click()

            if action == "checkin":
                page.locator(f"xpath={botao_checkin}").click()
                if projeto not in projeto_xpath_map:
                    browser.close()
                    raise ValueError("Projeto invalido para check-in")
                page.locator(f"xpath={projeto_xpath_map[projeto]}").click()
            else:
                page.locator(f"xpath={botao_checkout}").click()

            page.locator(f"xpath={botao_enviar}").click()
            page.wait_for_selector(f"xpath={sucesso}", timeout=settings.forms_timeout_seconds * 1000)
            browser.close()

        return {"success": True, "message": "Form submitted successfully"}

    def submit_with_retries(self, action: Literal["checkin", "checkout"], chave: str, projeto: str | None) -> dict:
        last_error = ""
        for attempt in range(1, settings.forms_max_retries + 1):
            try:
                result = self._submit_once(action=action, chave=chave, projeto=projeto)
                result["retry_count"] = attempt - 1
                return result
            except (PlaywrightTimeoutError, ValueError) as exc:
                last_error = str(exc)

        return {
            "success": False,
            "message": f"Form submission failed: {last_error or 'unknown error'}",
            "retry_count": settings.forms_max_retries,
        }
