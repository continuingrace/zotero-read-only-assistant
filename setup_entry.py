from __future__ import annotations

import ctypes
import json
import os
import shutil
import sys
from pathlib import Path

PLUGIN_NAME = "zotero-chatgpt"


def message(text: str, title: str = "Zotero for ChatGPT 설치") -> None:
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)


def error(text: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, text, "Zotero for ChatGPT 설치 오류", 0x10)


def payload_dir() -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root) / "payload" / PLUGIN_NAME
    return Path(__file__).resolve().parent / "plugins" / PLUGIN_NAME


def install() -> None:
    user_profile = os.environ.get("ZOTERO_CHATGPT_TEST_PROFILE") or os.environ.get("USERPROFILE")
    if not user_profile:
        raise RuntimeError("Windows 사용자 폴더를 확인할 수 없습니다")

    marketplace_root = Path(user_profile) / ".agents" / "plugins"
    plugin_target = Path(user_profile) / "plugins" / PLUGIN_NAME
    marketplace_path = marketplace_root / "marketplace.json"
    source = payload_dir()
    if not (source / ".codex-plugin" / "plugin.json").is_file():
        raise RuntimeError("설치 파일 안의 플러그인 구성을 찾을 수 없습니다")

    plugin_target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, plugin_target, dirs_exist_ok=True)

    if marketplace_path.is_file():
        try:
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError("기존 개인 플러그인 목록을 읽을 수 없습니다") from exc
    else:
        marketplace = {"name": "personal", "interface": {"displayName": "Personal"}, "plugins": []}

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        raise RuntimeError("개인 플러그인 목록 형식이 올바르지 않습니다")
    entry = {
        "name": PLUGIN_NAME,
        "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Education & Research",
    }
    marketplace["plugins"] = [item for item in plugins if not isinstance(item, dict) or item.get("name") != PLUGIN_NAME]
    marketplace["plugins"].append(entry)
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    marketplace_path.write_text(json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    try:
        install()
    except Exception as exc:
        error(f"설치하지 못했습니다.\n\n{exc}")
        raise SystemExit(1)
    message(
        "설치가 완료되었습니다.\n\n"
        "1. Zotero Desktop을 열어 두세요.\n"
        "2. ChatGPT 데스크톱 앱을 완전히 종료한 뒤 다시 여세요.\n"
        "3. 플러그인 탭의 개인 항목에서 'Zotero for ChatGPT'를 설치하세요.\n"
        "4. 새 일반 채팅에서 '내 Zotero 최근 자료 5개를 찾아줘'라고 입력하세요."
    )


if __name__ == "__main__":
    main()
