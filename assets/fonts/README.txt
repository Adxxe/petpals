把中文字体放在这个目录里（.ttf / .otf / .ttc）。

为什么需要：Kivy 自带字体没有中文字形，不装中文字体的话界面文字会变方框。
app/fonts.py 会自动扫描本目录（按文件名排序取第一个），注册成界面字体，
并且会一起打进 APK，所以手机上一定有。

建议用可再分发的字体（OFL 协议），例如：
  - Noto Sans SC（Google，OFL）
  - 思源黑体 Source Han Sans（Adobe，OFL）
  - 霞鹜文楷 LXGW WenKai（OFL）

命名示例：00-NotoSansSC-Regular.otf（前缀数字用来控制优先级）。

不放字体也能跑：app/i18n.py 会自动把界面文字切成英文，
不会出现乱码方框；等你有空了再放进来。
