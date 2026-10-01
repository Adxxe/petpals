"""桌宠的自主活动逻辑。

刻意写成纯 Python（不 import kivy），这样不用开窗口就能直接跑测试
（见 tests/smoke_test.py 的"自主活动逻辑"一节）。

Roamer 只知道三件事：能走到哪（limits）、朝哪走、走多快。
每隔一会儿随机换个方向，走累了停一下；被手指按住时它自己不动。
"""

import math
import random

SPEED = 74.0                       # 像素/秒，外面会按屏幕密度换算
WALK_MIN, WALK_MAX = 0.9, 2.4      # 保持同一个方向的时长（秒）
PAUSE_MIN, PAUSE_MAX = 0.5, 1.8    # 停下来歇一会儿的时长（秒）
PAUSE_CHANCE = 0.45                # 一个方向走完后停下来歇歇的概率
TURN_MIN, TURN_MAX = 0.6, 1.0      # 水平速度分量范围，越大越"横着走"
RISE = 0.7                         # 垂直速度分量范围


class Roamer:
    """在一块矩形场地里自己溜达的小家伙。

    limits = (max_x, max_y)：左上角坐标允许的最大值（单位像素），
    活动范围就是 [0, max_x] × [0, max_y]。
    """

    def __init__(self, limits, speed=SPEED, rng=None):
        self._rng = rng if rng is not None else random.Random()
        self.limits = [0.0, 0.0]
        self.speed = float(speed)
        self.pos = [0.0, 0.0]
        self.facing = 1
        self.moving = True
        self.held = False
        self._dir = (1.0, 0.0)
        self._time_left = 0.0
        self.set_limits(limits)
        self.pos = [self.limits[0] / 2.0, self.limits[1] / 2.0]
        self._plan()

    # --- 外部操作 -----------------------------------------------------

    def set_limits(self, limits):
        """场地大小变了（转屏、窗口缩放），把位置夹回新场地里。"""
        self.limits = [max(0.0, float(limits[0])), max(0.0, float(limits[1]))]
        self._clamp()

    def grab(self):
        """被手指按住：停下，别跟手指抢位置。"""
        self.held = True
        self.moving = False

    def drag_to(self, pos):
        """被拖到某个位置（会自动夹在场地内）。"""
        self.pos = [float(pos[0]), float(pos[1])]
        self._clamp()

    def release(self):
        """松手：重新挑个方向，接着溜达。"""
        self.held = False
        self._plan()

    # --- 每帧推进 -----------------------------------------------------

    def advance(self, dt):
        """往前走 dt 秒；dt 是真实帧间隔，所以快慢跟帧率无关。"""
        if self.held or dt <= 0:
            return

        self._time_left -= dt
        if self._time_left <= 0:
            self._plan()
        if not self.moving:
            return

        max_x, max_y = self.limits
        x = self.pos[0] + self._dir[0] * self.speed * dt
        y = self.pos[1] + self._dir[1] * self.speed * dt
        dx, dy = self._dir

        # 撞墙就掉头（把位置夹回场地，避免卡在墙上抖动）
        if x < 0.0 or x > max_x:
            dx = -dx
            x = min(max(x, 0.0), max_x)
            self.facing = 1 if dx > 0 else -1
        if y < 0.0 or y > max_y:
            dy = -dy
            y = min(max(y, 0.0), max_y)

        self._dir = (dx, dy)
        self.pos = [x, y]

    # --- 内部 ---------------------------------------------------------

    def _plan(self):
        """决定接下来是走还是歇。"""
        if self.moving and self._rng.random() < PAUSE_CHANCE:
            self.moving = False
            self._time_left = self._rng.uniform(PAUSE_MIN, PAUSE_MAX)
            return

        self.moving = True
        self._time_left = self._rng.uniform(WALK_MIN, WALK_MAX)

        sign = -1.0 if self._rng.random() < 0.5 else 1.0
        dx = sign * self._rng.uniform(TURN_MIN, TURN_MAX)
        dy = self._rng.uniform(-RISE, RISE)
        length = math.hypot(dx, dy) or 1.0
        self._dir = (dx / length, dy / length)
        self.facing = 1 if dx > 0 else -1

    def _clamp(self):
        self.pos[0] = min(max(self.pos[0], 0.0), self.limits[0])
        self.pos[1] = min(max(self.pos[1], 0.0), self.limits[1])
