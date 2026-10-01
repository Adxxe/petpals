"""生成界面素材：菜单背景、小天地场景、宠物影子。

全部用代码画，属于占位美术：想换成正式图，直接覆盖 assets/ui/ 下的同名文件即可。
场景的地平线高度读 app/config.py 的 SCENE_HORIZON，和界面里的活动区域严格对齐。

用法:
    python tools/make_ui_assets.py
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.config import SCENE_HORIZON  # noqa: E402

UI_DIR = os.path.join(ROOT, "assets", "ui")
ASSETS_DIR = os.path.join(ROOT, "assets")
W, H = 512, 1000
MENU_W, MENU_H = 256, 500      # 菜单背景只需要半分辨率（纯柔和渐变）

SKY_TOP = (169, 216, 245)
SKY_BOTTOM = (255, 235, 214)
GROUND_TOP = (172, 219, 140)
GROUND_BOTTOM = (104, 172, 100)


def vertical_gradient(size, top, bottom):
    """竖直线性渐变（PIL 的 y=0 在最上面）。"""
    width, height = size
    strip = Image.new("RGB", (1, height))
    pixels = strip.load()
    for y in range(height):
        ratio = y / max(1, height - 1)
        pixels[0, y] = tuple(
            int(round(top[i] + (bottom[i] - top[i]) * ratio)) for i in range(3)
        )
    return strip.resize((width, height), Image.BILINEAR)


def build_scene():
    """小天地：天空 + 远山 + 草地。地平线位置和界面活动区一致。"""
    horizon = int(round(H * (1.0 - SCENE_HORIZON)))
    scene = vertical_gradient((W, H), SKY_TOP, SKY_BOTTOM).convert("RGBA")

    # 远山（在天空层上画，等下被草地盖住下半截）
    hills = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hill_draw = ImageDraw.Draw(hills)
    hill_draw.ellipse([-0.32 * W, horizon - 74, 0.72 * W, horizon + 320],
                      fill=(178, 214, 186, 255))
    hill_draw.ellipse([0.44 * W, horizon - 116, 1.36 * W, horizon + 320],
                      fill=(154, 200, 166, 255))
    scene.alpha_composite(hills)

    # 草地：贴在下半部分
    ground = vertical_gradient((W, H - horizon), GROUND_TOP, GROUND_BOTTOM).convert("RGBA")
    scene.paste(ground, (0, horizon))

    # 地平线附近的柔光，让天地交接不生硬
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([-0.4 * W, horizon - 60, 1.4 * W, horizon + 150],
                      fill=(255, 255, 220, 130))
    glow = glow.filter(ImageFilter.GaussianBlur(26))
    scene.alpha_composite(glow)

    # 太阳 + 光晕
    sun_x, sun_y, sun_r = 0.78 * W, 0.15 * H, 0.085 * W
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse(
        [sun_x - sun_r * 2.6, sun_y - sun_r * 2.6, sun_x + sun_r * 2.6, sun_y + sun_r * 2.6],
        fill=(255, 226, 150, 150))
    scene.alpha_composite(halo.filter(ImageFilter.GaussianBlur(30)))
    ImageDraw.Draw(scene).ellipse(
        [sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r],
        fill=(255, 243, 200, 255))

    # 云
    clouds = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cloud_draw = ImageDraw.Draw(clouds)
    for cx, cy, scale, alpha in ((0.26, 0.14, 1.00, 240), (0.66, 0.30, 0.72, 215),
                                 (0.50, 0.07, 0.58, 200)):
        r = 0.075 * W * scale
        for dx, dy, rr in ((-r * 0.9, 0.0, r * 0.75), (0.0, -r * 0.25, r),
                           (r * 0.95, 0.0, r * 0.7), (0.0, r * 0.25, r * 0.85)):
            cloud_draw.ellipse([cx + dx - rr, cy + dy - rr * 0.8,
                                cx + dx + rr, cy + dy + rr * 0.8],
                               fill=(255, 255, 255, alpha))
    scene.alpha_composite(clouds.filter(ImageFilter.GaussianBlur(4)))

    # 草地上的小草和几朵小花
    detail = ImageDraw.Draw(scene)
    for index in range(26):
        gx = (index * 0.618 + 0.07) % 1.0 * W
        gy = horizon + 18 + ((index * 53) % 12) * 9
        height = 9 + (index % 4) * 4
        detail.line([(gx, gy), (gx - 4, gy - height)], fill=(92, 158, 88, 220), width=2)
        detail.line([(gx, gy), (gx + 4, gy - height * 0.85)], fill=(92, 158, 88, 220), width=2)
    for index in range(9):
        fx = (index * 0.271 + 0.13) % 1.0 * W
        fy = horizon + 60 + ((index * 71) % 10) * 26
        colour = ((255, 236, 150, 255), (255, 214, 224, 255), (255, 255, 255, 255))[index % 3]
        detail.ellipse([fx - 4, fy - 4, fx + 4, fy + 4], fill=colour)
        detail.ellipse([fx - 1.5, fy - 1.5, fx + 1.5, fy + 1.5], fill=(246, 196, 96, 255))

    return scene


def build_menu_bg(width=MENU_W, height=MENU_H):
    """菜单背景：暖色渐变 + 几块柔光，浅色背景上放深色文字。

    故意只做半分辨率：整张图都是柔和渐变，放大后肉眼看不出差别，
    但显存只有 1/4、解码也更快（冷启动省下来的就是这种小钱）。
    """
    bg = vertical_gradient((width, height), (255, 243, 226), (226, 228, 250)).convert("RGBA")

    blobs = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    blob_draw = ImageDraw.Draw(blobs)
    blob_draw.ellipse([-0.35 * width, -0.12 * height, 0.75 * width, 0.36 * height],
                      fill=(255, 206, 158, 150))
    blob_draw.ellipse([0.35 * width, 0.62 * height, 1.45 * width, 1.15 * height],
                      fill=(176, 200, 250, 140))
    blob_draw.ellipse([-0.25 * width, 0.72 * height, 0.55 * width, 1.10 * height],
                      fill=(255, 224, 190, 120))
    # 模糊半径跟着分辨率一起缩，视觉上的柔度才和原来一致
    bg.alpha_composite(blobs.filter(ImageFilter.GaussianBlur(int(70 * width / W))))

    # 几颗柔光圆斑：给背景一点层次，但要小、要淡，
    # 太大太亮会像"糊了一块"（第一版就是这样，被自己看出来了）
    bokeh = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bokeh_draw = ImageDraw.Draw(bokeh)
    spots = ((0.22, 0.14, 0.10, (255, 255, 255, 46)),
             (0.80, 0.20, 0.12, (255, 240, 215, 42)),
             (0.30, 0.44, 0.13, (255, 255, 255, 34)),
             (0.74, 0.60, 0.09, (255, 255, 255, 44)),
             (0.14, 0.74, 0.11, (255, 232, 205, 38)),
             (0.58, 0.90, 0.13, (255, 255, 255, 36)))
    for cx, cy, size, colour in spots:
        radius = size * width
        centre_x, centre_y = cx * width, cy * height
        bokeh_draw.ellipse([centre_x - radius, centre_y - radius,
                            centre_x + radius, centre_y + radius], fill=colour)
    bg.alpha_composite(bokeh.filter(ImageFilter.GaussianBlur(int(18 * width / W))))
    return bg


def build_shadow():
    """宠物脚下的软阴影：中间深、边缘透明。

    注意用平方曲线而不是线性衰减：线性衰减会有一大块"平台区"，
    在宠物脚下会看起来像一个灰色方框（踩过这个坑）。
    """
    width, height = 256, 128
    radial = Image.radial_gradient("L").resize((width, height), Image.LANCZOS)
    alpha = ImageOps.invert(radial).point(lambda value: int((value / 255.0) ** 2.0 * 210))
    alpha = alpha.filter(ImageFilter.GaussianBlur(3))
    shadow = Image.new("RGBA", (width, height), (46, 58, 40, 255))
    shadow.putalpha(alpha)
    return shadow


def build_presplash():
    """开机启动图：安卓在 Python 起来之前会先显示这张图（p4a 的 presplash），
    挡住冷启动那几百毫秒的黑屏。"""
    shot = build_menu_bg(W, H)
    try:  # 复用宠物工具里的图标画法；单独跑本文件时在 tools/ 目录下能找到
        from make_pet_placeholders import build_icon
    except ImportError:  # pragma: no cover - 拿不到就只出渐变背景
        return shot

    side = int(W * 0.42)
    icon = build_icon(side).resize((side, side), Image.LANCZOS)
    shot.alpha_composite(icon, ((W - side) // 2, int(H * 0.36)))
    return shot


def save(image, name, folder=UI_DIR):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    image.save(path, "PNG", optimize=True)
    print("wrote {0} ({1} bytes)".format(os.path.relpath(path, ROOT), os.path.getsize(path)))


def main():
    save(build_menu_bg(), "bg_menu.png")
    save(build_scene(), "bg_scene.png")
    save(build_shadow(), "shadow.png")
    # 启动图要放在 assets/ 根目录（buildozer.spec 里是这么引用的）
    save(build_presplash(), "presplash.png", ASSETS_DIR)
    print("done, 4 files")


if __name__ == "__main__":
    main()
