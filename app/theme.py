"""界面尺寸与配色。

想换风格只改这个文件。
单位用 dp()：手机会按屏幕密度自动换算，不同机型看起来一样大。
"""

from kivy.graphics import Line, Rectangle
from kivy.metrics import dp

from app.config import SCENE_HORIZON

try:  # 圆角矩形是 Kivy 2.1+ 才有的，低版本自动退回直角，不会崩
    from kivy.graphics import RoundedRectangle
except ImportError:  # pragma: no cover
    RoundedRectangle = None

# --- 玻璃拟态配色（浅色主题 + 半透明面板）------------------------------
# 说明：这里做的是"看起来像玻璃"，不是真正的背景模糊 ——
# Kivy 里要做真模糊得用 stencil 或自定义 shader，而我们的背景是柔和渐变/低对比场景，
# 模糊前后肉眼几乎没差别，不值得为它承担驱动兼容风险（详见 README）。
TEXT = (0.20, 0.16, 0.14, 1)            # 深可可色，浅背景上清楚
TEXT_DIM = (0.42, 0.37, 0.35, 1)
TEXT_ON_GLASS = (0.16, 0.13, 0.12, 1)

GLASS_TINT = (1, 1, 1, 0.55)            # 玻璃主体（半透明白）
GLASS_TINT_DOWN = (1, 1, 1, 0.74)       # 按下时更亮
GLASS_SHEEN = (1, 1, 1, 0.30)           # 顶部高光，玻璃的关键
GLASS_EDGE = (1, 1, 1, 0.85)            # 1px 亮边
GLASS_SHADOW = (0.28, 0.32, 0.46, 0.22)
GLASS_BLUR = (1, 1, 1, 0.10)            # 面板内侧的一层薄雾

BTN_TINT = (1, 1, 1, 0.42)
BTN_TINT_DOWN = (1, 1, 1, 0.66)

# 兼容旧名字（卡片/按钮默认就是玻璃）
CARD_BG = GLASS_TINT
CARD_BG_DOWN = GLASS_TINT_DOWN
CARD_SHADOW = GLASS_SHADOW
BTN_BG = BTN_TINT
BTN_BG_DOWN = BTN_TINT_DOWN

# --- 尺寸 -------------------------------------------------------------
PAD = dp(16)
GAP = dp(14)
RADIUS = dp(24)
RADIUS_SMALL = dp(14)
SHADOW_OFFSET = (dp(2), -dp(7))         # 投影往下方偏一点，玻璃才会有"厚度"
GLOW_ALPHA = 0.20                       # 宠物身后的柔光圆

TITLE_SIZE = dp(30)
SUBTITLE_SIZE = dp(14)
CARD_NAME_SIZE = dp(17)
BTN_SIZE = dp(15)
HINT_SIZE = dp(13)

# 小天地里的宠物和活动区域（带身子之后要高一点）
PET_SIZE = (dp(132), dp(152))
PET_HOP = dp(9)                         # 走动时整只往上蹦的高度
PET_MARGIN = dp(10)
ROAM_BOTTOM = dp(34)                    # 活动区底部留白，别踩到提示文字上
HORIZON = SCENE_HORIZON
BAR_HEIGHT = dp(62)                     # 小天地顶部那条浮动玻璃工具栏


def rounded_rect(radius):
    """返回一个背景绘制指令：能用圆角就用圆角，否则退回直角矩形。

    radius 可以是单个数字，也可以是 4 个数字（左上 / 右上 / 右下 / 左下）。
    """
    if isinstance(radius, (list, tuple)):
        values = list(radius)
    else:
        values = [radius] * 4
    if RoundedRectangle is not None:
        try:
            return RoundedRectangle(radius=values)
        except TypeError:
            pass
    return Rectangle()


def rounded_outline(radius):
    """1px 圆角描边：玻璃那圈"亮边"。低版本 Kivy 没有就返回 None。"""
    try:
        return Line(width=1.0, rounded_rectangle=(0, 0, 0, 0, radius))
    except Exception:  # noqa: BLE001
        return None


def tint(color, alpha):
    """取一个颜色的 RGB，换成指定透明度，用来做底部色块。"""
    return (color[0], color[1], color[2], alpha)
