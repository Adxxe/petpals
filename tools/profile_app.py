"""给应用做一次性能体检，输出一份可对比的报告。

后续加功能之后，重新跑一遍对比数字，就能知道有没有变慢、慢在哪。
（桌面数字不等于手机数字，但趋势是有参考价值的。）

用法:
    python tools/profile_app.py                  # 隐藏窗口：启动耗时 / 纹理占用 / 每帧成本
    python tools/profile_app.py --seconds 4      # 额外真跑 4 秒主循环（会短暂弹出窗口），量帧率
    python tools/profile_app.py --pet dog        # 指定进小天地时带的宠物
"""

import argparse
import os
import statistics
import sys
import time

os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

STARTED = time.perf_counter()

import kivy  # noqa: E402

IMPORT_MS = (time.perf_counter() - STARTED) * 1000.0

from kivy.core.window import Window  # noqa: E402
from kivy.uix.image import Image  # noqa: E402

from app import catalog, perf  # noqa: E402
from app.resources import asset_path  # noqa: E402
from app.ui.app import ShellApp  # noqa: E402
from app.ui.menu import MENU_SCREEN  # noqa: E402
from app.ui.playground import PLAYGROUND_SCREEN  # noqa: E402

STEP_FRAMES = 600


def walk(widget):
    yield widget
    for child in widget.children:
        for item in walk(child):
            yield item


def texture_report(root):
    """统计界面里实际用到的纹理张数与显存占用（按纹理去重，共享的只算一次）。"""
    seen = {}
    for widget in walk(root):
        texture = getattr(widget, "texture", None)
        size = getattr(texture, "size", None)
        if texture is None or not size or size[0] <= 0:
            continue
        seen.setdefault(id(texture), (size[0], size[1], getattr(texture, "source", "")))
    total = sum(w * h * 4 for w, h, _src in seen.values())
    return len(seen), total / (1024.0 * 1024.0)


def decode_cost():
    """单独量每个素材的**冷**解码耗时（冷启动里最实在的一块）。

    必须先于 build() 调用：Kivy 的 CoreImage 会按文件名缓存，
    已经加载过的图片再量就是 0.0x ms 的假数字。
    """
    from kivy.core.image import Image as CoreImage

    rows = []
    files = [("pets/" + pet.id, pet.image_path()) for pet in catalog.PETS]
    files += [("ui/bg_menu", asset_path("ui", "bg_menu.png")),
              ("ui/bg_scene", asset_path("ui", "bg_scene.png")),
              ("ui/shadow", asset_path("ui", "shadow.png"))]
    for label, path in files:
        started = time.perf_counter()
        image = CoreImage(path)
        texture = image.texture
        elapsed = (time.perf_counter() - started) * 1000.0
        pixels = tuple(texture.size) if texture else (0, 0)
        rows.append((label, elapsed, pixels, os.path.getsize(path) / 1024.0))
    return rows


def clear_image_cache():
    """清掉 Kivy 的图片/纹理缓存，好让后面的计时也是冷的。"""
    from kivy.cache import Cache

    for category in ("kv.image", "kv.texture"):
        try:
            Cache.remove(category)
        except Exception:  # noqa: BLE001
            pass


def live_fps(app, seconds, pet):
    """真跑主循环：前半段在主菜单（静止），后半段在小天地（有动画）。"""
    from kivy.clock import Clock

    buckets = {"menu": [], "playground": []}
    current = {"name": "menu"}

    def on_frame(dt):
        buckets[current["name"]].append(dt)

    def enter_playground(_dt):
        current["name"] = "playground"
        app.show_pet(pet)

    Clock.schedule_once(enter_playground, seconds * 0.5)
    Clock.schedule_interval(on_frame, 0)
    Clock.schedule_once(lambda _dt: app.stop(), seconds)

    started = time.perf_counter()
    app.run()
    elapsed = time.perf_counter() - started

    report = {}
    for name, samples in buckets.items():
        if not samples:
            report[name] = None
            continue
        span = sum(samples)
        steady = samples[1:] if len(samples) > 1 else samples   # 去掉窗口起来那一帧
        steady_span = sum(steady)
        ordered = sorted(samples)
        report[name] = {
            "frames": len(samples),
            "fps": len(samples) / span if span else 0.0,
            "steady_fps": len(steady) / steady_span if steady_span else 0.0,
            "p50_ms": statistics.median(ordered) * 1000.0,
            "p99_ms": ordered[int(len(ordered) * 0.99) - 1] * 1000.0,
            "worst_ms": ordered[-1] * 1000.0,
        }
    return report, elapsed


def main():
    parser = argparse.ArgumentParser(description="PetPals 性能体检")
    parser.add_argument("--seconds", type=float, default=0.0,
                        help="真跑主循环的秒数（默认 0 = 不跑，只做静态体检）")
    parser.add_argument("--pet", default="cat", help="进小天地时带的宠物 id")
    args = parser.parse_args()

    pet = catalog.get_pet(args.pet) or catalog.PETS[0]

    # 注意：隐藏窗口 + 跑主循环在 Windows 上会让 Kivy 崩（SDL2 swap 的问题），
    # 所以要跑主循环时不隐藏窗口。
    if args.seconds <= 0:
        Window.hide()

    print("=== PetPals 性能体检（桌面参考值，不等于手机）===")
    print("kivy 导入                 {0:8.1f} ms".format(IMPORT_MS))

    decode_rows = decode_cost()   # 冷解码，必须早于 build()
    clear_image_cache()

    app = ShellApp()
    started = time.perf_counter()
    root = app.build()
    build_ms = (time.perf_counter() - started) * 1000.0
    counts, mbytes = texture_report(root)
    print("界面构建（主菜单）         {0:8.1f} ms".format(build_ms))
    print("  启动纹理占用             {0:8.2f} MB / {1} 张".format(mbytes, counts))

    started = time.perf_counter()
    art_before = root.get_screen(PLAYGROUND_SCREEN).background.texture is not None
    app.show_pet(pet)
    select_ms = (time.perf_counter() - started) * 1000.0
    play = root.get_screen(PLAYGROUND_SCREEN)
    art_after = play.background.texture is not None

    art_started = time.perf_counter()
    play.on_enter()
    art_ms = (time.perf_counter() - art_started) * 1000.0
    counts2, mbytes2 = texture_report(root)
    decoded_here = (not art_before) and art_after
    print("选中宠物 -> 小天地         {0:8.1f} ms{1}".format(
        select_ms, "（含首次场景解码）" if decoded_here else ""))
    if not decoded_here:
        print("  进页面时补解码             {0:8.1f} ms".format(art_ms))
    print("  小天地纹理占用           {0:8.2f} MB / {1} 张".format(mbytes2, counts2))

    started = time.perf_counter()
    for _ in range(STEP_FRAMES):
        play._step(1.0 / 60.0)
    per_frame = (time.perf_counter() - started) / STEP_FRAMES * 1000.0
    play.on_leave()
    print("每帧推进（{0} 帧均值）   {1:8.4f} ms/帧".format(STEP_FRAMES, per_frame))

    print("--- 素材冷解码耗时 ---")
    for label, ms, pixels, kb in decode_rows:
        print("  {0:<14} {1:7.2f} ms  {2[0]}x{2[1]}  {3:6.1f} KB".format(label, ms, pixels, kb))

    print("--- 帧率上限 ---")
    print("  当前设置                 {0} FPS".format(perf.current_fps_cap()))

    if args.seconds > 0:
        print("--- 主循环（{0:.1f} 秒，窗口会短暂出现）---".format(args.seconds))
        app2 = ShellApp()
        report, elapsed = live_fps(app2, args.seconds, pet)
        for name in ("menu", "playground"):
            row = report[name]
            if row is None:
                print("  {0:<10} 无采样".format(name))
                continue
            print("  {0:<10} {1:5.1f} FPS（稳定后 {2:5.1f}）帧数 {3:4d}  p50 {4:5.2f} ms  p99 {5:5.2f} ms  最差 {6:6.2f} ms"
                  .format(name, row["fps"], row["steady_fps"], row["frames"],
                          row["p50_ms"], row["p99_ms"], row["worst_ms"]))
        print("  实际跑了 {0:.2f} 秒".format(elapsed))
    else:
        print("（加 --seconds 4 可以真跑一会儿主循环，量实际帧率和掉帧）")

    Window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
