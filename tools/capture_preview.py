"""跑一小段真实主循环并截图，用来快速看界面长什么样。

不参与打包（buildozer.spec 已经把 tools/ 排除掉了）。
运行时会真的弹出应用窗口，大约 1 秒，截完图自动退出。

用法:
    python tools/capture_preview.py
    python tools/capture_preview.py --out docs/shot.png --seconds 2
    python tools/capture_preview.py --pet cat --out docs/detail.png
"""

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

from kivy.config import Config  # noqa: E402

from app.config import WINDOW_SIZE  # noqa: E402

# 截图窗口按手机比例，预览才有参考价值
Config.set("graphics", "width", str(WINDOW_SIZE[0]))
Config.set("graphics", "height", str(WINDOW_SIZE[1]))
Config.set("graphics", "multisamples", "0")

from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402

from app import catalog  # noqa: E402
from app.ui.app import ShellApp  # noqa: E402


def collect_screenshot(target):
    """Kivy 会把文件名改写成 xxx0001.png，这里把它挪回我们想要的文件名。"""
    folder = os.path.dirname(target) or os.getcwd()
    stem, ext = os.path.splitext(os.path.basename(target))
    candidates = [os.path.join(folder, name) for name in os.listdir(folder)
                  if name.startswith(stem) and name.endswith(ext)]
    if not candidates:
        return None
    newest = max(candidates, key=os.path.getmtime)
    if os.path.abspath(newest) != os.path.abspath(target):
        if os.path.exists(target):
            os.remove(target)
        os.replace(newest, target)
    return target


def main():
    parser = argparse.ArgumentParser(description="截图看界面")
    parser.add_argument("--out", default=os.path.join(ROOT, "docs", "preview_menu.png"),
                        help="输出 PNG 路径")
    parser.add_argument("--seconds", type=float, default=1.2,
                        help="窗口停留时间（默认 1.2 秒）")
    parser.add_argument("--pet", default="",
                        help="给了就直接带这只宠物进小天地，例如 --pet cat")
    args = parser.parse_args()

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    pet = None
    if args.pet:
        pet = catalog.get_pet(args.pet)
        if pet is None:
            print("没有这只宠物: {0}（可选: {1}）".format(
                args.pet, ", ".join(p.id for p in catalog.PETS)))
            return 1

    app = ShellApp()
    frames = {"count": 0}

    def count_frame(_dt):
        frames["count"] += 1

    def snap(_dt):
        Window.screenshot(name=args.out)

    def select_pet(_dt):
        # 注意：App.run() 自己会调 build()，所以要等主循环起来之后再切页面，
        # 否则切的是另一棵没被显示的控件树（踩过一次）。
        app.show_pet(pet)

    if pet is not None:
        Clock.schedule_once(select_pet, 0.1)
    Clock.schedule_interval(count_frame, 0)
    Clock.schedule_once(snap, args.seconds * 0.7)
    Clock.schedule_once(lambda _dt: app.stop(), args.seconds)

    started = time.perf_counter()
    app.run()
    elapsed = time.perf_counter() - started

    saved = collect_screenshot(args.out)
    fps = frames["count"] / elapsed if elapsed > 0 else 0
    from app import perf

    print("窗口停留 {0:.2f}s，渲染 {1} 帧，约 {2:.0f} FPS（帧率上限 {3}，桌面参考值）".format(
        elapsed, frames["count"], fps, perf.current_fps_cap()))
    if saved:
        print("截图已保存: {0} ({1} bytes)".format(saved, os.path.getsize(saved)))
        return 0
    print("截图失败：没找到 Kivy 输出的 PNG")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
