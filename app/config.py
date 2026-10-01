"""应用级常量。

改名字、改版本、改包名都只改这个文件（版本号要和 buildozer.spec 保持一致，
tests/smoke_test.py 会检查这一点）。
"""

# 窗口标题只能用英文：桌面窗口标题栏不一定有中文字体
APP_TITLE_EN = "PetPals"

# 应用内显示名（有中文字体时用这个）
APP_TITLE_ZH = "宠物伙伴"

# 版本号，必须和 buildozer.spec 里的 version 一致
APP_VERSION = "0.7.0"

# Android 包名 = PACKAGE_DOMAIN + "." + PACKAGE_NAME
PACKAGE_DOMAIN = "com.example"
PACKAGE_NAME = "petpals"

# 桌面调试时的窗口尺寸，接近手机竖屏比例
WINDOW_SIZE = (400, 780)

# 小天地场景里地平线的高度占比（从底部算起）。
# 场景素材 tools/make_ui_assets.py 也读这个值，保证画面和活动区域对得上。
SCENE_HORIZON = 0.46
