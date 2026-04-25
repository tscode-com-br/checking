from __future__ import annotations

import argparse
import os
import queue
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORT = "22"
DEFAULT_DEPLOY_HOST = "157.230.35.21"
DEFAULT_DEPLOY_USER = "root"
DEFAULT_DEPLOY_DIR = "/root/checkcheck"
DEFAULT_DEPLOY_HOST_FINGERPRINT = "SHA256:pRjhMF0bKZ6t2+u3szubzGYEY+HOu4KwkCI1mCe3C3o"
DEFAULT_DEPLOY_KEY_PATH = PROJECT_ROOT / "deploy" / "keys" / "do_checkcheck"
DEFAULT_GHCR_REGISTRY = "ghcr.io"
DEFAULT_MANUAL_IMAGE_TAG_ENV = "CHECKCHECK_DEPLOY_IMAGE_TAG"
DEFAULT_DEPLOY_HOST_KEYS = (
    "157.230.35.21 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILcKvmHEtkkl9nI02Ds50toJUbMM4LFIWF011kR/Sq8k",
    "157.230.35.21 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDIFqEj9xCsCoggqcYsL+m7vSELFOnpUJiI8WHP3/qtDE4DYxjNBhlbB9Qw/yWip/Obl5T7jcCCCKf7OLtiYTNFUZKES9S6Eyy25DUz3ij7rbFWYVjF0HbUS6FiQXXUgZc0eEO9b89qUHomuL4p/RjIMZ6Qj/FVTgNAfLND0c2OeKVn/yIaKXDncTX7rWD5jjP9Ygdo2VMkTLZ8R92RqELqI8VjmtZBoLESWqa680q9siwrtuTzvYNW5Bsmv3nt1oQELKds6LzhpZwC43vsyg5yNDIsTp4rhNpjblfj+GDj/NimffGemPJqCL3XsJpVskhCfRhagekyLpCE6bpGThHDrEFPWV/M6wYnOs0Yl0qUrsM4xPm41ubMN4h+hcN5S4wXbK+6K6eT+8NWc39qftOezLryRQOfuhBZLmERqr30Tgyrxot+Td1lXZXpiXdDoDZvIMmhKzEW5SLdijrUYdzang3jWREiJ5zADX5DcPzy3ahYsMePwmQ5ZBEoMZKu4gU=",
    "157.230.35.21 ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBNmBYpOHGkimgKGY0MER0CTJmHx83XaDa7bGYOP+h32r0I3YbEWOeOww8wr1jdkyL1iyhIOY9bnAZi3J8I0z2P0=",
)
REQUIRED_LOCAL_TOOLS = ("ssh", "scp", "ssh-keyscan", "ssh-keygen")
ARCHIVE_EXCLUDE_PREFIXES = (
    ".git/",
    ".github/",
    ".venv/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".vscode/",
    "deploy/keys/",
    "checking_android_new/",
    "checking_kotlin/",
)
ARCHIVE_EXCLUDE_EXACT = {
    ".git",
    ".github",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".vscode",
    ".env",
    "deploy/keys",
    "checking_android_new",
    "checking_kotlin",
}


@dataclass(frozen=True)
class SmokeValidation:
    label: str
    compose_file: str
    service: str
    url: str
    contains: str | None = None


@dataclass(frozen=True)
class DeployAction:
    label: str
    summary: str
    release_marker: str
    restart_commands: tuple[str, ...]
    smoke_validation: SmokeValidation
    prepare_commands: tuple[str, ...] = ()
    image_repository: str | None = None
    compose_image_env_var: str | None = None
    requires_remote_env: bool = False
    prune_after_success: bool = False


@dataclass(frozen=True)
class DeployConfig:
    host: str
    user: str
    port: int
    key_path: Path
    deploy_dir: str
    host_fingerprint: str


DEPLOY_ACTIONS = (
    DeployAction(
        label="Fallback Global",
        summary="Redeploy completo direto do working tree local.",
        release_marker=".deploy-release",
        prepare_commands=(
            "docker compose up -d db",
        ),
        restart_commands=(
            "docker compose up -d --no-build --force-recreate --remove-orphans app",
        ),
        smoke_validation=SmokeValidation(
            label="application",
            compose_file="docker-compose.yml",
            service="app",
            url="http://127.0.0.1:8000/api/health",
        ),
        image_repository="ghcr.io/tscode-com-br/checkcheck-app",
        compose_image_env_var="CHECKCHECK_APP_IMAGE",
        requires_remote_env=True,
        prune_after_success=True,
    ),
    DeployAction(
        label="API",
        summary="Deploy isolado da API direto para a DigitalOcean.",
        release_marker=".deploy-release-api",
        prepare_commands=(
            "docker compose -f docker-compose.api.yml up -d db",
        ),
        restart_commands=(
            "docker compose -f docker-compose.api.yml up -d --no-build --force-recreate api",
        ),
        smoke_validation=SmokeValidation(
            label="API",
            compose_file="docker-compose.api.yml",
            service="api",
            url="http://127.0.0.1:18080/api/health",
        ),
        image_repository="ghcr.io/tscode-com-br/checkcheck-api",
        compose_image_env_var="CHECKCHECK_API_IMAGE",
        requires_remote_env=True,
    ),
    DeployAction(
        label="ADMIN",
        summary="Deploy isolado do Admin direto para a DigitalOcean.",
        release_marker=".deploy-release-admin-web",
        restart_commands=(
            "docker compose -f docker-compose.websites.yml up -d --no-build --force-recreate admin-web",
        ),
        smoke_validation=SmokeValidation(
            label="admin-web",
            compose_file="docker-compose.websites.yml",
            service="admin-web",
            url="http://127.0.0.1:18081/",
            contains="Checking Admin",
        ),
        image_repository="ghcr.io/tscode-com-br/checkcheck-admin-web",
        compose_image_env_var="CHECKCHECK_ADMIN_WEB_IMAGE",
    ),
    DeployAction(
        label="CHECK",
        summary="Deploy isolado do site de check direto para a DigitalOcean.",
        release_marker=".deploy-release-user-web",
        restart_commands=(
            "docker compose -f docker-compose.websites.yml up -d --no-build --force-recreate user-web",
        ),
        smoke_validation=SmokeValidation(
            label="user-web",
            compose_file="docker-compose.websites.yml",
            service="user-web",
            url="http://127.0.0.1:18082/",
            contains="Checking Mobile Web",
        ),
        image_repository="ghcr.io/tscode-com-br/checkcheck-user-web",
        compose_image_env_var="CHECKCHECK_USER_WEB_IMAGE",
    ),
    DeployAction(
        label="TRANSPORT",
        summary="Deploy isolado do transporte direto para a DigitalOcean.",
        release_marker=".deploy-release-transport-web",
        restart_commands=(
            "docker compose -f docker-compose.websites.yml up -d --no-build --force-recreate transport-web",
        ),
        smoke_validation=SmokeValidation(
            label="transport-web",
            compose_file="docker-compose.websites.yml",
            service="transport-web",
            url="http://127.0.0.1:18083/",
            contains="Checking Transport",
        ),
        image_repository="ghcr.io/tscode-com-br/checkcheck-transport-web",
        compose_image_env_var="CHECKCHECK_TRANSPORT_WEB_IMAGE",
    ),
)


class DeployError(RuntimeError):
    pass


def _run_local_capture(command: list[str]) -> tuple[int, str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            check=False,
        )
    except OSError:
        return 127, ""
    return completed.returncode, (completed.stdout or "").strip()


def resolve_git_commit_sha() -> str | None:
    git_path = shutil.which("git")
    if not git_path:
        return None

    returncode, output = _run_local_capture([git_path, "rev-parse", "HEAD"])
    if returncode != 0 or not output:
        return None
    return output


def is_git_working_tree_dirty() -> bool | None:
    git_path = shutil.which("git")
    if not git_path:
        return None

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [git_path, "diff", "--quiet", "--ignore-submodules", "HEAD", "--"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            check=False,
        )
    except OSError:
        return None
    return completed.returncode != 0


def resolve_manual_image_tag(image_tag_override: str | None = None) -> str:
    override = (image_tag_override or os.getenv(DEFAULT_MANUAL_IMAGE_TAG_ENV) or "").strip()
    if override:
        return override

    commit_sha = resolve_git_commit_sha()
    if not commit_sha:
        raise DeployError(
            "Nao foi possivel resolver a imagem publicada do deploy manual. "
            f"Defina {DEFAULT_MANUAL_IMAGE_TAG_ENV} ou execute a partir de um clone Git valido."
        )

    dirty = is_git_working_tree_dirty()
    if dirty is None:
        raise DeployError(
            "Nao foi possivel validar o estado do working tree local. "
            f"Defina {DEFAULT_MANUAL_IMAGE_TAG_ENV} explicitamente para o redeploy manual."
        )
    if dirty:
        raise DeployError(
            "O deploy manual por imagem precompilada exige working tree limpo. "
            f"Faça commit/push primeiro ou defina {DEFAULT_MANUAL_IMAGE_TAG_ENV} para redeployar uma imagem ja publicada."
        )

    return commit_sha


def resolve_registry_username(username_override: str | None = None) -> str:
    for candidate in (
        username_override,
        os.getenv("GHCR_USERNAME"),
        os.getenv("GH_USERNAME"),
        os.getenv("GITHUB_ACTOR"),
    ):
        value = (candidate or "").strip()
        if value:
            return value

    gh_path = shutil.which("gh")
    if gh_path:
        returncode, output = _run_local_capture([gh_path, "api", "user", "--jq", ".login"])
        if returncode == 0 and output:
            return output

    raise DeployError(
        "Nenhum usuario do GHCR foi encontrado. Defina GHCR_USERNAME/GITHUB_ACTOR "
        "ou autentique o GitHub CLI com `gh auth login`."
    )


def resolve_registry_token(token_override: str | None = None) -> str:
    for candidate in (
        token_override,
        os.getenv("GHCR_TOKEN"),
        os.getenv("GH_TOKEN"),
        os.getenv("GITHUB_TOKEN"),
    ):
        value = (candidate or "").strip()
        if value:
            return value

    gh_path = shutil.which("gh")
    if gh_path:
        returncode, output = _run_local_capture([gh_path, "auth", "token"])
        if returncode == 0 and output:
            return output

    raise DeployError(
        "Nenhum token do GHCR foi encontrado. Defina GHCR_TOKEN/GH_TOKEN/GITHUB_TOKEN "
        "ou autentique o GitHub CLI com `gh auth login`."
    )


def _normalize_archive_member(name: str) -> str:
    normalized = name.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def should_exclude_archive_member(name: str) -> bool:
    normalized = _normalize_archive_member(name)
    if not normalized:
        return False
    if normalized in ARCHIVE_EXCLUDE_EXACT:
        return True
    if any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in ARCHIVE_EXCLUDE_PREFIXES):
        return True

    basename = PurePosixPath(normalized).name
    if basename == ".env":
        return True
    if basename == "__pycache__":
        return True
    if basename.lower().endswith(".db"):
        return True
    return False


def _list_git_archive_members() -> list[tuple[Path, str]] | None:
    git_path = shutil.which("git")
    if not git_path:
        return None

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [git_path, "ls-files", "-z", "--cached", "--modified", "--others", "--exclude-standard"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            check=False,
        )
    except OSError:
        return None

    if completed.returncode != 0:
        return None

    members: list[tuple[Path, str]] = []
    seen_names: set[str] = set()
    for raw_name in (completed.stdout or "").split("\0"):
        normalized = _normalize_archive_member(raw_name)
        if not normalized or normalized in seen_names:
            continue

        candidate_path = (PROJECT_ROOT / Path(normalized)).resolve()
        try:
            candidate_path.relative_to(PROJECT_ROOT)
        except ValueError:
            continue

        if not candidate_path.exists() or candidate_path.is_dir():
            continue

        seen_names.add(normalized)
        members.append((candidate_path, normalized))

    return members


def create_project_archive(archive_path: Path) -> int:
    git_members = _list_git_archive_members()
    if git_members is not None:
        with tarfile.open(archive_path, mode="w:gz") as tar_handle:
            for file_path, archive_name in git_members:
                tar_handle.add(file_path, arcname=archive_name, recursive=False)
        return len(git_members)

    archived_file_count = 0

    def tar_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        nonlocal archived_file_count
        if should_exclude_archive_member(tarinfo.name):
            return None
        if tarinfo.isfile():
            archived_file_count += 1
        return tarinfo

    with tarfile.open(archive_path, mode="w:gz") as tar_handle:
        tar_handle.add(PROJECT_ROOT, arcname=".", filter=tar_filter)

    return archived_file_count


def get_default_key_path() -> str:
    direct_value = (os.getenv("OCEAN_SSH_KEY_PATH") or "").strip()
    if direct_value:
        return direct_value

    fallback_value = (os.getenv("OCEAN_SSH_KEY") or "").strip()
    if fallback_value and "\n" not in fallback_value:
        return fallback_value

    if DEFAULT_DEPLOY_KEY_PATH.is_file():
        return str(DEFAULT_DEPLOY_KEY_PATH)

    return ""


def resolve_release_identifier() -> str:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    git_path = shutil.which("git")
    if not git_path:
        return f"local-{timestamp}"

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        sha_completed = subprocess.run(
            [git_path, "rev-parse", "--short=12", "HEAD"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            check=False,
        )
        short_sha = (sha_completed.stdout or "").strip()
        if not short_sha:
            return f"local-{timestamp}"

        dirty_completed = subprocess.run(
            [git_path, "diff", "--quiet", "--ignore-submodules", "HEAD", "--"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            check=False,
        )
        dirty_suffix = "-dirty" if dirty_completed.returncode != 0 else ""
        return f"{short_sha}{dirty_suffix}-{timestamp}"
    except OSError:
        return f"local-{timestamp}"


class DeployLauncher:
    def __init__(
        self,
        root: tk.Tk,
        *,
        host: str,
        user: str,
        port: str,
        key_path: str,
        host_fingerprint: str,
        deploy_dir: str,
        image_tag: str,
        registry_username: str,
        registry_token: str,
    ) -> None:
        self.root = root
        self.host_var = tk.StringVar(value=host)
        self.user_var = tk.StringVar(value=user)
        self.port_var = tk.StringVar(value=port or DEFAULT_PORT)
        self.key_path_var = tk.StringVar(value=key_path)
        self.host_fingerprint_var = tk.StringVar(value=host_fingerprint)
        self.deploy_dir_var = tk.StringVar(value=deploy_dir)
        self.status_var = tk.StringVar(value="Pronto.")
        self.image_tag_override = image_tag.strip()
        self.registry_username_override = registry_username.strip()
        self.registry_token_override = registry_token.strip()
        self.environment_var = tk.StringVar(value="Verificando ambiente local...")
        self.log_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.command_running = False
        self.action_buttons: list[ttk.Button] = []
        self.local_tools: dict[str, str] = {}
        self.missing_local_tools: list[str] = []

        self.root.title("Checking Deploy Launcher")
        self.root.geometry("980x700")
        self.root.minsize(900, 620)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._configure_style()
        self._build_ui()
        self._refresh_environment_label()
        self.root.after(120, self._drain_log_queue)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        default_font = ("Segoe UI", 10)
        self.root.option_add("*Font", default_font)
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 18))
        style.configure("Muted.TLabel", foreground="#4b5563")
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10))

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Checking Deploy Launcher", style="Title.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(
            header,
            text="Executa deploy direto na DigitalOcean a partir do working tree local, sem GitHub Actions.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        context_frame = ttk.LabelFrame(container, text="Contexto do deploy", padding=14)
        context_frame.grid(row=1, column=0, sticky="ew", pady=(16, 12))
        context_frame.columnconfigure(1, weight=1)
        context_frame.columnconfigure(3, weight=1)

        ttk.Label(context_frame, text="Host:").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Entry(context_frame, textvariable=self.host_var).grid(row=0, column=1, sticky="ew")

        ttk.Label(context_frame, text="Usuário:").grid(row=0, column=2, sticky="w", padx=(16, 12))
        ttk.Entry(context_frame, textvariable=self.user_var).grid(row=0, column=3, sticky="ew")

        ttk.Label(context_frame, text="Porta SSH:").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(10, 0))
        ttk.Entry(context_frame, textvariable=self.port_var, width=10).grid(row=1, column=1, sticky="w", pady=(10, 0))

        ttk.Label(context_frame, text="Chave SSH:").grid(row=1, column=2, sticky="w", padx=(16, 12), pady=(10, 0))
        key_frame = ttk.Frame(context_frame)
        key_frame.grid(row=1, column=3, sticky="ew", pady=(10, 0))
        key_frame.columnconfigure(0, weight=1)
        ttk.Entry(key_frame, textvariable=self.key_path_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(key_frame, text="Selecionar", command=self.browse_key_path).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(context_frame, text="Fingerprint SSH:").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=(10, 0))
        ttk.Entry(context_frame, textvariable=self.host_fingerprint_var).grid(
            row=2,
            column=1,
            columnspan=3,
            sticky="ew",
            pady=(10, 0),
        )

        ttk.Label(context_frame, text="deploy_dir remoto:").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=(10, 0))
        ttk.Entry(context_frame, textvariable=self.deploy_dir_var).grid(
            row=3,
            column=1,
            columnspan=3,
            sticky="ew",
            pady=(10, 0),
        )

        ttk.Label(
            context_frame,
            text=f"Origem local: {PROJECT_ROOT}",
            style="Muted.TLabel",
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(12, 0))
        ttk.Label(
            context_frame,
            textvariable=self.environment_var,
            style="Muted.TLabel",
            wraplength=860,
        ).grid(row=5, column=0, columnspan=4, sticky="w", pady=(4, 0))

        actions_frame = ttk.LabelFrame(container, text="Deploys disponíveis", padding=14)
        actions_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        for column in range(3):
            actions_frame.columnconfigure(column, weight=1)

        for index, action in enumerate(DEPLOY_ACTIONS):
            row = index // 3
            column = index % 3
            card = ttk.Frame(actions_frame, padding=8)
            card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
            card.columnconfigure(0, weight=1)

            ttk.Label(card, text=action.label, font=("Segoe UI Semibold", 12)).grid(
                row=0,
                column=0,
                sticky="w",
            )
            ttk.Label(card, text=action.summary, style="Muted.TLabel", wraplength=240).grid(
                row=1,
                column=0,
                sticky="w",
                pady=(4, 10),
            )
            button = ttk.Button(
                card,
                text=f"Executar {action.label}",
                style="Accent.TButton",
                command=lambda selected=action: self.trigger_deploy(selected),
            )
            button.grid(row=2, column=0, sticky="ew")
            self.action_buttons.append(button)

        utilities_frame = ttk.Frame(container)
        utilities_frame.grid(row=3, column=0, sticky="ew")
        utilities_frame.columnconfigure(0, weight=1)

        ttk.Button(utilities_frame, text="Verificar ambiente", command=self.verify_environment).grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Button(utilities_frame, text="Limpar log", command=self.clear_log).grid(
            row=0,
            column=1,
            sticky="e",
        )

        log_frame = ttk.LabelFrame(container, text="Saída", padding=10)
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_widget = ScrolledText(
            log_frame,
            wrap="word",
            height=18,
            state="disabled",
            font=("Cascadia Mono", 10),
        )
        self.log_widget.grid(row=0, column=0, sticky="nsew")

        footer = ttk.Label(container, textvariable=self.status_var, style="Muted.TLabel")
        footer.grid(row=5, column=0, sticky="w", pady=(10, 0))

    def _probe_local_tools(self) -> dict[str, str]:
        return {tool: shutil.which(tool) or "" for tool in REQUIRED_LOCAL_TOOLS}

    def _refresh_environment_label(self) -> None:
        self.local_tools = self._probe_local_tools()
        self.missing_local_tools = [tool for tool, resolved in self.local_tools.items() if not resolved]
        if self.missing_local_tools:
            self.environment_var.set(
                f"Ferramentas locais ausentes: {', '.join(self.missing_local_tools)}. Instale o OpenSSH do Windows antes de usar o deploy direto."
            )
        else:
            self.environment_var.set(
                "OpenSSH local pronto. O launcher envia o estado atual do working tree diretamente para a DigitalOcean e ignora o GitHub."
            )
        self._update_action_button_states()

    def _update_action_button_states(self) -> None:
        state = "normal" if not self.command_running and not self.missing_local_tools else "disabled"
        for button in self.action_buttons:
            button.configure(state=state)

    def _set_running(self, running: bool, status: str) -> None:
        self.command_running = running
        self.status_var.set(status)
        self._update_action_button_states()

    def _append_log(self, text: str) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", text + "\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def _get_form_snapshot(self) -> dict[str, str]:
        return {
            "host": self.host_var.get().strip(),
            "user": self.user_var.get().strip(),
            "port": (self.port_var.get() or DEFAULT_PORT).strip(),
            "key_path": self.key_path_var.get().strip(),
            "host_fingerprint": self.host_fingerprint_var.get().strip(),
            "deploy_dir": self.deploy_dir_var.get().strip(),
        }

    def _build_config_from_snapshot(self, snapshot: dict[str, str]) -> DeployConfig:
        missing_fields = []
        if not snapshot["host"]:
            missing_fields.append("Host")
        if not snapshot["user"]:
            missing_fields.append("Usuário")
        if not snapshot["key_path"]:
            missing_fields.append("Chave SSH")
        if not snapshot["deploy_dir"]:
            missing_fields.append("deploy_dir remoto")
        if missing_fields:
            raise DeployError(f"Preencha os campos obrigatórios: {', '.join(missing_fields)}.")

        try:
            port = int(snapshot["port"] or DEFAULT_PORT)
        except ValueError as exc:
            raise DeployError("A porta SSH deve ser um número inteiro.") from exc
        if port <= 0 or port > 65535:
            raise DeployError("A porta SSH deve estar entre 1 e 65535.")

        expanded_key_path = Path(os.path.expandvars(os.path.expanduser(snapshot["key_path"])))
        if not expanded_key_path.exists() or not expanded_key_path.is_file():
            raise DeployError(f"Arquivo de chave SSH não encontrado: {expanded_key_path}")

        return DeployConfig(
            host=snapshot["host"],
            user=snapshot["user"],
            port=port,
            key_path=expanded_key_path.resolve(),
            deploy_dir=snapshot["deploy_dir"],
            host_fingerprint=snapshot["host_fingerprint"],
        )

    def browse_key_path(self) -> None:
        current_path = self.key_path_var.get().strip()
        initial_dir = str(Path.home())
        if current_path:
            current_candidate = Path(os.path.expandvars(os.path.expanduser(current_path)))
            parent = current_candidate.parent if current_candidate.parent.exists() else None
            if parent is not None:
                initial_dir = str(parent)

        selected = filedialog.askopenfilename(
            title="Selecionar chave SSH",
            initialdir=initial_dir,
        )
        if selected:
            self.key_path_var.set(selected)

    def clear_log(self) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", "end")
        self.log_widget.configure(state="disabled")
        self.status_var.set("Log limpo.")

    def verify_environment(self) -> None:
        if self.command_running:
            messagebox.showinfo("Deploy em andamento", "Espere o comando atual terminar antes de verificar o ambiente.")
            return

        self._refresh_environment_label()
        snapshot = self._get_form_snapshot()
        self._append_log("")
        self._append_log("### Verificação do ambiente")
        self._set_running(True, "Verificando ferramentas locais...")
        threading.Thread(
            target=self._run_environment_check,
            args=(snapshot,),
            daemon=True,
        ).start()

    def trigger_deploy(self, action: DeployAction) -> None:
        if self.command_running:
            messagebox.showinfo("Deploy em andamento", "Espere o comando atual terminar antes de iniciar outro deploy.")
            return

        self._refresh_environment_label()
        if self.missing_local_tools:
            messagebox.showerror(
                "Ferramentas locais ausentes",
                f"Instale as ferramentas ausentes antes de iniciar o deploy: {', '.join(self.missing_local_tools)}.",
            )
            return

        snapshot = self._get_form_snapshot()
        try:
            config = self._build_config_from_snapshot(snapshot)
        except DeployError as exc:
            messagebox.showerror("Configuração incompleta", str(exc))
            return

        prompt = [
            f"Destino: {config.user}@{config.host}:{config.port}",
            f"Diretório remoto: {config.deploy_dir}",
            f"Chave SSH: {config.key_path}",
            "",
            f"Deseja executar {action.label} agora usando o working tree local?",
        ]
        if not messagebox.askyesno("Confirmar deploy", "\n".join(prompt)):
            return

        self._append_log("")
        self._append_log(f"### {action.label}")
        self._append_log(f"Origem local: {PROJECT_ROOT}")
        self._append_log(f"Destino: {config.user}@{config.host}:{config.port} -> {config.deploy_dir}")
        self._set_running(True, f"Preparando {action.label}...")
        threading.Thread(
            target=self._run_direct_deploy,
            args=(action, config),
            daemon=True,
        ).start()

    def _run_environment_check(self, snapshot: dict[str, str]) -> None:
        try:
            if self.missing_local_tools:
                raise DeployError(
                    f"Ferramentas locais ausentes: {', '.join(self.missing_local_tools)}."
                )

            resolved_tools = ", ".join(f"{tool}={self.local_tools[tool]}" for tool in REQUIRED_LOCAL_TOOLS)
            self.log_queue.put(("output", f"Ferramentas locais: {resolved_tools}"))

            required_config_missing = [
                label
                for label, key in (
                    ("Host", "host"),
                    ("Usuário", "user"),
                    ("Chave SSH", "key_path"),
                    ("deploy_dir remoto", "deploy_dir"),
                )
                if not snapshot[key]
            ]
            if required_config_missing:
                self.log_queue.put(
                    (
                        "output",
                        "Configuração parcial: preencha "
                        + ", ".join(required_config_missing)
                        + " para validar o destino remoto.",
                    )
                )
                self.log_queue.put(("finished", "Verificação do ambiente|0"))
                return

            config = self._build_config_from_snapshot(snapshot)
            with tempfile.TemporaryDirectory(prefix="checking-deploy-") as temp_dir_value:
                known_hosts_path = Path(temp_dir_value) / "known_hosts"
                self._resolve_known_hosts(config, known_hosts_path)

            self.log_queue.put(
                (
                    "output",
                    f"Destino remoto validado: {config.user}@{config.host}:{config.port} -> {config.deploy_dir}",
                )
            )
            self.log_queue.put(("finished", "Verificação do ambiente|0"))
        except DeployError as exc:
            self.log_queue.put(("output", f"Falha: {exc}"))
            self.log_queue.put(("finished", "Verificação do ambiente|1"))

    def _run_direct_deploy(self, action: DeployAction, config: DeployConfig) -> None:
        try:
            release_id = resolve_release_identifier()
            image_tag = resolve_manual_image_tag(self.image_tag_override)
            registry_username = resolve_registry_username(self.registry_username_override)
            registry_token = resolve_registry_token(self.registry_token_override)
            deployed_release_id = image_tag if action.image_repository else release_id
            self.log_queue.put(("output", f"Release local: {release_id}"))
            if action.image_repository:
                self.log_queue.put(("output", f"Imagem publicada: {action.image_repository}:{image_tag}"))

            with tempfile.TemporaryDirectory(prefix="checking-deploy-") as temp_dir_value:
                temp_dir = Path(temp_dir_value)
                known_hosts_path = temp_dir / "known_hosts"
                archive_path = temp_dir / "checkcheck-deploy.tar.gz"
                remote_token = f"{int(time.time())}-{os.getpid()}"
                remote_archive = f"/tmp/checkcheck-deploy-{remote_token}.tar.gz"
                remote_stage_dir = f"/tmp/checkcheck-stage-{remote_token}"

                self.log_queue.put(("status", "Validando host SSH..."))
                self._resolve_known_hosts(config, known_hosts_path)

                self.log_queue.put(("status", "Empacotando working tree local..."))
                archived_files = create_project_archive(archive_path)
                archive_size_kib = archive_path.stat().st_size / 1024
                self.log_queue.put(
                    (
                        "output",
                        f"Pacote local criado com {archived_files} arquivos ({archive_size_kib:.1f} KiB).",
                    )
                )

                self.log_queue.put(("status", "Enviando pacote para o servidor..."))
                self._run_logged_command(
                    self._build_scp_command(config, known_hosts_path, archive_path, remote_archive),
                    "Upload do pacote",
                )

                self.log_queue.put(("status", "Sincronizando arquivos no servidor..."))
                self._run_logged_command(
                    self._build_ssh_command(
                        config,
                        known_hosts_path,
                        self._build_remote_sync_script(config, remote_archive, remote_stage_dir),
                    ),
                    "Sincronização remota",
                )

                self.log_queue.put(("status", f"Executando {action.label} no servidor..."))
                self._run_logged_command(
                    self._build_ssh_command(
                        config,
                        known_hosts_path,
                        self._build_remote_deploy_script(
                            action,
                            config,
                            deployed_release_id,
                            image_tag,
                            registry_username,
                            registry_token,
                        ),
                    ),
                    f"Deploy remoto {action.label}",
                )

            self.log_queue.put(("finished", f"{action.label}|0"))
        except DeployError as exc:
            self.log_queue.put(("output", f"Falha: {exc}"))
            self.log_queue.put(("finished", f"{action.label}|1"))

    def _resolve_known_hosts(self, config: DeployConfig, known_hosts_path: Path) -> None:
        ssh_keyscan_path = self.local_tools.get("ssh-keyscan") or "ssh-keyscan"
        scan_command = [ssh_keyscan_path, "-T", "10", "-p", str(config.port), config.host]
        self.log_queue.put(("output", "[Host key scan]"))
        self.log_queue.put(("output", "$ " + shlex.join(scan_command)))

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        raw_output = ""
        try:
            completed = subprocess.run(
                scan_command,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                check=False,
            )
        except OSError as exc:
            self.log_queue.put(("output", f"Falha ao executar ssh-keyscan: {exc}"))
        else:
            raw_output = completed.stdout or ""
            if raw_output.strip():
                for line in raw_output.rstrip().splitlines():
                    self.log_queue.put(("output", line))

        key_lines = self._extract_known_host_lines(raw_output)
        if not key_lines:
            fallback_source, fallback_lines = self._load_known_hosts_fallback(config)
            if not fallback_lines:
                details = f" Saída do ssh-keyscan: {raw_output.strip()}" if raw_output.strip() else ""
                raise DeployError(
                    f"Não foi possível obter a host key SSH de {config.host}:{config.port}.{details}"
                )

            self.log_queue.put(
                ("output", f"ssh-keyscan não retornou host keys; usando fallback de {fallback_source}.")
            )
            key_lines = fallback_lines

        known_hosts_path.write_text("\n".join(key_lines) + "\n", encoding="utf-8")
        fingerprints = self._extract_fingerprints(known_hosts_path)
        if not fingerprints:
            raise DeployError("Não foi possível calcular o fingerprint SSH do host remoto.")

        if config.host_fingerprint:
            if config.host_fingerprint not in fingerprints:
                raise DeployError(
                    "Fingerprint SSH inesperado. "
                    f"Esperado: {config.host_fingerprint}. Observado(s): {', '.join(fingerprints)}"
                )
            self.log_queue.put(("output", f"Fingerprint SSH validado: {config.host_fingerprint}"))
        else:
            self.log_queue.put(
                (
                    "output",
                    "Fingerprint SSH não informado; confiando na host key escaneada nesta execução.",
                )
            )
            self.log_queue.put(("output", f"Fingerprints observados: {', '.join(fingerprints)}"))

    def _load_known_hosts_fallback(self, config: DeployConfig) -> tuple[str, list[str]]:
        lookup_host = config.host if config.port == 22 else f"[{config.host}]:{config.port}"
        fallback_candidates = (
            Path.home() / ".ssh" / "known_hosts",
            Path.home() / ".ssh" / "known_hosts.old",
        )

        for candidate_path in fallback_candidates:
            lines = self._lookup_known_hosts_entries(candidate_path, lookup_host)
            if lines:
                return (str(candidate_path), lines)

        if config.host == DEFAULT_DEPLOY_HOST and config.port == int(DEFAULT_PORT):
            return ("host keys embutidas do droplet padrão", list(DEFAULT_DEPLOY_HOST_KEYS))

        return ("", [])

    def _lookup_known_hosts_entries(self, known_hosts_file: Path, lookup_host: str) -> list[str]:
        if not known_hosts_file.is_file():
            return []

        ssh_keygen_path = self.local_tools.get("ssh-keygen") or "ssh-keygen"
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            completed = subprocess.run(
                [ssh_keygen_path, "-F", lookup_host, "-f", str(known_hosts_file)],
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                check=False,
            )
        except OSError:
            return []

        if completed.returncode != 0:
            return []

        return self._extract_known_host_lines(completed.stdout or "")

    def _extract_known_host_lines(self, text: str) -> list[str]:
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if len(parts) < 3:
                continue

            key_type_index = 2 if parts[0].startswith("@") else 1
            if len(parts) <= key_type_index:
                continue

            key_type = parts[key_type_index]
            if not (
                key_type.startswith("ssh-")
                or key_type.startswith("ecdsa-")
                or key_type.startswith("sk-")
            ):
                continue

            lines.append(stripped)
        return lines

    def _extract_fingerprints(self, known_hosts_path: Path) -> list[str]:
        ssh_keygen_path = self.local_tools.get("ssh-keygen") or "ssh-keygen"
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            completed = subprocess.run(
                [ssh_keygen_path, "-lf", str(known_hosts_path), "-E", "sha256"],
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                check=False,
            )
        except OSError as exc:
            raise DeployError(f"Falha ao executar ssh-keygen: {exc}") from exc

        if completed.returncode != 0:
            output = (completed.stdout or "").strip() or "ssh-keygen falhou ao ler a host key."
            raise DeployError(output)

        fingerprints = []
        for line in (completed.stdout or "").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].startswith("SHA256:"):
                fingerprints.append(parts[1])
        return sorted(set(fingerprints))

    def _build_common_ssh_options(self, config: DeployConfig, known_hosts_path: Path) -> list[str]:
        return [
            "-i",
            str(config.key_path),
            "-o",
            f"UserKnownHostsFile={known_hosts_path}",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=15",
        ]

    def _build_ssh_command(self, config: DeployConfig, known_hosts_path: Path, script: str) -> list[str]:
        ssh_path = self.local_tools.get("ssh") or "ssh"
        remote_command = f"bash -lc {shlex.quote(script)}"
        return [
            ssh_path,
            *self._build_common_ssh_options(config, known_hosts_path),
            "-p",
            str(config.port),
            f"{config.user}@{config.host}",
            remote_command,
        ]

    def _build_scp_command(
        self,
        config: DeployConfig,
        known_hosts_path: Path,
        archive_path: Path,
        remote_archive: str,
    ) -> list[str]:
        scp_path = self.local_tools.get("scp") or "scp"
        return [
            scp_path,
            *self._build_common_ssh_options(config, known_hosts_path),
            "-P",
            str(config.port),
            str(archive_path),
            f"{config.user}@{config.host}:{remote_archive}",
        ]

    def _run_logged_command(self, command: list[str], step_label: str) -> None:
        self.log_queue.put(("output", f"[{step_label}]"))
        self.log_queue.put(("output", "$ " + shlex.join(command)))

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            process = subprocess.Popen(
                command,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )
        except OSError as exc:
            raise DeployError(f"Falha ao iniciar {step_label.lower()}: {exc}") from exc

        assert process.stdout is not None
        for line in process.stdout:
            self.log_queue.put(("output", line.rstrip("\n")))

        exit_code = process.wait()
        if exit_code != 0:
            raise DeployError(f"{step_label} falhou com código {exit_code}.")

    def _build_remote_sync_script(self, config: DeployConfig, remote_archive: str, remote_stage_dir: str) -> str:
        deploy_dir = shlex.quote(config.deploy_dir)
        archive_path = shlex.quote(remote_archive)
        stage_dir = shlex.quote(remote_stage_dir)
        lines = [
            "set -euo pipefail",
            f"DEPLOY_DIR={deploy_dir}",
            f"REMOTE_ARCHIVE={archive_path}",
            f"STAGE_DIR={stage_dir}",
            'case "$DEPLOY_DIR" in "~"|"~/"*) DEPLOY_DIR="${HOME}${DEPLOY_DIR:1}" ;; esac',
            'mkdir -p "$DEPLOY_DIR"',
            'rm -rf "$STAGE_DIR"',
            'mkdir -p "$STAGE_DIR"',
            'tar -xzf "$REMOTE_ARCHIVE" -C "$STAGE_DIR"',
            'find "$DEPLOY_DIR" -mindepth 1 -maxdepth 1 ! -name ".env" -exec rm -rf {} +',
            'cp -a "$STAGE_DIR"/. "$DEPLOY_DIR"/',
            'rm -rf "$STAGE_DIR" "$REMOTE_ARCHIVE"',
        ]
        return "\n".join(lines)

    def _build_remote_deploy_script(
        self,
        action: DeployAction,
        config: DeployConfig,
        release_id: str,
        image_tag: str,
        registry_username: str,
        registry_token: str,
    ) -> str:
        deploy_dir = shlex.quote(config.deploy_dir)
        smoke_command = [
            "bash",
            "deploy/smoke/validate_target.sh",
            "--label",
            action.smoke_validation.label,
            "--compose-file",
            action.smoke_validation.compose_file,
            "--service",
            action.smoke_validation.service,
            "--url",
            action.smoke_validation.url,
        ]
        if action.smoke_validation.contains:
            smoke_command.extend(["--contains", action.smoke_validation.contains])

        lines = [
            "set -euo pipefail",
            f"DEPLOY_DIR={deploy_dir}",
            'case "$DEPLOY_DIR" in "~"|"~/"*) DEPLOY_DIR="${HOME}${DEPLOY_DIR:1}" ;; esac',
            'cd "$DEPLOY_DIR"',
        ]
        if action.requires_remote_env:
            lines.extend(
                [
                    'if [ ! -f .env ]; then',
                    '  echo "Arquivo .env não encontrado em $DEPLOY_DIR"',
                    "  exit 1",
                    "fi",
                ]
            )

        compose_command = "docker compose"
        if action.smoke_validation.compose_file != "docker-compose.yml":
            compose_command = f"docker compose -f {shlex.quote(action.smoke_validation.compose_file)}"

        lines.append(f"printf '%s\\n' {shlex.quote(release_id)} > {shlex.quote(action.release_marker)}")
        lines.extend(action.prepare_commands)

        if action.image_repository and action.compose_image_env_var:
            image_ref = f"{action.image_repository}:{image_tag}"
            lines.extend(
                [
                    'TEMP_DOCKER_CONFIG="$(mktemp -d)"',
                    'cleanup() { rm -rf "$TEMP_DOCKER_CONFIG"; }',
                    'trap cleanup EXIT',
                    'export DOCKER_CONFIG="$TEMP_DOCKER_CONFIG"',
                    f"printf '%s' {shlex.quote(registry_token)} | docker login {DEFAULT_GHCR_REGISTRY} -u {shlex.quote(registry_username)} --password-stdin",
                    f"{action.compose_image_env_var}={shlex.quote(image_ref)} {compose_command} pull {shlex.quote(action.smoke_validation.service)}",
                    f"docker logout {DEFAULT_GHCR_REGISTRY} || true",
                ]
            )

        lines.extend(action.restart_commands)
        lines.append(shlex.join(smoke_command))

        if action.prune_after_success:
            lines.extend(
                [
                    "docker image prune -af || true",
                    "docker builder prune -af || true",
                    "docker system prune -f || true",
                    "docker system df",
                ]
            )

        return "\n".join(lines)

    def _drain_log_queue(self) -> None:
        while True:
            try:
                event, payload = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if event == "output" and isinstance(payload, str):
                self._append_log(payload)
            elif event == "status" and isinstance(payload, str):
                self.status_var.set(payload)
            elif event == "finished" and isinstance(payload, str):
                action_label, _, raw_code = payload.partition("|")
                exit_code = int(raw_code)
                status_text = (
                    f"{action_label} concluído com sucesso."
                    if exit_code == 0
                    else f"{action_label} falhou com código {exit_code}."
                )
                self._set_running(False, status_text)
                self._refresh_environment_label()

        self.root.after(120, self._drain_log_queue)

    def on_close(self) -> None:
        if self.command_running:
            should_close = messagebox.askyesno(
                "Fechar launcher",
                "Há um comando em execução. Deseja fechar a janela mesmo assim?",
            )
            if not should_close:
                return
        self.root.destroy()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Standalone launcher for direct DigitalOcean deploys from the local working tree.",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("OCEAN_HOST", DEFAULT_DEPLOY_HOST),
        help="Host ou IP do droplet da DigitalOcean.",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("OCEAN_USER", DEFAULT_DEPLOY_USER),
        help="Usuário SSH usado no deploy.",
    )
    parser.add_argument(
        "--port",
        default=os.getenv("OCEAN_PORT", DEFAULT_PORT),
        help=f"Porta SSH do droplet. Padrão: {DEFAULT_PORT}.",
    )
    parser.add_argument(
        "--key-path",
        default=get_default_key_path(),
        help="Caminho local da chave SSH privada. Também aceita a env OCEAN_SSH_KEY_PATH.",
    )
    parser.add_argument(
        "--host-fingerprint",
        default=os.getenv("OCEAN_HOST_FINGERPRINT", DEFAULT_DEPLOY_HOST_FINGERPRINT),
        help="Fingerprint SHA256 opcional para validar a host key do servidor.",
    )
    parser.add_argument(
        "--deploy-dir",
        default=os.getenv("OCEAN_APP_DIR", DEFAULT_DEPLOY_DIR),
        help="Diretório remoto onde o projeto será sincronizado.",
    )
    parser.add_argument(
        "--image-tag",
        default=os.getenv(DEFAULT_MANUAL_IMAGE_TAG_ENV, ""),
        help=(
            "Tag da imagem ja publicada no GHCR para o deploy manual. "
            "Quando omitida, o launcher exige working tree limpo e usa o commit atual."
        ),
    )
    parser.add_argument(
        "--registry-username",
        default=os.getenv("GHCR_USERNAME", os.getenv("GITHUB_ACTOR", "")),
        help="Usuario do GHCR. Quando omitido, tenta usar o GitHub CLI autenticado.",
    )
    parser.add_argument(
        "--registry-token",
        default=os.getenv("GHCR_TOKEN", os.getenv("GH_TOKEN", os.getenv("GITHUB_TOKEN", ""))),
        help="Token do GHCR. Quando omitido, tenta usar `gh auth token`.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    root = tk.Tk()
    DeployLauncher(
        root,
        host=args.host,
        user=args.user,
        port=args.port,
        key_path=args.key_path,
        host_fingerprint=args.host_fingerprint,
        deploy_dir=args.deploy_dir,
        image_tag=args.image_tag,
        registry_username=args.registry_username,
        registry_token=args.registry_token,
    )
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())