"""界面自检：需要一个真的装了 Kivy 的环境。

无头启动一次应用（窗口开好就立刻隐藏，不需要人看着），然后验证：
  * 主菜单建起来了：4 张卡片、图片纹理解码成功、布局算出非零尺寸
  * 点卡片进入"宠物小天地"，宠物图和场景图都正常
  * 桌宠会自己动、不会跑出场地、场地外点击不误触发
  * 手指拖拽：按在宠物身上能拖走，拖到哪跟到哪，松手后继续自己溜达
  * 返回键：小天地 -> 主菜单；主菜单 -> 退出应用（安卓上该有的行为）
  * 中文字体要么可用、要么已经回退英文
  * 控件数量、构建耗时（桌面数据，仅供回归参考）

用法:
    python tests/kivy_headless_check.py

没有显示器/显卡的环境可以加 PETPALS_MOCK_GL=1，只验证控件树不验证渲染。
注意：Windows 上不要设 SDL_VIDEODRIVER=dummy，会让 Kivy 直接崩溃。
"""

import math
import os
import sys
import time

# 必须在 import kivy 之前设置
os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

if os.environ.get("PETPALS_MOCK_GL") == "1":
    os.environ.setdefault("KIVY_GL_BACKEND", "mock")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import kivy  # noqa: F401
except ImportError:
    print("SKIP: 当前环境没装 Kivy。先 pip install -r requirements.txt 再跑这个自检。")
    raise SystemExit(0)

try:
    from kivy.core.window import Window  # noqa: E402
except Exception as exc:  # noqa: BLE001
    print("SKIP: 这台机器开不了窗口（{0}: {1}）。".format(type(exc).__name__, exc))
    print("      没有显示器的环境可以试 PETPALS_MOCK_GL=1。")
    raise SystemExit(0)

Window.hide()   # 只做逻辑自检，不用把窗口留在屏幕上

from kivy.clock import Clock  # noqa: E402

from app import android_bridge, catalog, fonts, i18n, theme  # noqa: E402
from app.ui.app import BACK_KEYS, ShellApp  # noqa: E402
from app.ui.menu import GRID_COLUMNS, MENU_SCREEN  # noqa: E402
from app.ui.playground import PLAYGROUND_SCREEN  # noqa: E402

FAILURES = []
STATE = {}
MAX_WIDGETS = 60          # 单个页面的控件数量上限，防止不小心把首页堆重
MAX_BUILD_MS = 3000.0     # 桌面冷启动参考值，超了说明有东西变重了
MAX_STARTUP_TEXTURE_MB = 5.0   # 冷启动允许占的纹理显存（宠物 4 张 + 菜单背景）
MAX_TOTAL_TEXTURE_MB = 7.5     # 两个页面都进过之后的总额
MB = 1024.0 * 1024.0
SCREEN_SIZE = (400, 780)  # 手机竖屏比例


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


class FakeTouch:
    """Touch 的最小替身。

    Kivy 的布局在派发触摸时会做坐标变换（push / apply_transform_2d / pop），
    所以这里把这几招也补上——本项目所有布局都是全屏不缩放的，变换是恒等变换。
    """

    def __init__(self, pos):
        self.pos = pos
        self.grab_current = None

    @property
    def x(self):
        return self.pos[0]

    @property
    def y(self):
        return self.pos[1]

    def grab(self, widget):
        self.grab_current = widget

    def ungrab(self, widget):
        if self.grab_current is widget:
            self.grab_current = None

    def push(self, *args, **kwargs):
        return self

    def pop(self, *args, **kwargs):
        return self

    def apply_transform_2d(self, transform):
        try:
            self.pos = transform(*self.pos)
        except TypeError:
            self.pos = transform(self.pos)


def widget_count(widget):
    total = 1
    for child in widget.children:
        total += widget_count(child)
    return total


def walk(widget):
    yield widget
    for child in widget.children:
        for item in walk(child):
            yield item


def texture_bytes(root):
    """界面实际占用的纹理显存（按纹理去重，共享的只算一次）。"""
    seen = {}
    for widget in walk(root):
        getter = getattr(widget, "textures", None)
        textures = getter() if callable(getter) else [getattr(widget, "texture", None)]
        for texture in textures:
            size = getattr(texture, "size", None)
            if texture is None or not size or size[0] <= 0:
                continue
            seen.setdefault(id(texture), size)
    return sum(width * height * 4 for width, height in seen.values())


def build_app_tree():
    app = ShellApp()
    started = time.perf_counter()
    root = app.build()
    STATE["build_ms"] = (time.perf_counter() - started) * 1000.0
    STATE["app"] = app
    STATE["root"] = root

    assert root.current == MENU_SCREEN, root.current
    assert sorted(screen.name for screen in root.screens) == sorted([MENU_SCREEN, PLAYGROUND_SCREEN])

    menu = root.get_screen(MENU_SCREEN)
    STATE["menu"] = menu
    assert len(menu.cards) == len(catalog.PETS) == 4, len(menu.cards)
    assert menu.grid.cols == GRID_COLUMNS
    STATE["play"] = root.get_screen(PLAYGROUND_SCREEN)
    STATE["startup_texture_mb"] = texture_bytes(root) / MB

    # 屏幕尺寸给个手机竖屏的，后面的布局和拖拽都用它
    root.size = SCREEN_SIZE
    root.do_layout()
    for screen in root.screens:
        screen.size = SCREEN_SIZE
        screen.do_layout()


def scene_art_is_lazy():
    """场景和影子的贴图不该在冷启动时就加载（省 2MB 显存和解码时间）。"""
    play = STATE["play"]
    assert play.background.texture is None, "场景贴图不该在启动时加载"
    assert play.shadow.texture is None, "影子贴图不该在启动时加载"
    assert STATE["startup_texture_mb"] <= MAX_STARTUP_TEXTURE_MB, \
        "启动纹理占用 {0:.2f} MB 超预算".format(STATE["startup_texture_mb"])
    print("     info 启动纹理占用: {0:.2f} MB（预算 {1} MB）".format(
        STATE["startup_texture_mb"], MAX_STARTUP_TEXTURE_MB))


def texture_budget():
    total = texture_bytes(STATE["root"]) / MB
    assert total <= MAX_TOTAL_TEXTURE_MB, "纹理占用 {0:.2f} MB 超预算".format(total)
    print("     info 两页合计纹理占用: {0:.2f} MB（预算 {1} MB）".format(
        total, MAX_TOTAL_TEXTURE_MB))


def fps_caps_follow_screens():
    """静止页面 30 帧、有动画 60 帧，而且真的写进了 Kivy 的 Clock。"""
    from app import perf

    menu, play = STATE["menu"], STATE["play"]
    menu.on_pre_enter()
    assert perf.current_fps_cap() == perf.FPS_IDLE, perf.current_fps_cap()
    play.on_pre_enter()
    assert perf.current_fps_cap() == perf.FPS_ACTIVE, perf.current_fps_cap()
    assert float(Clock._max_fps) == float(perf.FPS_ACTIVE), Clock._max_fps
    print("     info 帧率上限: 菜单 {0} / 小天地 {1}".format(perf.FPS_IDLE, perf.FPS_ACTIVE))


def menu_art_loaded():
    menu = STATE["menu"]
    assert menu.background.texture is not None, "菜单背景图没解码"
    for card in menu.cards:
        texture = card.picture.texture
        assert texture is not None, "{0} 的图片没解码".format(card.pet.id)
        assert texture.size[0] > 0 and texture.size[1] > 0, card.pet.id


def layout_has_size():
    menu = STATE["menu"]
    menu.do_layout()
    menu.grid.do_layout()
    sizes = [(round(card.width, 1), round(card.height, 1)) for card in menu.cards]
    assert all(w > 0 and h > 0 for w, h in sizes), sizes
    assert abs(sizes[0][0] - sizes[1][0]) < 1.0, sizes


def tap_outside_card_ignored():
    menu, root = STATE["menu"], STATE["root"]
    card = menu.cards[1]
    touch = FakeTouch((card.x - 40, card.y - 40))
    assert card.on_touch_down(touch) is False, "卡片外面的按下不应该被吃掉"
    assert root.current == MENU_SCREEN


def tap_card_enters_playground():
    root, menu, app = STATE["root"], STATE["menu"], STATE["app"]
    card = menu.cards[0]
    assert card.collide_point(*card.center), "布局后的卡片中心应该在自己身上"

    touch = FakeTouch(card.center)
    assert card.on_touch_down(touch) is True
    assert touch.grab_current is card
    assert card._pressed is True, "按下时应该进入按下状态"
    # Color.rgba 是 Kivy 的 ListProperty，只能逐项比较（直接比 tuple 恒为 False）
    assert abs(card._bg_color.rgba[3] - card._tint_down[3]) < 1e-6, card._bg_color.rgba
    assert card.on_touch_up(touch) is True
    assert card._pressed is False
    assert abs(card._bg_color.rgba[3] - card._tint[3]) < 1e-6, card._bg_color.rgba

    assert root.current == PLAYGROUND_SCREEN, root.current
    assert app.selected_pet is card.pet

    play = root.get_screen(PLAYGROUND_SCREEN)
    STATE["play"] = play
    assert play.pet is card.pet
    assert play.pet_view.parts_ready, "宠物的头 / 身子 / 四肢没有全部就位"
    assert play.name_label.text == i18n.pet_name(card.pet)


def playground_art_loaded():
    play = STATE["play"]
    play.on_pre_enter()          # 真机上切页时会触发，场景素材在这里才加载
    for name in ("background", "shadow"):
        widget = getattr(play, name)
        assert widget.texture is not None, "{0} 没解码".format(name)
        assert widget.texture.size[0] > 0, name
    assert play.pet_view.parts_ready, "宠物的头 / 身子 / 四肢没有全部就位"
    assert play.pet_view.head_texture.size[0] > 0


def pet_has_body_and_moving_limbs():
    """宠物要按物种有身子四肢，而且走动时四肢/翅膀真的在动。"""
    play = STATE["play"]
    view = play.pet_view

    # --- 四足（猫）：两条前爪交替迈步，没有像人的手臂 ---
    play.set_pet(catalog.get_pet("cat"))
    assert view.species == "quadruped", view.species
    assert view.parts_ready
    keys = set(view.pose())
    assert {"paw_left", "paw_right"} <= keys, keys
    assert not {"wing_left", "claw_left"} & keys, keys

    for _ in range(12):
        view.update(0.05, math.pi / 2, True, False)
    walking = view.pose()
    assert walking["paw_left"] > 12.0, walking
    assert walking["paw_right"] < -12.0, walking
    assert walking["bob"] > 0.01, walking

    for _ in range(20):                       # 站住不动 -> 回到原位
        view.update(0.05, 0.0, False, False)
    resting = view.pose()
    assert abs(resting["paw_left"]) < 3.0 and abs(resting["paw_right"]) < 3.0, resting

    # --- 小鸟：翅膀 + 小爪子，而且不能沿用四足的骨架 ---
    play.set_pet(catalog.get_pet("bird"))
    assert view.species == "bird", view.species
    assert view.parts_ready
    bird_keys = set(view.pose())
    assert {"wing_left", "wing_right", "claw_left", "claw_right"} <= bird_keys, bird_keys
    assert "paw_left" not in bird_keys, bird_keys

    wing_angles = []
    for phase in (0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4):
        for _ in range(6):
            view.update(0.05, phase, True, False)
        wing_angles.append(round(view.pose()["wing_left"], 2))
    assert len(set(wing_angles)) >= 3, wing_angles      # 翅膀真的在扇

    for _ in range(20):                       # 被拎起来：翅膀爪子松垂
        view.update(0.05, 0.0, False, True)
    held = view.pose()
    assert held["wing_left"] < -4.0 and held["claw_left"] < -4.0, held

    play.set_pet(catalog.get_pet("cat"))      # 复原，后面的用例按四足继续


def playground_roams():
    play = STATE["play"]
    play.set_pet(catalog.PETS[0])          # 场地尺寸已知了，重新摆到中间
    play.on_enter()
    try:
        assert play.roamer.limits[0] > 0 and play.roamer.limits[1] > 0, play.roamer.limits
        seen = set()
        for _ in range(180):               # 3 秒
            play._step(1.0 / 60.0)
            seen.add((round(play.pet_view.x), round(play.pet_view.y)))
        assert len(seen) > 5, "3 秒里宠物只出现在 {0} 个位置上".format(len(seen))

        max_x, max_y = play.roamer.limits
        x, y = play.roamer.pos
        assert 0.0 <= x <= max_x and 0.0 <= y <= max_y, (x, y)
        assert abs(play.pet_view.x - x) < 1.0, (play.pet_view.x, x)
        assert y + theme.ROAM_BOTTOM <= play.height * theme.HORIZON + 1.0, \
            "宠物不应该跑到地平线上面的天空里"
    finally:
        play.on_leave()


def playground_touch_outside_pet_ignored():
    play = STATE["play"]
    if play.pet is None:                    # 前置条件：宠物得在场上（且在场地中间）
        play.set_pet(catalog.PETS[0])
    before = tuple(play.pet_view.center)
    touch = FakeTouch((2.0, 2.0))          # 左下角：宠物活动区之外
    assert not play.on_touch_down(touch), "宠物以外的触摸不该被拦下"
    assert tuple(play.pet_view.center) == before


def playground_drag():
    play = STATE["play"]
    # 先摆到固定角落并让它停下，这样拖拽测试可复现、也不会被上下浮动干扰
    play.roamer.drag_to((0.0, 0.0))
    play.roamer.moving = False
    play._sync_views()

    start = tuple(play.pet_view.center)
    touch = FakeTouch(start)
    assert play.on_touch_down(touch) is True, "按在宠物身上应该开始拖拽"
    assert touch.grab_current is play
    assert play.roamer.held is True, "被抓住时应该停住"
    assert play.shadow.opacity < 0.3, "被抓起时影子应该变淡"

    grabbed = tuple(play.roamer.pos)
    offset = (start[0] - grabbed[0], start[1] - grabbed[1])

    # 拖到"当前位置和活动区中心的中点"：这个点一定在场地内，不会被夹住
    pet_w, pet_h = play.pet_view.size
    max_x, max_y = play.roamer.limits
    area_center = (pet_w / 2.0 + max_x / 2.0, theme.ROAM_BOTTOM + pet_h / 2.0 + max_y / 2.0)
    target = ((start[0] + area_center[0]) / 2.0, (start[1] + area_center[1]) / 2.0)

    touch.pos = target
    assert play.on_touch_move(touch) is True
    expected = (target[0] - offset[0], target[1] - offset[1])
    assert abs(play.roamer.pos[0] - expected[0]) < 0.5, (play.roamer.pos, expected)
    assert abs(play.roamer.pos[1] - expected[1]) < 0.5, (play.roamer.pos, expected)

    # 画面位置 = 逻辑位置 + 半个身子（拖拽时没有上下浮动），所以"跟手"是真的
    assert abs(play.pet_view.center_x - (play.roamer.pos[0] + pet_w / 2.0)) < 0.5
    assert abs(play.pet_view.center_y
               - (play.roamer.pos[1] + theme.ROAM_BOTTOM + pet_h / 2.0)) < 0.5

    travelled = math.hypot(play.roamer.pos[0] - grabbed[0], play.roamer.pos[1] - grabbed[1])
    assert travelled > 10.0, "拖动距离太短: {0:.1f}".format(travelled)

    assert play.on_touch_up(touch) is True
    assert play.roamer.held is False, "松手后应该继续自己溜达"
    assert touch.grab_current is None
    assert play.shadow.opacity > 0.3, "松手后影子应该恢复"

    # 松手之后确实会继续动
    frozen = tuple(play.roamer.pos)
    play.on_enter()
    try:
        for _ in range(180):
            play._step(1.0 / 60.0)
    finally:
        play.on_leave()
    assert tuple(play.roamer.pos) != frozen, "松手后宠物应该继续溜达"


def back_key_navigation():
    app, root = STATE["app"], STATE["root"]
    if root.current != PLAYGROUND_SCREEN:
        app.show_pet(catalog.PETS[0])
    assert root.current == PLAYGROUND_SCREEN
    assert app._on_keyboard(Window, BACK_KEYS[0]) is True, "小天地里应该拦住返回键"
    assert root.current == MENU_SCREEN, root.current

    # 已经在主菜单：应该退出应用，而不是毫无反应
    stopped = []
    original = app.stop
    app.stop = lambda *args, **kwargs: stopped.append(True)
    try:
        assert app._on_keyboard(Window, BACK_KEYS[0]) is True, "主菜单应该处理返回键"
    finally:
        app.stop = original
    assert stopped == [True], "主菜单按返回键应该退出应用"


def overlay_button_on_desktop():
    play = STATE["play"]
    assert play.overlay_button.label.text == i18n.overlay_button_label(), \
        play.overlay_button.label.text
    play._toggle_overlay()
    assert play.hint.text == i18n.overlay_unavailable_hint(), play.hint.text
    assert play.overlay_button.label.text == i18n.overlay_button_label(), \
        "电脑上不该变成'召回'"


def overlay_button_on_android():
    """把桥换成假的安卓，验证按钮的三段逻辑：要权限 -> 启动 -> 召回。"""
    play = STATE["play"]
    calls = []
    state = {"running": False}

    def fake_settings():
        calls.append("settings")
        return (True, "opened")

    def fake_start(pet):
        calls.append(("start", pet.id))
        state["running"] = True
        return (True, "started")

    def fake_stop():
        calls.append("stop")
        state["running"] = False
        return (True, "stopped")

    names = ("is_android", "has_overlay_permission", "open_overlay_settings",
             "start_overlay", "stop_overlay", "is_overlay_running",
             "request_notification_permission")
    saved = {name: getattr(android_bridge, name) for name in names}
    try:
        android_bridge.is_android = lambda: True
        android_bridge.has_overlay_permission = lambda: False
        android_bridge.open_overlay_settings = fake_settings
        android_bridge.start_overlay = fake_start
        android_bridge.stop_overlay = fake_stop
        android_bridge.is_overlay_running = lambda: state["running"]
        android_bridge.request_notification_permission = lambda: (True, "asked")

        # 1) 没给悬浮窗权限 -> 跳系统设置，不启动服务
        play._toggle_overlay()
        assert calls == ["settings"], calls
        assert play.hint.text == i18n.overlay_need_permission_hint(), play.hint.text
        assert play.overlay_button.label.text == i18n.overlay_button_label()

        # 2) 给了权限 -> 启动，按钮变成"召回"
        android_bridge.has_overlay_permission = lambda: True
        play._toggle_overlay()
        assert calls[-1] == ("start", play.pet.id), calls
        assert play.overlay_button.label.text == i18n.overlay_recall_label(), \
            play.overlay_button.label.text

        # 3) 再点一次 -> 召回，按钮变回"放到桌面"
        play._toggle_overlay()
        assert calls[-1] == "stop", calls
        assert play.overlay_button.label.text == i18n.overlay_button_label()
    finally:
        for name, value in saved.items():
            setattr(android_bridge, name, value)


def font_state_consistent():
    ready, source = fonts.is_cjk_ready(), fonts.font_source()
    if ready:
        assert source and os.path.isfile(source), source
    else:
        assert source is None, source
    print("     info 中文字体: {0}".format(source or "未找到 -> 界面用英文"))


def cjk_glyphs_render():
    if not fonts.is_cjk_ready():
        print("     skip 没有中文字体，跳过字形渲染检查")
        return
    from kivy.core.text import Label as CoreLabel

    for text in ("宠", "宠物伙伴"):
        core = CoreLabel(text=text, font_name=fonts.ui_font_name(), font_size=32)
        core.refresh()
        assert core.texture is not None and core.texture.size[0] > 0, text


def pages_not_too_heavy():
    menu_count = widget_count(STATE["menu"])
    play_count = widget_count(STATE["play"])
    assert menu_count <= MAX_WIDGETS, "主菜单控件太多: {0}".format(menu_count)
    assert play_count <= MAX_WIDGETS, "小天地控件太多: {0}".format(play_count)
    print("     info 控件数: 主菜单 {0} / 小天地 {1}".format(menu_count, play_count))


def step_cost_is_small():
    """每帧的推进只改两个 widget 的 pos/size，量一下 300 帧要多久。"""
    play = STATE["play"]
    play.on_enter()
    try:
        started = time.perf_counter()
        for _ in range(300):
            play._step(1.0 / 60.0)
        per_frame_ms = (time.perf_counter() - started) / 300.0 * 1000.0
    finally:
        play.on_leave()
    assert per_frame_ms < 2.0, "每帧推进耗时 {0:.3f}ms，太贵了".format(per_frame_ms)
    print("     info 每帧推进耗时: {0:.3f}ms（桌面参考值，预算 16.7ms）".format(per_frame_ms))


def startup_time_ok():
    elapsed = STATE["build_ms"]
    assert elapsed < MAX_BUILD_MS, "界面构建耗时 {0:.0f}ms".format(elapsed)
    print("     info 界面构建耗时: {0:.0f}ms（桌面参考值）".format(elapsed))


def main():
    check("构建应用与主菜单", build_app_tree)
    if FAILURES:
        print("\nRESULT: FAILED -> {0}".format(", ".join(FAILURES)))
        return 1

    check("菜单图片纹理解码", menu_art_loaded)
    check("场景素材延迟加载", scene_art_is_lazy)
    check("菜单布局尺寸非零", layout_has_size)
    check("点击卡片外不响应", tap_outside_card_ignored)
    check("点卡片进入小天地", tap_card_enters_playground)
    check("小天地的图都解码了", playground_art_loaded)
    check("宠物有身子且四肢会动", pet_has_body_and_moving_limbs)
    check("桌宠会自己活动且不越界", playground_roams)
    check("宠物以外点击不误触发", playground_touch_outside_pet_ignored)
    check("手指拖拽与松手", playground_drag)
    check("返回键行为", back_key_navigation)
    check("放到桌面按钮（电脑上）", overlay_button_on_desktop)
    check("放到桌面按钮（安卓逻辑）", overlay_button_on_android)
    check("字体状态自洽", font_state_consistent)
    check("中文字形可渲染", cjk_glyphs_render)
    check("页面控件数量", pages_not_too_heavy)
    check("纹理显存预算", texture_budget)
    check("帧率上限分页面切换", fps_caps_follow_screens)
    check("每帧推进开销", step_cost_is_small)
    check("构建耗时", startup_time_ok)

    Window.close()
    if FAILURES:
        print("\nRESULT: FAILED ({0}) -> {1}".format(len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("\nRESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.stdout.flush()
    code = main()
    sys.stdout.flush()
    raise SystemExit(code)
