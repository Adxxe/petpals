"""入口文件。

桌面调试：python main.py
Android 打包：buildozer android debug（入口就是本文件）

这里只做三件事：调 Kivy 参数、启动界面、返回退出码。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import WINDOW_SIZE  # noqa: E402  (不依赖 kivy，可以提前导入)


def _tune_kivy():
    """在创建窗口之前调参。低端手机上这几项对流畅度影响最直接。"""
    from kivy.config import Config

    from app.perf import FPS_IDLE

    # 关掉多重采样抗锯齿：省 GPU，老旧安卓机上提升明显
    Config.set("graphics", "multisamples", "0")
    # 帧率上限先按"静止页面"的 30 帧起（有动画时 app/perf.py 会切到 60）
    Config.set("graphics", "maxfps", str(FPS_IDLE))
    # 窗口尺寸只对桌面生效，手机上自动忽略
    Config.set("graphics", "width", str(WINDOW_SIZE[0]))
    Config.set("graphics", "height", str(WINDOW_SIZE[1]))
    Config.set("graphics", "resizable", "1")
    # 返回键交给我们自己处理（见 app/ui/app.py），别让 Kivy 直接退出应用
    Config.set("kivy", "exit_on_escape", "0")


def main():
    _tune_kivy()

    from app.ui import build_app

    build_app().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
