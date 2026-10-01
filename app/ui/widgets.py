"""可复用的基础组件：玻璃面板、点击容器、宠物卡片、文字按钮。

外观统一走 GlassBox：投影 -> 半透明底 -> 顶部高光 -> 1px 亮边。
全部是自绘的绘图指令，不加载任何贴图，所以不占纹理显存。
"""

from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from app import theme
from app.resources import asset_path


def shadow_texture():
    """脚下那片软阴影的纹理（同一个文件只解码一次）。"""
    return CoreImage(asset_path("ui", "shadow.png")).texture


class GlassBox(BoxLayout):
    """玻璃面板的外观。不做真正的背景模糊，理由见 app/theme.py 的注释。"""

    def __init__(self, tint=theme.GLASS_TINT, tint_down=None, radius=theme.RADIUS,
                 shadow=True, sheen=True, edge=True, **kwargs):
        self._radius = radius
        self._tint = tint
        self._tint_down = tint if tint_down is None else tint_down
        super().__init__(**kwargs)

        # 画在内容下面，顺序就是层次：投影在最底，亮边在最上
        with self.canvas.before:
            self._shadow_color = Color(*theme.GLASS_SHADOW) if shadow else None
            self._shadow_rect = theme.rounded_rect(radius) if shadow else None
            self._bg_color = Color(*tint)
            self._bg_rect = theme.rounded_rect(radius)
            self._sheen_color = Color(*theme.GLASS_SHEEN) if sheen else None
            self._sheen_rect = theme.rounded_rect(radius) if sheen else None
            self._edge_color = Color(*theme.GLASS_EDGE) if edge else None
            self._edge_line = theme.rounded_outline(radius) if edge else None

        self.bind(pos=self._sync_glass, size=self._sync_glass)

    def _sync_glass(self, *_args):
        x, y = self.pos
        width, height = self.size
        offset_x, offset_y = theme.SHADOW_OFFSET
        radius = self._radius

        if self._shadow_rect is not None:
            self._shadow_rect.pos = (x + offset_x, y + offset_y)
            self._shadow_rect.size = (max(0.0, width - offset_x * 2.0), max(0.0, height))

        self._bg_rect.pos = (x, y)
        self._bg_rect.size = (width, height)

        if self._sheen_rect is not None:
            sheen_height = height * 0.52
            self._sheen_rect.pos = (x, y + height - sheen_height)
            self._sheen_rect.size = (width, sheen_height)
            if hasattr(self._sheen_rect, "radius"):     # 上半部分：上圆下略方
                self._sheen_rect.radius = [radius, radius, radius * 0.3, radius * 0.3]

        if self._edge_line is not None:
            self._edge_line.rounded_rectangle = (x, y, width, height, radius)

    def set_background(self, rgba):
        self._bg_color.rgba = rgba


class TapBox(GlassBox):
    """带按下反馈的点击容器。

    on_tap：手指在组件内按下并抬起时调用；传 None 就是纯展示。
    """

    def __init__(self, on_tap=None, tint=theme.GLASS_TINT, tint_down=theme.GLASS_TINT_DOWN,
                 **kwargs):
        self._on_tap = on_tap
        self._pressed = False
        super().__init__(tint=tint, tint_down=tint_down, **kwargs)

    def _set_pressed(self, pressed):
        self._pressed = pressed
        self.set_background(self._tint_down if pressed else self._tint)

    def on_touch_down(self, touch):
        if self.disabled or not self.collide_point(*touch.pos):
            return False
        touch.grab(self)
        self._set_pressed(True)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        tapped = self._pressed and self.collide_point(*touch.pos)
        self._set_pressed(False)
        if tapped and self._on_tap is not None:
            self._on_tap()
        return True


class PetCard(TapBox):
    """菜单里的一张宠物卡片。

    特意**没有白色底板**：宠物直接站在背景上，脚下垫一层软阴影，
    按下时才浮出一层很淡的高光当反馈。
    """

    def __init__(self, pet, display_name, on_select=None, font_name=None, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", (dp(8), dp(8), dp(8), dp(10)))
        kwargs.setdefault("spacing", dp(2))
        super().__init__(
            on_tap=(lambda: on_select(pet)) if on_select else None,
            tint=(1, 1, 1, 0.0),            # 平时完全透明，不给宠物垫白底
            tint_down=(1, 1, 1, 0.16),      # 按下才有一层淡高光
            radius=theme.RADIUS,
            shadow=False, sheen=False, edge=False,
            **kwargs
        )
        self.pet = pet

        # 脚下的软阴影：直接画在卡片自己的 canvas 上（在宠物图片下面），
        # 不额外套一层布局 —— 套布局会让图片拿不到尺寸、全叠到原点去。
        with self.canvas.before:
            self._shadow_color = Color(1, 1, 1, 0.20)
            self._shadow_rect = Rectangle(texture=shadow_texture(), size=(0, 0))

        self.picture = Image(source=pet.full_path(), fit_mode="contain")
        self.add_widget(self.picture)

        self.name_label = Label(text=display_name, font_size=theme.CARD_NAME_SIZE,
                                color=theme.TEXT, size_hint_y=None, height=dp(26))
        if font_name:
            self.name_label.font_name = font_name
        self.add_widget(self.name_label)

        self.picture.bind(pos=self._sync_shadow, size=self._sync_shadow)

    def _sync_shadow(self, *_args):
        """脚下那片阴影：贴着宠物最低处，宽约身子的 6 成。"""
        width = self.picture.width * 0.60
        height = self.picture.height * 0.09
        self._shadow_rect.size = (width, height)
        self._shadow_rect.pos = (self.picture.center_x - width / 2.0,
                                 self.picture.y + self.picture.height * 0.035)


class TextButton(TapBox):
    """整行宽的普通按钮（也可以指定宽度当小按钮用）。"""

    def __init__(self, text, on_tap=None, font_name=None, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", dp(46))
        super().__init__(on_tap=on_tap, tint=theme.BTN_TINT, tint_down=theme.BTN_TINT_DOWN,
                         radius=theme.RADIUS_SMALL, shadow=False, **kwargs)

        self.label = Label(text=text, font_size=theme.BTN_SIZE, color=theme.TEXT_ON_GLASS)
        if font_name:
            self.label.font_name = font_name
        self.add_widget(self.label)


class Pill(GlassBox):
    """只是个玻璃药丸（不可点），用来放宠物名字这种内容。"""

    def __init__(self, tint=(1, 1, 1, 0.34), radius=theme.RADIUS_SMALL, **kwargs):
        super().__init__(tint=tint, radius=radius, shadow=False, **kwargs)
