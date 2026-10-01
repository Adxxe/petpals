[app]

# 桌面显示名 / Android 桌面图标名（保持 ASCII，避免个别 launcher 乱码）
title = PetPals

# Android 包名：package.domain + package.name（和 app/config.py 保持一致）
package.name = petpals
package.domain = com.example

source.dir = .

# ttf/otf/ttc 一定要在列表里，否则 assets/fonts/ 下的中文字体不会被打进 APK
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf,otf,ttc

# tools/ tests/ .github/ 是开发用的，不打进 APK
source.exclude_dirs = tests,tools,.github,bin,.git,.buildozer,venv,.venv,__pycache__,.pytest_cache
source.exclude_patterns = README.md,BUILD.md,requirements.txt,requirements-build.txt,.gitignore

# 需要和 app/config.py 里的 APP_VERSION 保持一致
version = 0.7.0

# 空壳只依赖 kivy。
# 不写版本号 = 用 p4a 那一套 recipe 自带的版本（见下面的 p4a.branch）。
requirements = python3,kivy

# ★ 用 p4a 的正式发布版，**不要用 master**：
#   master（以及最新正式版 v2026.05.09）现在配的是 Python 3.14.2 + Kivy 2.3.1，
#   我们连撞两个新坑：老 Cython 生成的 C 对不上 3.14 的签名
#   （_PyLong_AsByteArray）、以及 build venv 里 pip._internal 少
#   BuildDependencyInstallError。v2024.01.21 = Python 3.11.5 + Kivy 2.3.0，
#   是长期被大量项目验证过的组合。
p4a.branch = v2024.01.21

orientation = portrait
fullscreen = 0

# 悬浮桌宠需要的权限（这是本应用唯一申请权限的地方）：
#   SYSTEM_ALERT_WINDOW  显示在其他应用上层（悬浮窗）—— 特殊权限，要用户去系统设置手动开
#   FOREGROUND_SERVICE   前台服务，让桌宠不被系统随手回收
#   POST_NOTIFICATIONS   安卓 13+ 显示前台服务的那条常驻通知
android.permissions = SYSTEM_ALERT_WINDOW, FOREGROUND_SERVICE, POST_NOTIFICATIONS

# 悬浮桌宠的后台服务。
#   * 键名是 services（buildozer 1.6 的官方模板如此；老教程里的 android.services 不是现在的写法）
#   * 名字首字母要大写：p4a 生成的 Java 类叫 ServicePetservice（在 Service.tmpl.java 里是 Service + name|capitalize）
#   * :foreground 让 p4a 以"前台服务"方式启动：PythonService.doStartForeground 会自己建通知渠道，
#     安卓 8+ 也不会漏通知；我们自己再调一次 startForeground 反而会多出一条通知
#   * 不加 :sticky：系统重启粘性服务时拿不到图片参数，会静默失败（见 README）
services = Petservice:service.py:foreground

# 目标 API 用 33：从 34 起前台服务必须声明 foregroundServiceType 并配额外的
# manifest 项，配置复杂且本机无法验证；要上架 Google Play 时再升，见 README。
android.api = 33
android.minapi = 21
# p4a v2024.01.21 只接受 NDK 25（MIN_NDK_VERSION = MAX_NDK_VERSION = 25，推荐 25b）；
# buildozer 1.6 默认会给 r28c，会被直接拒掉。
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
# 打包机上自动同意 Google 的 Android SDK 许可协议（buildozer 文档说明此项是给自动化用的）。
# 云端 CI 里如果卡在 "Do you accept the license?" 上会一直等到超时，所以打开它。
android.accept_sdk_license = True

# 图标：由 tools/make_pet_placeholders.py 生成，可直接换成你自己的
icon.filename = %(source.dir)s/assets/icon.png

# 开机启动图（Python 起来之前安卓先显示它，挡住冷启动黑屏）
presplash.filename = %(source.dir)s/assets/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
