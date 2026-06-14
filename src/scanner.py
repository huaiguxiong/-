import os
from pathlib import Path

# 可执行文件名黑名单关键词（出现在文件名中即排除）
EXCLUDED_NAMES = {
    "unitycrashhandler", "unins", "setup", "install", "vc_redist", "dxsetup",
    "dotnet", "redist", "crashhandler", "crashpad", "vcredist", "directx",
    "oalinst", "gfwlivesetup", "xnafx", "openal", "bootstrap", "runtime",
    "host", "service", "agent", "helper", "sandbox", "renderer", "swiftshader",
    "ffmpeg", "node", "python", "java", "jre", "jdk", "launcher", "updater",
    "patch", "config", "settings", "reg", "register", "update", "version",
    "download", "downloads", "torrent", "qbittorrent", "utorrent", "transmission",
    "deluge", "aria2", "idm", "motrix", "fdm", "xunlei", "thunder", "baidunetdisk",
    "aliyunpan", "quark", "cloud", "onedrive", "dropbox", "googledrive", "rclone",
    "chrome", "firefox", "edge", "opera", "brave", "vivaldi", "browser", "iexplore",
    "explorer", "discord", "skype", "teams", "zoom", "qq", "wechat", "weixin",
    "dingtalk", "lark", "feishu", "tim", "wxwork", "office", "excel", "word",
    "powerpnt", "outlook", "onenote", "acrobat", "reader", "foxit", "wps",
    "vlc", "potplayer", "mpc-hc", "media", "player", "spotify", "netease",
    "qqmusic", "kugou", "winrar", "7z", "zip", "7zip", "bandizip", "peazip",
    "everything", "wiztree", "spacesniffer", "diskgenius", "partition", "defrag",
    "ccleaner", "geek", "avast", "avira", "bitdefender", "kaspersky", "norton",
    "360", "tencent", "huorong", "wegame", "epicgames", "origin", "anydesk",
    "teamviewer", "todesk", "rustdesk", "sunlogin", "向日葵", "notepad", "vscode",
    "sublime", "atom", "eclipse", "idea", "pycharm", "webstorm", "rider",
    "studio", "git", "svn", "wallpaper", "rainmeter", "powershell", "cmd",
    "terminal", "system", "sys", "boot", "bios", "recovery", "repair", "fix",
    "tool", "tools", "util", "utility", "diag", "benchmark", "bench", "test",
    "stress", "furmark", "heaven", "valley", "3dmark", "cinebench", "cpuid",
    "coretemp", "afterburner", "msi", "gpu-z", "cpu-z", "hwinfo", "speccy",
    "crystaldisk", "miner", "mining", "casino", "gamble", "bet", "lottery",
    "poker", "photoshop", "illustrator", "premiere", "aftereffect", "blender",
    "gimp", "paint", "obs", "streamlabs", "obs-studio", "nzb", "tmp", "temp",
    "cache", "log", "dump", "dat", "bin", "demo", "trial", "portable", "lite",
    "mini", "pro", "plus", "ultimate", "steam", "epic", "gog", "uplay",
    "battlenet", "bnet", "ea", "ubisoft", "galaxy", "itch", "parsec", "remotr",
    "moonlight", "sunshine", "rainway", "playnite", "launchbox", "gamejolt",
    "gamejoltclient", "goggalaxy", "egs", "originthin", "origin", "uplay",
}

# 目录黑名单：遇到这些目录名直接跳过（不区分大小写）
EXCLUDED_DIRS = {
    "windows", "program files", "program files (x86)", "programdata", "users",
    "public", "default", "perflogs", "inetpub", "recovery",
    "system volume information", "$recycle.bin", "recycler", "recycled",
    "temp", "tmp", "cache", "logs", "log", "crash dumps", "debug",
    "downloads", "download", "文档", "documents", "music", "pictures",
    "videos", "desktop", "saved games", "favorites", "links", "searches",
    "contacts", "onedrive", "dropbox", "google drive", "坚果云",
    "qq", "wechat", "weixin", "tencent", "360", "baidu", "alibaba",
    "alipay", "dingtalk", "lark", "feishu", "wps", "kingsoft",
    "mozilla", "google", "microsoft", "intel", "amd", "nvidia", "realtek",
    "common files", "windowsapps", "packages", "winsxs", "syswow64",
    "system32", "drivers", "driverstore", "fonts", "help", "mui", "oobe",
    "prefetch", "rescache", "schcache", "servicing", "winevt", "winhlp32",
    "appdata", "local", "locallow", "roaming", "startup", "start menu",
    "sendto", "recent", "cookies", "history", "application data",
    "epic games", "ea games", "steam", "steamlibrary", "steamapps",
    "gog", "origin", "ubisoft", "uplay", "battle.net", "battlenet",
    "overwatch", "call of duty", "x86", "wow6432node", "uninstall information",
    "installer", "installers", "installshield", "msocache", "netframework",
    "redist", "redistributable", "sdk", "runtimes", "runtime", "node_modules",
    "git", "svn", "repo", "repository", "source", "src", "build", "dist",
    "out", "output", "release", "obj", "bin", "__pycache__", "venv", "env",
    "virtualenv", "conda", "pyenv", "pip", "npm", "yarn", "pnpm", "gradle",
    "maven", "target", "classes", "artifacts", "libs", "lib", "library",
    "include", "includes", "third_party", "thirdparty", "3rdparty", "deps",
    "dependencies", "vendor", "externals", "external", "assets", "resources",
    "res", "data", "content", "raw", "sounds", "sound", "audio", "musique",
    "bgm", "voice", "voices", "se", "sfx", "texture", "textures", "tex",
    "material", "materials", "mesh", "meshes", "model", "models", "mdl",
    "animation", "animations", "anim", "anims", "motion", "motions",
    "cutscene", "cutscenes", "cinematic", "cinematics", "movie", "movies",
    "video", "fmv", "bik", "bk2", "usm", "mp4", "avi", "wmv", "mkv", "flv", "swf",
}


def is_likely_game(exe_name):
    """判断可执行文件名是否可能是游戏主程序。"""
    name_lower = exe_name.lower().replace(".exe", "")
    for excluded in EXCLUDED_NAMES:
        if excluded in name_lower:
            return False
    return True


def _should_skip_dir(dir_name):
    """判断目录名是否在黑名单中。"""
    name_lower = dir_name.lower()
    return name_lower in EXCLUDED_DIRS


def scan_directory(path, max_depth=12):
    """
    递归扫描目录，找出可能是游戏主程序的可执行文件。
    - 跳过黑名单目录，避免扎进 Downloads/Windows/Temp 等无关目录
    - max_depth 控制最大递归深度（默认 12，足够应对深层游戏目录）
    """
    found = set()
    root = Path(path)
    if not root.exists() or not root.is_dir():
        return found

    # 使用 os.walk 手动递归，可跳过黑名单目录和控制系统目录
    for dirpath, dirnames, filenames in os.walk(str(root)):
        # 计算当前深度
        depth = dirpath.count(os.sep) - str(root).count(os.sep)
        if depth > max_depth:
            # 不再深入，清空 dirnames 让 os.walk 不再递归
            dirnames[:] = []
            continue

        # 过滤掉黑名单目录，防止 os.walk 继续进入
        dirnames[:] = [
            d for d in dirnames
            if not _should_skip_dir(d)
        ]

        for fname in filenames:
            if fname.lower().endswith(".exe"):
                if is_likely_game(fname):
                    full_path = Path(dirpath) / fname
                    try:
                        found.add(str(full_path.resolve()))
                    except (OSError, ValueError):
                        #  resolve() 可能遇到特殊文件失败，回退到 abspath
                        found.add(str(full_path.absolute()))

    return found
