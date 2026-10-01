"""离线自检：不需要装 Kivy 就能跑。

检查五件事：
  1. 预设宠物名录和素材（尺寸、透明通道、边角确实是透明的）
  2. 界面素材（菜单背景够亮、场景有天地、影子边缘透明）
  3. 桌宠的自主活动逻辑（不越界、会动、能拖、拖完继续走、可复现）
  4. 源码里没有任何联网 / 动态执行 / 打开文件的行为（"零后门"的自证），
     也没有用 Kivy 已废弃的 Image 属性
  5. app/config.py 和 buildozer.spec 的版本号、包名一致；没中文字体时文案退回英文

用法: python tests/smoke_test.py
"""

import configparser
import json
import os
import random
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import android_bridge, catalog, config, i18n, overlay, pet_layout  # noqa: E402
from app.roaming import Roamer  # noqa: E402

FAILURES = []

# 源码里不允许出现的写法：联网、动态执行、文件读取（离线 + 无后门的自证）
BANNED = (
    "import socket", "from socket", "import urllib", "from urllib",
    "import requests", "from requests", "import http", "from http",
    "import subprocess", "from subprocess", "import ctypes", "from ctypes",
    "import pickle", "from pickle", "import marshal", "from marshal",
    "import base64", "from base64",
    "os.system", "os.popen", "eval(", "exec(", "compile(", "__import__",
    "open(", "http://", "https://",
)

# Kivy 2.3 起已废弃，将来的版本会直接删掉
DEPRECATED = ("allow_stretch", "keep_ratio")

# service.py 是打包进 APK 的后台服务，也要一起扫
SCANNED_FILES = ("main.py", "service.py")
SCANNED_DIRS = ("app", "tools")

UI_ASSETS = ("bg_menu.png", "bg_scene.png", "shadow.png")
ROOT_ASSETS = ("icon.png", "presplash.png")

# 悬浮桌宠需要的权限，多一个都不行
EXPECTED_PERMISSIONS = {"SYSTEM_ALERT_WINDOW", "FOREGROUND_SERVICE", "POST_NOTIFICATIONS"}


def check(label, fn):
    try:
        fn()
    except AssertionError as exc:
        FAILURES.append(label)
        print("FAIL {0} -> {1}".format(label, exc))
    except Exception as exc:  # noqa: BLE001
        FAILURES.append(label)
        print("ERROR {0} -> {1}: {2}".format(label, type(exc).__name__, exc))
    else:
        print("PASS {0}".format(label))


def png_header(path):
    """不依赖 Pillow，直接读 PNG 头，返回 (宽, 高, 位深, 颜色类型)。颜色类型 6 = RGBA。"""
    with open(path, "rb") as handle:
        head = handle.read(33)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", "不是 PNG 文件"
    assert head[12:16] == b"IHDR", "PNG 头缺少 IHDR"
    width, height = struct.unpack(">II", head[16:24])
    return width, height, head[24], head[25]


def source_files():
    for name in SCANNED_FILES:
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            yield path
    for folder in SCANNED_DIRS:
        base = os.path.join(ROOT, folder)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for filename in sorted(filenames):
                if filename.endswith(".py"):
                    yield os.path.join(dirpath, filename)


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def pillow_or_skip(label):
    try:
        from PIL import Image
    except ImportError:
        print("SKIP {0}（这个环境没装 Pillow）".format(label))
        return None
    return Image


"""---------------- 1. 宠物名录与抠图 ----------------"""


def pets_catalog():
    assert len(catalog.PETS) >= 4, "至少要有 4 只预设宠物"
    ids = [pet.id for pet in catalog.PETS]
    assert len(ids) == len(set(ids)), "宠物 id 有重复: {0}".format(ids)
    for pet in catalog.PETS:
        assert pet.name_zh and pet.name_en, pet.id
        assert pet.image.endswith(".png"), pet.id
        assert catalog.get_pet(pet.id) is pet
    assert catalog.get_pet("not-a-pet") is None


def pet_images():
    for pet in catalog.PETS:
        path = pet.image_path()
        assert os.path.isfile(path), "缺少素材: {0}".format(path)
        width, height, _depth, color_type = png_header(path)
        assert color_type == 6, "{0} 不是 RGBA（没有透明通道）".format(pet.id)
        assert width == height >= 256, "{0} 尺寸不合适: {1}x{2}".format(pet.id, width, height)
        assert os.path.getsize(path) < 512 * 1024, "{0} 文件过大".format(pet.id)


def pet_images_transparent():
    Image = pillow_or_skip("抠图透明检查")
    if Image is None:
        return
    for pet in catalog.PETS:
        with Image.open(pet.image_path()) as img:
            alpha = img.convert("RGBA").getchannel("A")
            corners = [alpha.getpixel((0, 0)), alpha.getpixel((img.width - 1, 0)),
                       alpha.getpixel((0, img.height - 1)),
                       alpha.getpixel((img.width - 1, img.height - 1))]
            assert corners == [0, 0, 0, 0], "{0} 四角不是透明的: {1}".format(pet.id, corners)
            bbox = alpha.getbbox()
            assert bbox is not None, "{0} 整张图都是空的".format(pet.id)
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            assert area > 0.15 * img.width * img.height, "{0} 抠图内容太小".format(pet.id)


def pet_part_images():
    """每只宠物都得有 身子 + 符合物种的四肢 + 全身静态图。"""
    for pet in catalog.PETS:
        roles = ["paw"] if pet.species() == "quadruped" else ["wing", "claw"]
        targets = [("body", pet.body_path()), ("full", pet.full_path())]
        targets += [(role, pet.limb_path(role)) for role in roles]
        for label, path in targets:
            assert os.path.isfile(path), "缺少素材: {0}".format(path)
            width, height, _depth, color_type = png_header(path)
            assert color_type == 6, "{0} 的 {1} 不是 RGBA".format(pet.id, label)
            assert width == height >= 64, "{0} 的 {1} 尺寸不对: {2}".format(
                pet.id, label, width)


def pet_full_body_content():
    """全身图必须真的画出了下半身（腿脚），不是只有一个头。"""
    Image = pillow_or_skip("全身图内容检查")
    if Image is None:
        return
    for pet in catalog.PETS:
        with Image.open(pet.full_path()) as img:
            alpha = img.convert("RGBA").getchannel("A")
            width, height = alpha.size
            box = alpha.getbbox()
            assert box is not None, "{0} 全身图是空的".format(pet.id)
            assert (box[2] - box[0]) > 0.45 * width, (pet.id, box)
            assert (box[3] - box[1]) > 0.6 * height, (pet.id, box)
            lower = alpha.crop((0, int(height * 0.78), width, height))
            assert lower.getbbox() is not None, "{0} 没有腿脚".format(pet.id)


def pet_layout_sane():
    """骨架要合法、要符合物种，而且四肢必须压在身子上（不能飘在外面）。"""
    for species, layout in pet_layout.LAYOUTS.items():
        for part in layout:
            x, y, side = part.rect
            assert 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0, (species, part.name, x, y)
            assert 0.0 < side <= 1.0, (species, part.name, side)
            assert x + side <= 1.001 and y + side <= 1.001, (species, part.name)
        assert any(part.role == "head" for part in layout), species
        assert any(part.role == "body" for part in layout), species

    # 四足（猫/狗/兔）是坐姿：两条前爪，**没有**像人一样的手臂/翅膀
    quad_roles = [part.role for part in pet_layout.LAYOUTS["quadruped"]]
    assert quad_roles.count("paw") == 2, quad_roles
    assert "wing" not in quad_roles and "claw" not in quad_roles, quad_roles

    # 小鸟：一对翅膀 + 两只小爪子（不是腿）
    bird_roles = [part.role for part in pet_layout.LAYOUTS["bird"]]
    assert bird_roles.count("wing") == 2, bird_roles
    assert bird_roles.count("claw") == 2, bird_roles
    assert "paw" not in bird_roles, bird_roles

    # 四肢必须和身子有重叠，不能飘在身体外面
    for species, layout in pet_layout.LAYOUTS.items():
        body = [part for part in layout if part.role == "body"][0].rect
        for part in layout:
            if not part.is_limb:
                continue
            px, py, pside = part.rect
            assert px < body[0] + body[2] and px + pside > body[0], \
                "{0}.{1} 横向和身子没重叠".format(species, part.name)
            assert py < body[1] + body[2] and py + pside > body[1], \
                "{0}.{1} 纵向和身子没重叠".format(species, part.name)


def app_icon():
    path = os.path.join(ROOT, "assets", "icon.png")
    assert os.path.isfile(path), "缺少 assets/icon.png"
    width, height, _depth, color_type = png_header(path)
    assert width == height >= 256, "图标尺寸不合适: {0}x{1}".format(width, height)
    assert color_type == 6, "图标应为 RGBA"


def font_folder():
    assert os.path.isfile(os.path.join(ROOT, "assets", "fonts", "README.txt")), \
        "assets/fonts/ 说明文件丢失"


"""---------------- 2. 界面素材 ----------------"""


def ui_assets_exist():
    for name in UI_ASSETS:
        path = os.path.join(ROOT, "assets", "ui", name)
        assert os.path.isfile(path), "缺少界面素材 assets/ui/{0}".format(name)
        width, height, _depth, color_type = png_header(path)
        assert width > 0 and height > 0, name
        assert color_type == 6, "{0} 应该是 RGBA".format(name)
        assert os.path.getsize(path) < 1024 * 1024, "{0} 太大".format(name)

    for name in ROOT_ASSETS:
        path = os.path.join(ROOT, "assets", name)
        assert os.path.isfile(path), "缺少素材 assets/{0}".format(name)

    # 菜单背景是纯柔和渐变，故意用半分辨率（显存 1/4、解码更快）：
    # 像素数应该明显小于场景图，否则说明有人把它生成成整分辨率了
    menu_w, menu_h, _d, _c = png_header(os.path.join(ROOT, "assets", "ui", "bg_menu.png"))
    scene_w, scene_h, _d, _c = png_header(os.path.join(ROOT, "assets", "ui", "bg_scene.png"))
    assert menu_w * menu_h < scene_w * scene_h * 0.5, \
        "菜单背景应该保持半分辨率: {0}x{1} vs 场景 {2}x{3}".format(
            menu_w, menu_h, scene_w, scene_h)


def ui_assets_content():
    Image = pillow_or_skip("界面素材内容检查")
    if Image is None:
        return

    # 菜单背景必须够亮：主题用的是深色文字，背景一暗就看不清了
    with Image.open(os.path.join(ROOT, "assets", "ui", "bg_menu.png")) as img:
        average = img.convert("RGB").resize((1, 1), Image.LANCZOS).getpixel((0, 0))
    assert min(average) > 180, "菜单背景太暗，深色文字会看不清: {0}".format(average)

    # 场景：上面是天空（偏蓝），地平线以下是草地（绿色最多）
    with Image.open(os.path.join(ROOT, "assets", "ui", "bg_scene.png")) as img:
        scene = img.convert("RGB")
        width, height = scene.size
        for ratio in (0.10, 0.45):
            r, g, b = scene.getpixel((int(ratio * width), int(0.04 * height)))
            assert b > g > r, "场景顶部应该是蓝天: {0}".format((r, g, b))
        horizon = (1.0 - config.SCENE_HORIZON) * height
        greens = 0
        for ratio in (0.08, 0.28, 0.50, 0.72, 0.92):
            r, g, b = scene.getpixel((int(ratio * width), int(horizon + 0.12 * height)))
            if g > b and g > r:
                greens += 1
        assert greens >= 4, "地平线以下应该是草地，只有 {0}/5 个采样点偏绿".format(greens)

    # 影子：中间深、往外单调变淡、边缘几乎透明（线性衰减会变成灰色方框）
    with Image.open(os.path.join(ROOT, "assets", "ui", "shadow.png")) as img:
        alpha = img.convert("RGBA").getchannel("A")
        width, height = alpha.size
        assert alpha.getpixel((0, 0)) == 0, "影子四角应该是透明的"
        center = alpha.getpixel((width // 2, height // 2))
        assert center > 120, "影子中间应该是不透明的: {0}".format(center)
        samples = [alpha.getpixel((int(width * ratio), height // 2))
                   for ratio in (0.5, 0.65, 0.8, 0.92)]
        assert all(samples[i] >= samples[i + 1] for i in range(len(samples) - 1)), samples
        assert samples[-1] < 0.25 * center, \
            "影子边缘还太实，会看起来像方框: {0}（中心 {1}）".format(samples, center)


"""---------------- 3. 桌宠自主活动逻辑 ----------------"""


def roaming_stays_in_bounds():
    roamer = Roamer((300.0, 200.0), speed=80.0, rng=random.Random(11))
    for _ in range(3000):
        roamer.advance(1.0 / 60.0)
        x, y = roamer.pos
        assert 0.0 <= x <= 300.0 and 0.0 <= y <= 200.0, (x, y)


def roaming_moves():
    roamer = Roamer((300.0, 200.0), speed=80.0, rng=random.Random(3))
    start = tuple(roamer.pos)
    walked = 0.0
    previous = tuple(roamer.pos)
    for _ in range(900):        # 15 秒
        roamer.advance(1.0 / 60.0)
        walked += abs(roamer.pos[0] - previous[0]) + abs(roamer.pos[1] - previous[1])
        previous = tuple(roamer.pos)
    assert walked > 200.0, "15 秒里只走了 {0:.1f} 像素，太少了".format(walked)
    assert tuple(roamer.pos) != start, "不应该原地不动"


def roaming_is_reproducible():
    first = Roamer((300.0, 200.0), rng=random.Random(5))
    second = Roamer((300.0, 200.0), rng=random.Random(5))
    for _ in range(300):
        first.advance(1.0 / 60.0)
        second.advance(1.0 / 60.0)
    assert first.pos == second.pos, (first.pos, second.pos)


def roaming_drag_and_release():
    roamer = Roamer((300.0, 200.0), rng=random.Random(9))
    roamer.grab()
    roamer.drag_to((9999.0, -50.0))          # 拖出场地 -> 自动夹回来
    assert roamer.pos == [300.0, 0.0], roamer.pos
    assert roamer.held and not roamer.moving

    frozen = tuple(roamer.pos)
    roamer.advance(0.5)                      # 抓在手里时不许自己乱跑
    assert tuple(roamer.pos) == frozen, "被按住时不应该自己移动"

    roamer.release()
    assert not roamer.held and roamer.moving
    for _ in range(180):
        roamer.advance(1.0 / 60.0)
    assert tuple(roamer.pos) != frozen, "松手后应该继续自己溜达"


def roaming_area_shrinks():
    roamer = Roamer((400.0, 300.0), rng=random.Random(2))
    roamer.drag_to((400.0, 300.0))
    roamer.set_limits((100.0, 50.0))         # 转屏/缩放后场地变小
    assert roamer.pos == [100.0, 50.0], roamer.pos


"""---------------- 4. 零联网 / 零后门 ----------------"""


def no_network_no_exec():
    for path in source_files():
        for number, line in enumerate(read_text(path).splitlines(), 1):
            for token in BANNED:
                assert token not in line, "{0}:{1} 出现禁止写法 {2!r}".format(
                    os.path.relpath(path, ROOT), number, token)


def no_deprecated_image_props():
    for path in source_files():
        text = read_text(path)
        for token in DEPRECATED:
            assert token not in text, "{0} 还在用 Kivy 已废弃的 {1}，请改用 fit_mode".format(
                os.path.relpath(path, ROOT), token)


def no_stray_ui_module():
    stale = os.path.join(ROOT, "app", "ui.py")
    assert not os.path.exists(stale), "旧的 app/ui.py 还在，会和 app/ui/ 包冲突"
    detail = os.path.join(ROOT, "app", "ui", "detail.py")
    assert not os.path.exists(detail), "detail.py 已被 playground.py 取代，应该删掉"


"""---------------- 5. 配置与文案 ----------------"""


def spec_consistent():
    parser = configparser.ConfigParser()
    parser.read(os.path.join(ROOT, "buildozer.spec"), encoding="utf-8")
    assert parser.has_section("app") and parser.has_section("buildozer")

    assert parser.get("app", "version") == config.APP_VERSION, "版本号不一致"
    assert parser.get("app", "package.name") == config.PACKAGE_NAME, "包名不一致"
    assert parser.get("app", "package.domain") == config.PACKAGE_DOMAIN, "域名不一致"

    requirements = parser.get("app", "requirements")
    assert "kivy" in requirements and "python3" in requirements, requirements

    # 只有悬浮桌宠需要的三个权限，多一个（相机、定位、存储…）都不行
    permissions = {item.strip() for item in
                   parser.get("app", "android.permissions").split(",") if item.strip()}
    assert permissions == EXPECTED_PERMISSIONS, permissions

    # 悬浮桌宠服务：名字、入口、前台标志，以及和 android_bridge 里的类名对上
    service_spec = parser.get("app", "services").strip()
    service_name, _sep, entry = service_spec.partition(":")
    parts = entry.split(":")
    assert parts[0] == "service.py", service_spec
    assert "foreground" in parts[1:], "悬浮桌宠应该声明成前台服务: {0}".format(service_spec)
    assert "sticky" not in parts[1:], "不要用 sticky：系统重启时拿不到图片参数"
    expected_class = "{0}.{1}.Service{2}".format(config.PACKAGE_DOMAIN, config.PACKAGE_NAME,
                                                 service_name.capitalize())
    assert android_bridge.SERVICE_CLASS == expected_class, \
        (android_bridge.SERVICE_CLASS, expected_class)
    assert os.path.isfile(os.path.join(ROOT, "service.py")), "缺少 service.py"

    exts = parser.get("app", "source.include_exts").split(",")
    for ext in ("py", "png", "ttf", "otf"):
        assert ext in exts, "include_exts 缺少 {0}".format(ext)

    icon = parser.get("app", "icon.filename")
    assert icon.endswith("assets/icon.png"), icon
    assert os.path.isfile(os.path.join(ROOT, "assets", "icon.png"))

    presplash = parser.get("app", "presplash.filename")
    assert presplash.endswith("assets/presplash.png"), presplash
    assert os.path.isfile(os.path.join(ROOT, "assets", "presplash.png")), "缺少启动图"

    excluded = parser.get("app", "source.exclude_dirs").split(",")
    for folder in ("tests", "tools"):
        assert folder in excluded, "开发目录 {0} 会被打进 APK".format(folder)


def i18n_fallback():
    # 自检环境里没有注册中文字体，所以必须回退成英文
    assert i18n.app_title() == config.APP_TITLE_EN
    assert i18n.pet_name(catalog.PETS[0]) == catalog.PETS[0].name_en
    assert i18n.change_pet_label().strip() != ""
    assert i18n.overlay_button_label().strip() != ""


"""---------------- 6. 悬浮桌宠（安卓那部分） ----------------"""


def overlay_size_is_sane():
    assert overlay.overlay_size(1080, 2400) == int(1080 * overlay.DEFAULT_SIZE_RATIO)
    # 横屏 / 方屏 / 极端小屏都不能算出个负数或者 0
    assert overlay.overlay_size(2400, 1080) == int(1080 * overlay.DEFAULT_SIZE_RATIO)
    assert overlay.overlay_size(120, 120) >= overlay.MIN_SIZE
    assert overlay.overlay_size(0, 0) == overlay.MIN_SIZE


def overlay_default_position_on_screen():
    width, height = 1080, 2400
    size = overlay.overlay_size(width, height)
    x, y = overlay.default_position(width, height, size)
    assert 0 <= x <= width - size, x
    assert 0 <= y <= height - size, y
    assert x > width / 2.0, "默认应该靠右放"


def overlay_clamp_keeps_on_screen():
    assert overlay.clamp_position(-500, -500, 1080, 2400, 300) == (0, 0)
    assert overlay.clamp_position(9999, 9999, 1080, 2400, 300) == (1080 - 300, 2400 - 300)
    # 悬浮窗比屏幕还大时，只能贴到 0
    assert overlay.clamp_position(50, 50, 200, 200, 400) == (0, 0)


def overlay_follow_matches_finger():
    # 拖动就是"按下时的位置 + 手指位移"
    assert overlay.follow_position(100, 200, 30, -50, 1080, 2400, 300) == (130, 150)
    # 拖到屏幕外会被夹住
    assert overlay.follow_position(100, 200, 5000, 0, 1080, 2400, 300) == (1080 - 300, 200)


def bridge_is_safe_on_desktop():
    """桌面上所有接口都必须是安全的空实现：应用照常能跑，只是没悬浮功能。"""
    assert android_bridge.is_android() is False
    assert android_bridge.has_overlay_permission() is False
    assert android_bridge.is_overlay_running() is False
    for result in (android_bridge.open_overlay_settings(),
                   android_bridge.start_overlay(catalog.PETS[0]),
                   android_bridge.stop_overlay(),
                   android_bridge.request_notification_permission()):
        ok, message = result
        assert ok is False, result
        assert isinstance(message, str) and message, result
    assert android_bridge.is_overlay_running() is False


def service_is_desktop_safe():
    """service.py 在电脑上被导入/执行都不该有任何动作。"""
    import service

    assert service.is_android() is False
    assert service.main() == 0, "桌面上 main() 应该直接返回"

    # 服务启动参数是应用传进来的 JSON，解析要能容错
    original = os.environ.get(service.ARGUMENT_ENV)
    try:
        os.environ[service.ARGUMENT_ENV] = json.dumps({"image": "/data/x/cat.png"})
        assert service.read_arguments()["image"] == "/data/x/cat.png"
        os.environ[service.ARGUMENT_ENV] = "not-json"
        assert service.read_arguments() == {}
        os.environ[service.ARGUMENT_ENV] = "[1, 2, 3]"
        assert service.read_arguments() == {}
        os.environ.pop(service.ARGUMENT_ENV)
        assert service.read_arguments() == {}
    finally:
        if original is None:
            os.environ.pop(service.ARGUMENT_ENV, None)
        else:
            os.environ[service.ARGUMENT_ENV] = original


def main():
    print("--- 1. 宠物名录与抠图 ---")
    check("宠物名录", pets_catalog)
    check("抠图 PNG 规格", pet_images)
    check("抠图透明通道", pet_images_transparent)
    check("身体/四肢/全身图齐全", pet_part_images)
    check("全身图有下半身", pet_full_body_content)
    check("拼装位置合法且手脚贴身", pet_layout_sane)
    check("应用图标", app_icon)
    check("字体目录", font_folder)

    print("--- 2. 界面素材 ---")
    check("界面素材存在", ui_assets_exist)
    check("界面素材内容", ui_assets_content)

    print("--- 3. 桌宠自主活动逻辑 ---")
    check("不会跑出场地", roaming_stays_in_bounds)
    check("真的会走动", roaming_moves)
    check("同种子结果一致", roaming_is_reproducible)
    check("拖走再松手会继续走", roaming_drag_and_release)
    check("场地变小会夹回", roaming_area_shrinks)

    print("--- 4. 零联网 / 零后门 ---")
    check("源码无联网/动态执行/读文件", no_network_no_exec)
    check("没用 Kivy 已废弃的 Image 属性", no_deprecated_image_props)
    check("没有遗留的旧模块", no_stray_ui_module)

    print("--- 5. 配置与文案 ---")
    check("buildozer.spec 与 config.py 一致", spec_consistent)
    check("无中文字体时回退英文", i18n_fallback)

    print("--- 6. 悬浮桌宠（安卓那部分） ---")
    check("悬浮窗尺寸计算", overlay_size_is_sane)
    check("默认位置在屏幕内", overlay_default_position_on_screen)
    check("拖动后位置夹在屏幕内", overlay_clamp_keeps_on_screen)
    check("拖动跟手", overlay_follow_matches_finger)
    check("桌面上接口都是空实现", bridge_is_safe_on_desktop)
    check("service.py 在桌面上无副作用", service_is_desktop_safe)

    if FAILURES:
        print("\nRESULT: FAILED ({0}) -> {1}".format(len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("\nRESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
