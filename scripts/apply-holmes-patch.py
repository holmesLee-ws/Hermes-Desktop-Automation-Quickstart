from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_INSTALL = (
    Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    / "hermes"
    / "hermes-agent"
)
DEFAULT_HERMES_HOME = DEFAULT_INSTALL.parent
DEFAULT_REMOTE_URL = "https://github.com/holmesLee-ws/hermes-agent.git"
DEFAULT_SOURCE_BRANCH = "holmes/live-main"
PATCH_VERSION = "1.1.1"
EXPECTED_COMMIT = "b244576e48206f3ade97cac5d0b8125033970c66"
LOCAL_SOURCE_REF = "refs/hermes-quickstart/source"
LOCAL_PATCH_BRANCH = "local/holmes-live-main"

SKILL_MARKER = "Credential entry is allowed only when the user explicitly requests it"
SKILL_INSERT = """- **Credential entry is allowed only when the user explicitly requests it for
  a named login target.** Prefer password-manager autofill or clipboard paste
  that does not reveal the value. Never read, display, log, echo, save, or
  retain the credential. A login request is not permission to approve a
  payment, purchase, transfer, account recovery, or unrelated prompt.
"""
LEGACY_SKILL_BLOCK = """- **Never click permission dialogs, password prompts, payment UI, 2FA
  challenges, or anything the user didn't explicitly ask for.** Stop
  and ask instead.
- **Never type passwords, API keys, credit card numbers, or any
  secret.**
"""


def run(
    cwd: Path, *args: str, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    print(">", subprocess.list2cmdline(args), flush=True)
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
    )


def output(cwd: Path, *args: str) -> str:
    return run(cwd, *args, capture=True).stdout.strip()


def optional_output(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def validate_remote_url(remote_url: str) -> None:
    if any(char in remote_url for char in ("\0", "\r", "\n")):
        raise RuntimeError("--remote-url에 제어 문자를 포함할 수 없습니다.")

    segment = r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?"
    repository = rf"{segment}/{segment}(?:\.git)?"
    allowed_patterns = (
        rf"https://github\.com/{repository}",
        rf"ssh://git@github\.com/{repository}",
        rf"git@github\.com:{repository}",
    )
    if not any(
        re.fullmatch(pattern, remote_url, flags=re.IGNORECASE | re.ASCII)
        for pattern in allowed_patterns
    ):
        raise RuntimeError(
            "--remote-url에는 인증정보 없는 GitHub HTTPS/SSH 저장소 URL만 지정하세요."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply the pinned Holmes Hermes patch to a Windows Git installation."
    )
    parser.add_argument("--install", type=Path, default=DEFAULT_INSTALL)
    parser.add_argument("--hermes-home", type=Path, default=DEFAULT_HERMES_HOME)
    parser.add_argument("--remote-url", default=DEFAULT_REMOTE_URL)
    parser.add_argument("--branch", default=DEFAULT_SOURCE_BRANCH)
    parser.add_argument("--expected-commit", default=EXPECTED_COMMIT)
    parser.add_argument(
        "--version",
        action="version",
        version=f"apply-holmes-patch {PATCH_VERSION}",
    )
    return parser.parse_args()


def resolve_uv(install: Path) -> Path:
    candidates = [
        shutil.which("uv"),
        str(install.parent / "bin" / "uv.exe"),
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "bin" / "uv.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    raise RuntimeError(
        "uv를 찾을 수 없습니다. Hermes 관리형 bin 또는 PATH를 확인하세요."
    )


def patch_profile_skill(
    source_skill: Path, profile_skill: Path, backup_root: Path
) -> Path | None:
    """Align the active profile copy while preserving unrelated local guidance."""
    if not source_skill.is_file():
        raise RuntimeError(f"번들 Computer Use 스킬을 찾을 수 없습니다: {source_skill}")

    if not profile_skill.exists():
        profile_skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_skill, profile_skill)
        return None

    text = profile_skill.read_text(encoding="utf-8")
    updated = text.replace(LEGACY_SKILL_BLOCK, "")
    if SKILL_MARKER not in updated:
        heading = "## Safety — these are hard rules\n\n"
        if heading not in updated:
            raise RuntimeError(
                f"프로필 스킬의 Safety 섹션을 찾을 수 없습니다: {profile_skill}"
            )
        updated = updated.replace(heading, heading + SKILL_INSERT, 1)
    if updated == text:
        return None

    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / "SKILL.md"
    shutil.copy2(profile_skill, backup)
    profile_skill.write_text(updated, encoding="utf-8")
    return backup


def install_editable(install: Path, uv: Path, python: Path) -> None:
    run(
        install,
        str(uv),
        "pip",
        "install",
        "--python",
        str(python),
        "-e",
        ".[all]",
    )


def restore_source(install: Path, previous_head: str, previous_branch: str) -> None:
    if previous_branch:
        run(install, "git", "switch", previous_branch)
        run(install, "git", "reset", "--hard", previous_head)
    else:
        run(install, "git", "switch", "--detach", previous_head)


def main() -> int:
    args = parse_args()
    validate_remote_url(args.remote_url)
    print(f"apply-holmes-patch {PATCH_VERSION}")
    install = args.install.resolve()
    hermes_home = args.hermes_home.resolve()
    python = install / "venv" / "Scripts" / "python.exe"
    hermes = install / "venv" / "Scripts" / "hermes.exe"

    if shutil.which("git") is None:
        raise RuntimeError("git을 찾을 수 없습니다.")
    if not install.is_dir() or not (install / ".git").exists():
        raise RuntimeError(f"Hermes Git 설치본을 찾을 수 없습니다: {install}")
    if not python.is_file() or not hermes.is_file():
        raise RuntimeError(f"Hermes 가상환경을 찾을 수 없습니다: {install / 'venv'}")
    uv = resolve_uv(install)

    dirty = output(install, "git", "status", "--porcelain")
    if dirty:
        raise RuntimeError(
            "로컬 Hermes 소스에 커밋되지 않은 변경사항이 있습니다.\n"
            f"{dirty}\n변경을 커밋·stash·백업한 뒤 다시 실행하세요."
        )

    source_ref = f"refs/heads/{args.branch}"
    fetch_spec = f"+{source_ref}:{LOCAL_SOURCE_REF}"
    run(install, "git", "fetch", args.remote_url, fetch_spec)
    branch_head = output(install, "git", "rev-parse", "--verify", LOCAL_SOURCE_REF)
    expected = args.expected_commit.lower()
    if re.fullmatch(r"[0-9a-f]{40}", expected) is None:
        raise RuntimeError("--expected-commit에는 40자리 Git SHA를 지정하세요.")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", expected, branch_head],
        cwd=install,
        check=False,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise RuntimeError(
            "검증된 고정 커밋이 원격 브랜치 이력에 없습니다.\n"
            f"expected:    {expected}\nbranch HEAD: {branch_head}\n"
            "원격 이력이 변경됐습니다. 새 커밋을 검토한 뒤 고정값을 갱신하세요."
        )
    target = expected

    previous_head = output(install, "git", "rev-parse", "HEAD")
    previous_branch = optional_output(
        install, "git", "symbolic-ref", "--quiet", "--short", "HEAD"
    )
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_branch = f"backup/pre-holmes-{stamp}"
    backup_root = hermes_home / "backups" / "computer-use" / stamp
    profile_skill = (
        hermes_home / "skills" / "autonomous-ai-agents" / "computer-use" / "SKILL.md"
    )
    source_skill = (
        install / "skills" / "autonomous-ai-agents" / "computer-use" / "SKILL.md"
    )
    profile_existed = profile_skill.exists()
    profile_before = profile_skill.read_bytes() if profile_existed else None

    run(install, "git", "branch", backup_branch, previous_head)
    try:
        run(install, "git", "switch", "-C", LOCAL_PATCH_BRANCH, target)
        install_editable(install, uv, python)

        profile_backup = patch_profile_skill(source_skill, profile_skill, backup_root)
        if profile_backup:
            print(f"프로필 스킬 백업: {profile_backup}")

        schema_probe = (
            "from tools.computer_use.schema import COMPUTER_USE_SCHEMA; "
            "s=COMPUTER_USE_SCHEMA['description'].lower(); "
            "assert 'explicit user request' in s; "
            "assert 'never expose or persist' in s; "
            "assert 'payment' in s; "
            "print('computer-use runtime schema: PASS')"
        )
        run(install, str(python), "-c", schema_probe)
        source_text = source_skill.read_text(encoding="utf-8")
        profile_text = profile_skill.read_text(encoding="utf-8")
        for label, text in (("번들", source_text), ("프로필", profile_text)):
            if SKILL_MARKER not in text or LEGACY_SKILL_BLOCK in text:
                raise RuntimeError(
                    f"{label} Computer Use 스킬 정책 검증에 실패했습니다."
                )
        if output(install, "git", "status", "--porcelain"):
            raise RuntimeError("패치 저장소에 예상하지 않은 변경사항이 생겼습니다.")
        run(install, str(hermes), "--version")
    except Exception:
        print(
            f"\n실패하여 소스를 {previous_head}으로 되돌립니다.",
            file=sys.stderr,
        )
        restore_source(install, previous_head, previous_branch)
        if profile_before is not None:
            profile_skill.parent.mkdir(parents=True, exist_ok=True)
            profile_skill.write_bytes(profile_before)
        elif not profile_existed and profile_skill.exists():
            profile_skill.unlink()
        try:
            install_editable(install, uv, python)
        except (OSError, subprocess.SubprocessError) as restore_error:
            print(
                f"이전 Python 환경 재설치도 실패했습니다: {restore_error}",
                file=sys.stderr,
            )
        raise

    print("\n적용 및 검증 완료")
    print(f"설치 경로: {install}")
    print(f"Hermes 홈: {hermes_home}")
    print(f"백업 브랜치: {backup_branch}")
    print(f"패치 브랜치: {LOCAL_PATCH_BRANCH}")
    print(f"고정 커밋: {target}")
    print("Hermes와 Orca를 다시 시작하고 /reset으로 새 세션을 여세요.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            message = f"명령이 종료 코드 {exc.returncode}로 끝났습니다."
        else:
            message = str(exc)
        print(f"\n적용 실패: {message}", file=sys.stderr)
        raise SystemExit(1)
