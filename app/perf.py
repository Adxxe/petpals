"""性能开关：帧率上限。

为什么要这个：Kivy 默认一直按 60 帧重画整个窗口，哪怕画面上什么都没有动
（主菜单就是完全静止的）。手机上这意味着白白烧掉一半的 GPU 和电。
所以这里做两档：

  * 静止页面（主菜单）     -> FPS_IDLE  = 30
  * 有动画/拖拽（小天地）  -> FPS_ACTIVE = 60

实现上有个关键点：Kivy 的 Clock 是在**每次 tick 时**读 `self._max_fps`
（见 kivy/clock.py 里多处 `fps = self._max_fps`），不是启动时缓存一次，
所以运行时改它当场生效。顺便写回 Config，让其它读配置的地方看到同一个值。
"""

from kivy.clock import Clock
from kivy.config import Config

FPS_ACTIVE = 60     # 有动画时
FPS_IDLE = 30       # 静止页面，省一半 GPU

_current = None


def set_fps_cap(fps):
    """把帧率上限切成 fps，返回实际生效的值。值没变就什么都不做。"""
    global _current
    fps = int(fps)
    if fps == _current:
        return _current
    try:
        Clock._max_fps = float(fps)   # Clock 每帧都读它，所以立刻生效
    except Exception:  # noqa: BLE001 - 改不动就算了，不该影响功能
        pass
    try:
        Config.set("graphics", "maxfps", str(fps))
    except Exception:  # noqa: BLE001
        pass
    _current = fps
    return _current


def current_fps_cap():
    """当前上限；还没设过就报 Kivy 配置里的值。"""
    if _current is not None:
        return _current
    try:
        return Config.getint("graphics", "maxfps")
    except Exception:  # noqa: BLE001
        return 0
