"""资源路径。

Android(python-for-android) 和桌面下 __file__ 都指向项目内的真实路径，
直接用它拼绝对路径即可，不需要联网、也不需要额外权限。
"""

import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")


def asset_path(*parts):
    """返回 assets 下某个文件的绝对路径，例如 asset_path("pets", "cat.png")。"""
    return os.path.join(ASSETS_DIR, *parts)


def asset_exists(*parts):
    return os.path.isfile(asset_path(*parts))
