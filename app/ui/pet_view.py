"""小天地里那只会动的宠物。

按**物种骨架**拼装（见 app/pet_layout.py）：
  * 四足（猫 / 狗 / 兔）：身子（坐姿）+ 两条前爪 + 头；
  * 小鸟：蛋形身子 + 一对翅膀 + 两只小爪子 + 头。

所有部件画在**同一个 canvas** 里（不是一堆 widget），所以：
  * 不增加控件数量，布局开销为零；
  * 每帧只改十几条绘图指令的属性，开销固定且很小；
  * 前爪/小爪子交替迈步、翅膀扇动、头轻轻歪，都是绕各自"根部"旋转。
"""

import math

from kivy.core.image import Image as CoreImage
from kivy.graphics import PopMatrix, PushMatrix, Rectangle, Rotate
from kivy.uix.widget import Widget

from app import pet_layout

EASE_RATE = 12.0          # 姿态变化时的缓动速度（越小越"软"）
PAW_SWING = 18.0          # 四足迈步的摆幅（度）
CLAW_SWING = 13.0         # 小鸟小爪子的摆幅
WING_SWING = 26.0         # 小鸟扇翅膀的摆幅
IDLE_PAW = 2.0            # 站着不动时的轻微晃动
IDLE_WING = 4.0
HOLD_ANGLE = -9.0         # 被拎起来时四肢松垂


class PetView(Widget):
    """有身子、四肢/翅膀会动的宠物。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._species = None
        self._layout = ()
        self._textures = {}
        self._rect = {}
        self._rotate = {}
        self._angles = {}
        self._bob = 0.0
        self._idle_time = 0.0
        self.bind(pos=self._apply, size=self._apply)

    # --- 组装 ---------------------------------------------------------

    def _build_canvas(self):
        """按物种骨架重建绘图指令（换物种时要重建）。"""
        self.canvas.clear()
        self._rect = {}
        self._rotate = {}
        self._angles = {}

        with self.canvas:
            for part in self._layout:
                if part.role == "body":
                    self._rect[part.name] = Rectangle()
                    continue
                PushMatrix()
                self._rotate[part.name] = Rotate(angle=0.0, origin=(0.0, 0.0))
                self._rect[part.name] = Rectangle()
                PopMatrix()
                self._angles[part.name] = 0.0

    def set_pet(self, pet):
        """换上另一只宠物（物种不同就重建骨架；旧纹理交给 Kivy 缓存回收）。"""
        species = pet.species()
        if species != self._species or not self._rect:
            self._species = species
            self._layout = pet_layout.layout_for(species)
            self._build_canvas()

        self._textures = {
            "head": _texture(pet.image_path()),
            "body": _texture(pet.body_path()),
        }
        for part in self._layout:
            if part.is_limb and part.role not in self._textures:
                self._textures[part.role] = _texture(pet.limb_path(part.role))

        for part in self._layout:
            self._rect[part.name].texture = self._textures.get(part.role)
        self._apply()

    # --- 姿态 ---------------------------------------------------------

    def update(self, dt, walk_phase, moving, held):
        """每帧调用：walk_phase 是走路相位（只有走动时才会推进）。"""
        step = math.sin(walk_phase)
        flapping = math.sin(walk_phase * 2.0)

        if held:
            targets = {name: HOLD_ANGLE for name in self._angles}
            target_bob, target_tilt = -0.010, 0.0
        elif moving:
            targets = {}
            for part in self._layout:
                if not part.is_limb:
                    continue
                sign = 1.0 if part.side == "left" else -1.0
                if part.role == "wing":
                    targets[part.name] = flapping * WING_SWING * sign
                elif part.role == "claw":
                    targets[part.name] = step * CLAW_SWING * sign
                else:
                    targets[part.name] = step * PAW_SWING * sign
            target_bob, target_tilt = abs(step) * 0.02, step * 2.5
        else:
            idle = math.sin(self._idle_time * 1.8)
            targets = {}
            for part in self._layout:
                if not part.is_limb:
                    continue
                if part.role == "wing":
                    targets[part.name] = idle * IDLE_WING * (1.0 if part.side == "left" else -1.0)
                elif part.role == "paw":
                    targets[part.name] = idle * IDLE_PAW
                else:
                    targets[part.name] = 0.0
            target_bob, target_tilt = idle * 0.004, idle * 1.2

        self._idle_time += dt
        ease = min(1.0, max(0.0, dt) * EASE_RATE)
        for name, value in targets.items():
            if name in self._angles:
                self._angles[name] += (value - self._angles[name]) * ease
        self._angles["head"] = self._angles.get("head", 0.0) + (
            target_tilt - self._angles.get("head", 0.0)) * ease
        self._bob += (target_bob - self._bob) * ease
        self._apply()

    def pose(self):
        """当前姿态（测试用）。"""
        return dict(self._angles, bob=self._bob)

    @property
    def species(self):
        return self._species

    @property
    def parts_ready(self):
        """头/身子/四肢都拿到纹理了才算就位（空视图不算）。"""
        return bool(self._textures) and all(
            texture is not None for texture in self._textures.values())

    def textures(self):
        """本视图用到的纹理（性能体检 / 显存预算统计用）。"""
        return [texture for texture in self._textures.values() if texture is not None]

    @property
    def head_texture(self):
        return self._textures.get("head")

    # --- 画出来 -------------------------------------------------------

    def _apply(self, *_args):
        side_box = min(self.width, self.height)
        if side_box <= 0 or not self._layout:
            return
        origin_x = self.x + (self.width - side_box) / 2.0
        origin_y = self.y + (self.height - side_box) / 2.0
        lift = self._bob * side_box

        for part in self._layout:
            rect_x, rect_y, rect_side = part.rect
            side = rect_side * side_box
            pos_x = origin_x + rect_x * side_box
            pos_y = origin_y + rect_y * side_box
            if part.role != "body":
                pos_y += lift            # 身子以外跟着颠一下

            self._rect[part.name].pos = (pos_x, pos_y)
            self._rect[part.name].size = (side, side)

            rotate = self._rotate.get(part.name)
            if rotate is not None:
                rotate.origin = (pos_x + part.pivot[0] * side,
                                 pos_y + part.pivot[1] * side)
                rotate.angle = self._angles.get(part.name, 0.0)


def _texture(path):
    """取一张图的纹理。同一个文件只会解码一次（Kivy 内部有缓存）。"""
    return CoreImage(path).texture
