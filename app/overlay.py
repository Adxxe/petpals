"""悬浮桌宠的几何计算。

纯 Python：不 import kivy，也不 import jnius，所以既能在安卓服务里用，
也能在电脑上直接跑测试（见 tests/smoke_test.py 的"悬浮窗几何"一节）。
"""

DEFAULT_SIZE_RATIO = 0.28      # 悬浮窗边长 = 屏幕短边 × 这个比例
MARGIN_RATIO = 0.12            # 默认位置离屏幕边缘的空隙（相对悬浮窗边长）
DEFAULT_HEIGHT_RATIO = 0.62    # 默认位置的纵向位置（屏幕高度的比例）
MIN_SIZE = 48                  # 再小就按不中了


def overlay_size(screen_width, screen_height, ratio=DEFAULT_SIZE_RATIO):
    """悬浮窗边长（像素）。太小不好按，太大挡别的应用。"""
    short_side = min(int(screen_width), int(screen_height))
    return max(MIN_SIZE, int(short_side * ratio))


def clamp_position(x, y, screen_width, screen_height, size):
    """把悬浮窗夹在屏幕内，免得拖出屏幕之后找不回来。"""
    max_x = max(0, int(screen_width) - int(size))
    max_y = max(0, int(screen_height) - int(size))
    return (min(max(0, int(x)), max_x), min(max(0, int(y)), max_y))


def default_position(screen_width, screen_height, size, height_ratio=DEFAULT_HEIGHT_RATIO):
    """默认位置：右侧靠下，像只小宠物蹲在屏幕边上。"""
    margin = max(1, int(size * MARGIN_RATIO))
    x = int(screen_width) - int(size) - margin
    y = int(int(screen_height) * height_ratio)
    return clamp_position(x, y, screen_width, screen_height, size)


def follow_position(start_x, start_y, delta_x, delta_y,
                    screen_width, screen_height, size):
    """拖动后的新位置 = 按下时的位置 + 手指位移，再夹回屏幕内。"""
    return clamp_position(int(start_x) + int(delta_x), int(start_y) + int(delta_y),
                          screen_width, screen_height, size)
