"""中文字体处理。

Kivy 自带的 Roboto 没有中文字形，直接用会显示成方框。
这里按顺序找一个能显示中文的字体，注册成 "AppFont"：

1. assets/fonts/ 下你自己放的字体（推荐：会一起打进 APK，手机端一定有）
2. 桌面系统的中文字体（只在 Windows/macOS 本地调试时用，不会被打包）
3. 都没有 -> 不注册，界面文字自动切成英文（见 app/i18n.py）

放字体时注意版权：请放可再分发的字体，例如 Noto Sans SC / 思源黑体（OFL 协议）。
"""

import os
import sys

from app.resources import asset_path

APP_FONT_NAME = "AppFont"
_FONT_EXTS = (".ttf", ".otf", ".ttc")

# 仅桌面调试用的系统字体，找不到就跳过；这些文件不会被复制进项目
_DESKTOP_FONTS = {
    "win32": (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyh.ttf",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\Deng.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ),
    "darwin": (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ),
}

_state = {"ready": None, "source": None}


def bundled_font():
    """assets/fonts/ 下第一个字体（按文件名排序，方便用 00-、01- 前缀控制优先级）。"""
    folder = asset_path("fonts")
    if not os.path.isdir(folder):
        return None
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(_FONT_EXTS):
            return os.path.join(folder, name)
    return None


def desktop_font():
    for path in _DESKTOP_FONTS.get(sys.platform, ()):
        if os.path.isfile(path):
            return path
    return None


def _register(path):
    from kivy.core.text import LabelBase

    LabelBase.register(name=APP_FONT_NAME, fn_regular=path)


def _renders_cjk():
    """真渲染一次来确认：字体能打开，而且确实有中文字形。

    判断"有没有中文字形"用的办法是：分别渲染一个中文字和一个私用区码位
    （基本所有字体都没有的码位，会画成 .notdef 方框），宽度一样就说明
    这个字体没有中文，只是把中文也画成了方框。
    """
    from kivy.core.text import Label as CoreLabel

    cjk = CoreLabel(text="宠", font_name=APP_FONT_NAME, font_size=32)
    cjk.refresh()
    width_cjk = cjk.texture.size[0] if cjk.texture else 0
    if width_cjk <= 0:
        return False

    missing = CoreLabel(text="\ue123", font_name=APP_FONT_NAME, font_size=32)
    missing.refresh()
    width_missing = missing.texture.size[0] if missing.texture else 0
    return width_cjk != width_missing


def register_app_font():
    """注册可用的中文字体并返回是否成功；结果会缓存，重复调用不会重复加载。"""
    if _state["ready"] is not None:
        return _state["ready"]

    _state["ready"] = False
    for path in (bundled_font(), desktop_font()):
        if not path:
            continue
        try:
            _register(path)
            if not _renders_cjk():
                continue
        except Exception:
            continue
        _state["ready"] = True
        _state["source"] = path
        break

    return _state["ready"]


def is_cjk_ready():
    return bool(_state["ready"])


def ui_font_name():
    """给 Label 用的字体名；没有中文字体时返回 None（用 Kivy 默认字体）。"""
    return APP_FONT_NAME if _state["ready"] else None


def font_source():
    """当前实际使用的字体文件路径（调试/自检用，可能为 None）。"""
    return _state["source"]
