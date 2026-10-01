"""安卓能力桥：悬浮窗权限 + 启停悬浮桌宠服务。

设计原则：桌面上（开发机）所有函数都是安全的空实现，返回 (是否成功, 提示语)，
所以应用在电脑上照样能跑，只是"放到桌面"这个按钮会告诉你只在手机上可用。

注意：`SYSTEM_ALERT_WINDOW`（显示在其他应用上层）是**特殊权限**，
不能在应用内弹窗申请，只能跳到系统设置页让用户手动开——这是安卓的设计。
"""

import json
import os


def _detect_platform():
    """优先问 Kivy；问不到（比如没装 Kivy 的自检环境）就看安卓环境变量。

    这样 android_bridge 在没装 Kivy 的机器上也能安全导入，
    tests/smoke_test.py 才能验证"桌面上全是空实现"这条契约。
    """
    try:
        from kivy.utils import platform as kivy_platform
        return kivy_platform
    except Exception:  # noqa: BLE001
        if os.environ.get("ANDROID_ARGUMENT") or os.environ.get("ANDROID_PRIVATE"):
            return "android"
        return "unknown"


# 对应 buildozer.spec 里的 android.services = petservice:service.py
# p4a 生成的 Java 服务类是 "Service" + 服务名（首字母大写），即 ServicePetservice。
# 出处：python-for-android 文档 Services 一节（"with the first letter upper case"）。
# tests/smoke_test.py 会拿 buildozer.spec 反推这个名字并比对，防止写错。
SERVICE_CLASS = "com.example.petpals.ServicePetservice"
NOTIFICATION_PERMISSION = "android.permission.POST_NOTIFICATIONS"

_android = _detect_platform() == "android"
_service_started = False

# 前台服务那条常驻通知的文案。这条通知是安卓系统画的（不是 Kivy 画的），
# 用的是系统字体，所以中文一定显示得出来。
NOTIFICATION_TITLE = "PetPals"
NOTIFICATION_TEXT = "桌宠正在桌面上活动"


def is_android():
    return _android


def is_overlay_running():
    """上一次是不是我们启动的（进程内记着，不做持久化）。"""
    return _service_started


def has_overlay_permission():
    if not _android:
        return False
    try:
        from jnius import autoclass
        Settings = autoclass("android.provider.Settings")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        return bool(Settings.canDrawOverlays(PythonActivity.mActivity))
    except Exception:
        return False


def open_overlay_settings():
    """跳到系统设置的"显示在其他应用上层"页面。"""
    if not _android:
        return (False, "悬浮桌宠只在安卓手机上可用，电脑上请用应用内的小天地")
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")
        intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:" + activity.getPackageName()))
        activity.startActivity(intent)
        return (True, "已打开系统设置：请允许「显示在其他应用上层」，然后回来再点一次")
    except Exception as exc:  # noqa: BLE001
        return (False, "打开系统设置失败: {0}".format(exc))


def request_notification_permission():
    """安卓 13 起，前台服务的常驻通知也要用户同意才会显示。"""
    if not _android:
        return (False, "只有安卓需要这个权限")
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Build = autoclass("android.os.Build$VERSION")
        if Build.SDK_INT < 33:
            return (True, "系统版本不需要")
        PythonActivity.mActivity.requestPermissions([NOTIFICATION_PERMISSION], 0)
        return (True, "已请求通知权限")
    except Exception as exc:  # noqa: BLE001
        return (False, "请求通知权限失败: {0}".format(exc))


def start_overlay(pet):
    """把宠物放到系统桌面上（启动后台服务）。"""
    global _service_started
    if not _android:
        return (False, "悬浮桌宠只在安卓手机上可用，电脑上请用应用内的小天地")
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        service = autoclass(SERVICE_CLASS)
        # 服务进程里用 os.environ["PYTHON_SERVICE_ARGUMENT"] 读到这个字符串。
        # 用全身静态图，悬浮在桌面上才是一只完整的宠物（不是只有一个头）。
        arguments = json.dumps({"image": pet.full_path(), "name": pet.name_zh,
                                "name_en": pet.name_en})
        # 用 p4a 生成类的 5 参数重载（smallIcon 留空 = 用应用图标），顺便设好通知文案
        service.start(activity, "", NOTIFICATION_TITLE, NOTIFICATION_TEXT, arguments)
        _service_started = True
        return (True, "已放到桌面上，可以拖它；再点一次可以召回")
    except Exception as exc:  # noqa: BLE001
        return (False, "启动悬浮桌宠失败: {0}".format(exc))


def stop_overlay():
    global _service_started
    if not _android:
        return (False, "悬浮桌宠只在安卓手机上可用")
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        service = autoclass(SERVICE_CLASS)
        service.stop(PythonActivity.mActivity)
        _service_started = False
        return (True, "已把桌宠召回")
    except Exception as exc:  # noqa: BLE001
        return (False, "召回失败: {0}".format(exc))
