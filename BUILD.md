# 怎么把它变成手机上能装的 APK

**结论先放这**：这台开发机是 Windows，**buildozer 不能在 Windows 上打 Android 包**
（python-for-android 的 Android 目标在 Windows 上直接抛 `NotImplementedError`；
这台机器也没有 WSL / Docker / JDK / Android SDK）。
所以要出 APK，得借一台 Linux —— 下面三条路，推荐第一条。

---

## 路线 A（推荐）：用 GitHub Actions 在云端打包

不用装 Linux、不用管理员权限、不用重启。第一次大概 20~40 分钟（要下 Android SDK/NDK），
之后有缓存，几分钟就能出包。

1. 注册/登录 [github.com](https://github.com)；
2. 新建一个仓库（private 也行），把 `D:\APP111` 里的文件传上去
   （网页上 "uploading an existing file" 直接拖文件夹就行，不用会 git）；
3. 确保 `.github/workflows/android.yml` 也传上去了（本仓库里已经有了）；
4. 打开仓库的 **Actions** 页 → 左边选 **Build Android APK** → 右边 **Run workflow**；
5. 等它跑绿，点进这次运行，最下面 **Artifacts** 里下载 `petpals-debug-apk`，
   解压出来就是 `petpals-0.7.0-debug.apk`；
6. 把 APK 传到手机（微信/QQ/数据线都行），点击安装，
   手机需要允许"安装未知来源应用"。

> private 仓库也能用 Actions（每月有免费额度，一次打包约 20~40 分钟，够用）。
>
> **想快一倍**：把 `buildozer.spec` 里的 `android.archs` 改成只留 `arm64-v8a`
> （现在的 `arm64-v8a, armeabi-v7a` 是两种 CPU 架构各打一遍，兼容性最好但最慢。
> 2017 年之后的手机基本都是 arm64，只留一个也够用）。
>
> `buildozer.spec` 里 `android.accept_sdk_license = True` 是给打包机自动同意
> Google 的 Android SDK 许可协议用的（不然 CI 会卡在 "Do you accept the license?" 上）。

---

## 路线 B：本机装 WSL 后打包（要重启一次，需要管理员权限）

```powershell
# 1) 管理员身份打开 PowerShell，装 WSL + Ubuntu（装完要重启）
wsl --install -d Ubuntu

# 2) 重启后打开 Ubuntu，装系统依赖
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv \
    autoconf automake libtool pkg-config zlib1g-dev libncurses5-dev \
    libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# 3) 项目目录在 WSL 里的路径是 /mnt/d/APP111
cd /mnt/d/APP111
python3 -m venv .venv && source .venv/bin/activate
pip install buildozer "cython<3"

# 4) 打包（首次 20~40 分钟，会下载 Android SDK/NDK 约 3~5GB）
yes | buildozer -v android debug
```

产物：`/mnt/d/APP111/bin/petpals-0.7.0-debug.apk`（Windows 里就是 `D:\APP111\bin\`）。

**注意**：打包最好在 WSL 自己的家目录（`~/petpals`）里做，再拷回 Windows。
直接在 `/mnt/d/...` 下打会慢很多（跨文件系统）而且偶发权限问题。

---

## 路线 C：不打包，手机上直接跑源码（没有悬浮桌宠）

想先看界面和桌宠走路，最快的办法：

- **Pydroid 3**：把 `D:\APP111` 整个目录拷到手机 → Pydroid 里用它的 pip 装 `kivy`
  → 打开 `main.py` → 点运行。
- **Termux**：`pkg install python`，装好 kivy 后 `python main.py`。

这条路 **只能跑应用内的小天地**：悬浮桌宠需要 p4a 的后台服务和 `SYSTEM_ALERT_WINDOW`
权限声明，只有打包成 APK 才有。

---

## 装到手机之后要试什么

1. **打开要多久**（冷启动那一下）；
2. 选一只宠物 → 看它**走路顺不顺**、四肢/翅膀动不动；
3. 按住**拖**它，松手后会不会自己继续走；
4. 点右上角 **「放到桌面」** → 会跳系统设置，打开 **「显示在其他应用上层」**
   → 回来再点一次 → 看宠物有没有浮在桌面上；
5. 如果没出来，用数据线连电脑看日志（需要 adb）：

```bash
adb logcat -s PetPalsOverlay python
```

对照表（README 里也有）：

| 日志 | 意思 |
| --- | --- |
| `桌宠已上桌面: ...` | 成功了 |
| `找不到宠物图片: '...'` | 服务没收到图片路径 |
| `加悬浮窗失败（多半是没给「显示在其他应用上层」权限）` | 权限没开 |
| 完全没有日志 | 服务根本没起来，先检查 `buildozer.spec` 里 `services` 那一行 |

**提醒**：悬浮桌宠这部分代码**我一次都没在真机上验证过**（本机打不出包）。
真出了问题是正常的，把 logcat 贴回来我改。
