from __future__ import annotations

import ctypes
import os
import subprocess
import sys

from config import AUTO_ELEVATE_TO_ADMIN


_ELEVATION_ENV_FLAG = "AUI_TRANSLATOR_ELEVATED"


def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    if not is_windows():
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_admin_or_relaunch() -> bool:
    """
    Returns True, ha mar folytathato a futas az aktualis processzben.
    Returns False, ha elinditottunk egy admin ujrapeldanyt, es a jelenlegi
    processznek ki kell lepnie.
    """
    if not is_windows():
        return True
    if not AUTO_ELEVATE_TO_ADMIN:
        return True
    if is_admin():
        return True
    if os.getenv(_ELEVATION_ENV_FLAG) == "1":
        return True

    script_path = os.path.abspath(sys.argv[0])
    args = [script_path, *sys.argv[1:]]
    params = subprocess.list2cmdline(args)

    os.environ[_ELEVATION_ENV_FLAG] = "1"
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        params,
        None,
        1,
    )
    if int(result) <= 32:
        raise RuntimeError("Az admin jogu ujrainditas nem sikerult vagy megszakadt.")
    return False
