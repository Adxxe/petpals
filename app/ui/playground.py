"""宠物小天地：选中的桌宠住在这里。

它会自己到处溜达，也可以被手指按住拖走；还能把宠物"放到系统桌面"上当悬浮桌宠
（只有安卓能用，见 app/android_bridge.py）。

性能上的几个决定（"不卡"就靠这些）：
  * 定时器只在页面被显示时开着（on_enter 开、on_leave 关），回菜单就停，不空转；
  * 宠物是一只 PetView（所有部件画在同一个 canvas 里），每帧只改十几条绘图指令；
  * 背景是一张整图，不是一堆控件拼出来的；
  * 移动按 dt 计算，帧率高低只影响平滑度，不影响速度。
"""

import math

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from app import android_bridge, i18n, perf, theme
from app.fonts import ui_font_name
from app.resources import asset_path
from app.roaming import Roamer
from app.ui.pet_view import PetView
from app.ui.widgets import GlassBox, Pill, TextButton

PLAYGROUND_SCREEN = "playground"
FRAME = 1.0 / 60.0          # 60 FPS 的定时器，但移动用 dt 算，掉帧也不会变慢
HINT_RESET_SECONDS = 3.5    # 提示文字多久恢复成默认那句
WALK_RATE = 7.0             # 走路相位推进速度（越大四肢摆得越快）


class PlaygroundScreen(Screen):
    def __init__(self, on_back=None, **kwargs):
        super().__init__(name=PLAYGROUND_SCREEN, **kwargs)
        font = ui_font_name()
        self.pet = None
        self.roamer = Roamer((0.0, 0.0))
        self._clock = None
        self._hint_clock = None
        self._area = None
        self._walk_phase = 0.0
        self._grab_offset = (0.0, 0.0)
        self._art_ready = False

        root = FloatLayout()
        # 添加顺序 = 显示层级：背景 -> 影子 -> 宠物 -> 顶部按钮。
        # 背景和影子的贴图**第一次进这个页面时才加载**（见 _ensure_art）：
        # 冷启动时能少解码 2 张图、少占约 2MB 显存。
        self.background = Image(fit_mode="fill")
        root.add_widget(self.background)

        self.shadow = Image(fit_mode="fill", opacity=0.34, size_hint=(None, None))
        root.add_widget(self.shadow)

        self.pet_view = PetView(size_hint=(None, None))
        root.add_widget(self.pet_view)

        bar = GlassBox(orientation="horizontal", size_hint=(None, None),
                       width=max(dp(200), theme.PAD * 0),
                       height=theme.BAR_HEIGHT,
                       pos_hint={"center_x": 0.5, "top": 0.975},
                       padding=(dp(8), dp(8)), spacing=dp(8),
                       radius=theme.BAR_HEIGHT / 2.0)
        bar.add_widget(TextButton(i18n.change_pet_label(), on_tap=on_back, font_name=font,
                                  size_hint=(None, None), width=dp(96), height=dp(46)))
        pill = Pill(size_hint=(1, None), height=dp(46))
        self.name_label = Label(text="", font_size=theme.BTN_SIZE, color=theme.TEXT)
        if font:
            self.name_label.font_name = font
        pill.add_widget(self.name_label)
        bar.add_widget(pill)
        self.overlay_button = TextButton(i18n.overlay_button_label(),
                                         on_tap=self._toggle_overlay, font_name=font,
                                         size_hint=(None, None), width=dp(104),
                                         height=dp(46))
        bar.add_widget(self.overlay_button)
        self.bar = bar
        root.add_widget(bar)
        self.hint = Label(text=i18n.playground_hint(), font_size=theme.HINT_SIZE,
                          color=theme.TEXT_DIM, size_hint=(1, None), height=dp(24),
                          pos_hint={"x": 0, "y": 0})
        if font:
            self.hint.font_name = font
        root.add_widget(self.hint)

        self.add_widget(root)
        self.bind(size=self._on_resize)

    # --- 外部调用 -----------------------------------------------------

    def set_pet(self, pet):
        """换上一只宠物，并且把它放到场地中间。"""
        self.pet = pet
        self.pet_view.set_pet(pet)
        self.name_label.text = i18n.pet_name(pet)
        self._refresh_overlay_button()
        self._sync_area(force=True)
        self.roamer.drag_to((self.roamer.limits[0] / 2.0, self.roamer.limits[1] / 2.0))
        self._walk_phase = 0.0
        self._sync_views()

    def on_pre_enter(self):
        # 切页动画开始前：把帧率提到 60，并趁这一下把场景素材准备好（避免闪白）
        perf.set_fps_cap(perf.FPS_ACTIVE)
        self._ensure_art()

    def on_enter(self):
        self._ensure_art()
        self._sync_area(force=True)
        self._resize_bar()
        self._sync_views()
        self._refresh_overlay_button()
        if self._clock is None:
            self._clock = Clock.schedule_interval(self._step, FRAME)

    def _ensure_art(self):
        """第一次进页面才加载场景/影子贴图。"""
        if self._art_ready:
            return
        self._art_ready = True
        self.background.source = asset_path("ui", "bg_scene.png")
        self.shadow.source = asset_path("ui", "shadow.png")

    def on_leave(self):
        if self._clock is not None:
            self._clock.cancel()
            self._clock = None
        if self._hint_clock is not None:
            self._hint_clock.cancel()
            self._hint_clock = None

    # --- 悬浮桌宠 -----------------------------------------------------

    def _refresh_overlay_button(self):
        running = android_bridge.is_overlay_running()
        label = i18n.overlay_recall_label() if running else i18n.overlay_button_label()
        self.overlay_button.label.text = label

    def _toggle_overlay(self):
        """点一下把宠物放到系统桌面；再点一下召回。"""
        if not android_bridge.is_android():
            self._say(i18n.overlay_unavailable_hint())
            return

        if android_bridge.is_overlay_running():
            _ok, message = android_bridge.stop_overlay()
            self._refresh_overlay_button()
            self._say(message)
            return

        if not android_bridge.has_overlay_permission():
            android_bridge.request_notification_permission()
            android_bridge.open_overlay_settings()
            self._say(i18n.overlay_need_permission_hint())
            return

        android_bridge.request_notification_permission()
        _ok, message = android_bridge.start_overlay(self.pet)
        self._refresh_overlay_button()
        self._say(message)

    def _say(self, message):
        """底部那行字临时换成状态提示，几秒后自动恢复。"""
        self.hint.text = message
        if self._hint_clock is not None:
            self._hint_clock.cancel()
        self._hint_clock = Clock.schedule_once(self._restore_hint, HINT_RESET_SECONDS)

    def _restore_hint(self, *_args):
        self._hint_clock = None
        self.hint.text = i18n.playground_hint()

    # --- 内部：场地与画面 ---------------------------------------------

    def _on_resize(self, *_args):
        self._sync_area()
        self._resize_bar()

    def _resize_bar(self):
        """顶部那条玻璃工具栏：左右各留一点边距，看起来是"浮"在场景上的。"""
        self.bar.width = max(dp(200), self.width - theme.PAD * 2)

    def _sync_area(self, force=False):
        pet_w, pet_h = theme.PET_SIZE
        max_x = max(0.0, self.width - pet_w - theme.PET_MARGIN)
        max_y = max(0.0, self.height * theme.HORIZON - pet_h)
        area = (max_x, max_y)
        if force or area != self._area:
            self._area = area
            self.roamer.set_limits(area)

    def _step(self, dt):
        if self.pet is None:
            return
        self.roamer.advance(dt)
        if self.roamer.moving and not self.roamer.held:
            self._walk_phase += dt * WALK_RATE      # 走路的相位，驱动四肢摆动
        self._sync_views(dt)

    def _sync_views(self, dt=0.0):
        if self.pet is None:
            return
        pet_w, pet_h = theme.PET_SIZE
        x, y = self.roamer.pos

        # 走动时整只往上蹦一下（坐着的小动物就是"蹦着走"的），影子留在地上并缩小一点
        hop = 0.0
        if self.roamer.moving and not self.roamer.held:
            hop = abs(math.sin(self._walk_phase)) * theme.PET_HOP

        self.pet_view.size = (pet_w, pet_h)
        self.pet_view.pos = (x, y + theme.ROAM_BOTTOM + hop)
        # 四肢摆动 / 翅膀扇动 / 身子上下颠 / 头轻轻歪，由它自己按 dt 缓动
        self.pet_view.update(dt, self._walk_phase, self.roamer.moving, self.roamer.held)

        shrink = 1.0 - 0.22 * (hop / theme.PET_HOP if theme.PET_HOP else 0.0)
        shadow_w = pet_w * 0.62 * shrink
        shadow_h = pet_h * 0.20 * shrink
        self.shadow.size = (shadow_w, shadow_h)
        self.shadow.pos = (x + (pet_w - shadow_w) / 2.0,
                           y + theme.ROAM_BOTTOM - shadow_h * 0.35)
        self.shadow.opacity = 0.18 if self.roamer.held else 0.34

    # --- 手指拖拽 -----------------------------------------------------

    def on_touch_down(self, touch):
        if self.pet is not None and self.pet_view.collide_point(*touch.pos):
            touch.grab(self)
            self._grab_offset = (touch.pos[0] - self.roamer.pos[0],
                                 touch.pos[1] - self.roamer.pos[1])
            self.roamer.grab()
            self._sync_views()
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self.roamer.drag_to((touch.pos[0] - self._grab_offset[0],
                                 touch.pos[1] - self._grab_offset[1]))
            self._sync_views()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self.roamer.release()
            self._sync_views()
            return True
        return super().on_touch_up(touch)
