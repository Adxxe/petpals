"""界面文案。

有中文字体时输出中文，没有就自动退回英文——否则在缺少中文字体的设备上
会满屏方框（豆腐块）。
"""

from app import config
from app.fonts import is_cjk_ready


def t(zh, en):
    return zh if is_cjk_ready() else en


def app_title():
    return t(config.APP_TITLE_ZH, config.APP_TITLE_EN)


def menu_subtitle():
    return t("挑一只带回家", "Pick a buddy to take home")


def pet_name(pet):
    return t(pet.name_zh, pet.name_en)


def change_pet_label():
    return t("← 换一只", "← Change")


def playground_hint():
    return t("它会自己溜达 · 也可以按住拖走", "Wanders on its own · hold and drag it")


def offline_hint():
    return t("完全离线 · 不需要联网", "Fully offline · no network needed")


def overlay_button_label():
    return t("放到桌面", "To desktop")


def overlay_recall_label():
    return t("召回", "Recall")


def overlay_unavailable_hint():
    return t("悬浮桌宠只在安卓手机上可用（电脑上就用这个小天地）",
             "Desktop overlay works on Android only")


def overlay_need_permission_hint():
    return t("请先允许「显示在其他应用上层」，然后回来再点一次",
             "Allow \"display over other apps\", then tap again")
