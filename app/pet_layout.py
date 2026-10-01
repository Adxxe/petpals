"""宠物各部件的位置、角色与旋转支点（0~1，左下角原点，和 Kivy 一致）。

素材生成脚本和界面里的 PetView 共用这一套数字，所以"静态全身图"和"会动的那只"
永远长得一样。不同物种的骨架不一样：

  * 四足（猫 / 狗 / 兔）：坐姿 —— 屁股后腿团成底座、胸口立起来、两条前爪撑地。
    **没有像人一样站在两侧的手臂**，这是之前被吐槽的地方。
  * 小鸟：蛋形身子 + 一对翅膀 + 两只细细的小爪子（不是腿）。

每个部件 = Part(name, rect, role, side, pivot)
  rect  = (x, y, side) 左下角与边长（相对整只宠物）
  role  = body / head / paw / wing / claw
  side  = left / right / ""（决定摆动方向）
  pivot = 旋转支点（相对各自那个方框，0~1）
"""

from typing import NamedTuple


class Part(NamedTuple):
    name: str
    rect: tuple
    role: str
    side: str = ""
    pivot: tuple = (0.5, 1.0)

    @property
    def is_limb(self):
        return self.role in ("paw", "wing", "claw")


SPECIES = {"cat": "quadruped", "dog": "quadruped", "rabbit": "quadruped", "bird": "bird"}

# 坐姿四足：身子（底座 + 胸口）在下，两条前爪撑在最前面，头压在最上面
_QUADRUPED = (
    Part("body", (0.17, 0.05, 0.66), "body"),
    Part("paw_left", (0.30, 0.01, 0.19), "paw", "left"),
    Part("paw_right", (0.51, 0.01, 0.19), "paw", "right"),
    Part("head", (0.24, 0.42, 0.52), "head", "", (0.5, 0.12)),
)

# 小鸟：翅膀长在身子两侧（支点在内侧上方），小爪子在最下面
_BIRD = (
    Part("body", (0.21, 0.16, 0.58), "body"),
    Part("wing_left", (0.08, 0.32, 0.30), "wing", "left", (0.82, 0.80)),
    Part("wing_right", (0.62, 0.32, 0.30), "wing", "right", (0.18, 0.80)),
    Part("claw_left", (0.33, 0.10, 0.20), "claw", "left"),
    Part("claw_right", (0.52, 0.10, 0.20), "claw", "right"),
    Part("head", (0.27, 0.46, 0.46), "head", "", (0.5, 0.12)),
)

LAYOUTS = {"quadruped": _QUADRUPED, "bird": _BIRD}


def layout_for(species):
    return LAYOUTS.get(species, _QUADRUPED)


def species_of(pet_id):
    return SPECIES.get(pet_id, "quadruped")


def to_top_down(rect):
    """换成 PIL 需要的大头朝下坐标（返回 x, top, side）。"""
    x, y, side = rect
    return (x, 1.0 - y - side, side)
