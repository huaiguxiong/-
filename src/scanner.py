import os
from pathlib import Path

EXCLUDED_NAMES = {
    "unitycrashhandler", "unins000", "unins001", "setup", "install",
    "vc_redist", "dxsetup", "dotnet", "redist", "crashhandler",
    "steam", "epic", "launcher", "updater", "patch", "config",
    "settings", "reg", "register", "vcredist", "directx", "vcredist",
    "oalinst", "gfwlivesetup", "xnafx", "openal"
}


def is_likely_game(exe_name):
    name_lower = exe_name.lower().replace(".exe", "")
    for excluded in EXCLUDED_NAMES:
        if excluded in name_lower:
            return False
    return True


def scan_directory(path):
    """递归扫描目录，找出可能是游戏主程序的可执行文件。"""
    found = set()
    path = Path(path)
    if not path.exists() or not path.is_dir():
        return found

    for exe in path.rglob("*.exe"):
        if is_likely_game(exe.name):
            found.add(str(exe.resolve()))

    return found
