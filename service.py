"""安卓悬浮桌宠服务 —— 让宠物盖在其他 App 上面，可以拖着走。

**这个文件只在打包成 APK 之后、由 python-for-android 作为后台服务运行。**
在电脑上导入或运行它不会有任何动作（见文件末尾的 is_android() 判断）。
它不参与应用界面，桌面上的开发/自测也不会碰它。

它做的事：
  1. 用 WindowManager 加一个 TYPE_APPLICATION_OVERLAY 的 ImageView（就是宠物图）；
  2. 按住可以拖动（OnTouchListener -> updateViewLayout），边界由 app/overlay.py 算；
  3. 前台服务的通知由 p4a 负责（buildozer.spec 里服务名后面带 :foreground，
     PythonService.doStartForeground 会建通知渠道并调 startForeground），这里不用管；
  4. 出错只写 logcat（TAG = PetPalsOverlay），不写文件、不联网。

打包配置在 buildozer.spec：
    android.permissions = SYSTEM_ALERT_WINDOW, FOREGROUND_SERVICE, POST_NOTIFICATIONS
    services = Petservice:service.py:foreground
应用里通过 app/android_bridge.py 启动它（调 p4a 生成的 ServicePetservice.start）。
"""

import json
import os
import sys
import time

LOG_TAG = "PetPalsOverlay"
ARGUMENT_ENV = "PYTHON_SERVICE_ARGUMENT"

# 这些引用必须留着：被 Python 回收掉，Java 那边的悬浮窗就没数据了
_KEEP_ALIVE = {}


def _ensure_app_path():
    """让 "import app.overlay" 在服务进程里也能用。"""
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (here, os.environ.get("ANDROID_PRIVATE") or ""):
        if path and path not in sys.path:
            sys.path.insert(0, path)


def is_android():
    """纯 Python 判断，不 import kivy（服务进程里不需要图形栈）。"""
    if os.environ.get("ANDROID_ARGUMENT") or os.environ.get("ANDROID_PRIVATE"):
        return True
    try:
        import jnius  # noqa: F401
    except Exception:
        return False
    return True


def log(message):
    """写到 logcat：adb logcat -s PetPalsOverlay"""
    try:
        from jnius import autoclass
        autoclass("android.util.Log").i(LOG_TAG, str(message))
    except Exception:
        print("[{0}] {1}".format(LOG_TAG, message))


def read_arguments():
    """应用启动服务时通过 PYTHON_SERVICE_ARGUMENT 传进来的 JSON。"""
    raw = os.environ.get(ARGUMENT_ENV) or ""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def build_touch_listener(window_manager, view, params, screen_width, screen_height, size):
    """返回一个 Java 的 OnTouchListener，实现"按住拖动"。"""
    from jnius import PythonJavaClass, autoclass, java_method
    from app.overlay import follow_position

    MotionEvent = autoclass("android.view.MotionEvent")

    class TouchListener(PythonJavaClass):
        __javainterfaces__ = ["android/view/View$OnTouchListener"]
        __javacontext__ = "app"

        def __init__(self):
            super().__init__()
            self._down_x = 0.0
            self._down_y = 0.0
            self._origin_x = 0
            self._origin_y = 0
            self._moved = False

        @java_method("(Landroid/view/View;Landroid/view/MotionEvent;)Z")
        def onTouch(self, _view, event):
            action = int(event.getAction())
            if action == int(MotionEvent.ACTION_DOWN):
                self._down_x = float(event.getRawX())
                self._down_y = float(event.getRawY())
                self._origin_x = int(params.x)
                self._origin_y = int(params.y)
                self._moved = False
                return True
            if action == int(MotionEvent.ACTION_MOVE):
                delta_x = int(float(event.getRawX()) - self._down_x)
                delta_y = int(float(event.getRawY()) - self._down_y)
                if abs(delta_x) > 4 or abs(delta_y) > 4:
                    self._moved = True
                params.x, params.y = follow_position(
                    self._origin_x, self._origin_y, delta_x, delta_y,
                    screen_width, screen_height, size)
                window_manager.updateViewLayout(view, params)
                return True
            if action == int(MotionEvent.ACTION_UP):
                if not self._moved:
                    log("宠被点了一下（位置 {0}, {1}）".format(int(params.x), int(params.y)))
                return True
            return False

    return TouchListener()


def main():
    if not is_android():
        print("[{0}] 这个脚本只在安卓上作为后台服务运行，当前环境直接返回。".format(LOG_TAG))
        return 0

    _ensure_app_path()
    from jnius import autoclass, cast

    from app.overlay import default_position, overlay_size

    PythonService = autoclass("org.kivy.android.PythonService")
    Context = autoclass("android.content.Context")
    LayoutParams = autoclass("android.view.WindowManager$LayoutParams")
    Gravity = autoclass("android.view.Gravity")
    PixelFormat = autoclass("android.graphics.PixelFormat")
    BuildVersion = autoclass("android.os.Build$VERSION")
    BitmapFactory = autoclass("android.graphics.BitmapFactory")
    ImageView = autoclass("android.widget.ImageView")
    DisplayMetrics = autoclass("android.util.DisplayMetrics")

    service = PythonService.mService
    if service is None:
        log("拿不到 Service 实例，退出")
        return 1

    arguments = read_arguments()
    image_path = arguments.get("image") or ""
    if not image_path or not os.path.isfile(image_path):
        log("找不到宠物图片: {0!r}".format(image_path))
        return 1

    bitmap = BitmapFactory.decodeFile(image_path)
    if bitmap is None:
        log("宠物图解码失败: {0}".format(image_path))
        return 1

    # 前台服务的通知由 p4a 处理（buildozer.spec 里服务名带了 :foreground），这里不重复调 startForeground
    window_manager = cast("android.view.WindowManager",
                          service.getSystemService(Context.WINDOW_SERVICE))
    metrics = DisplayMetrics()
    window_manager.getDefaultDisplay().getMetrics(metrics)
    screen_width = int(metrics.widthPixels)
    screen_height = int(metrics.heightPixels)
    size = overlay_size(screen_width, screen_height)
    x, y = default_position(screen_width, screen_height, size)

    # Android 8.0(API 26) 起必须用 TYPE_APPLICATION_OVERLAY，再老用 TYPE_PHONE
    layout_type = (LayoutParams.TYPE_APPLICATION_OVERLAY
                   if int(BuildVersion.SDK_INT) >= 26 else LayoutParams.TYPE_PHONE)
    params = LayoutParams(size, size, layout_type,
                          LayoutParams.FLAG_NOT_FOCUSABLE
                          | LayoutParams.FLAG_NOT_TOUCH_MODAL
                          | LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                          PixelFormat.TRANSLUCENT)
    params.gravity = Gravity.TOP | Gravity.LEFT
    params.x = x
    params.y = y

    view = ImageView(service)
    view.setImageBitmap(bitmap)
    listener = build_touch_listener(window_manager, view, params,
                                    screen_width, screen_height, size)
    view.setOnTouchListener(listener)

    try:
        window_manager.addView(view, params)
    except Exception as exc:  # noqa: BLE001
        log("加悬浮窗失败（多半是没给「显示在其他应用上层」权限）: {0}".format(exc))
        return 1

    _KEEP_ALIVE.update({"view": view, "listener": listener,
                        "params": params, "bitmap": bitmap})
    log("桌宠已上桌面: {0}x{0}px @ ({1}, {2})，屏幕 {3}x{4}".format(
        size, x, y, screen_width, screen_height))

    # 服务进程不能退出，否则悬浮窗会被回收
    while True:
        time.sleep(1.0)


# p4a 的服务进程会执行本文件；桌面上（开发机）什么都不做。
if is_android():
    main()
