"""生成占位用的宠物素材（透明背景 PNG）。

每只宠物按**物种骨架**生成，不再是"人形站在两边"：

  四足（猫 / 狗 / 兔）  坐姿：<id>.png 头 / <id>_body.png 身子 / <id>_paw.png 前爪
  小鸟                  蛋形：<id>.png 头 / <id>_body.png 身子 /
                        <id>_wing.png 翅膀 / <id>_claw.png 小爪子
  所有宠物              <id>_full.png 全身静态图（菜单卡片 + 安卓悬浮窗）

部件位置来自 app/pet_layout.py，和界面里会动的那只共用同一套数字。
都是占位素材：你有正式美术资源时，用同名 PNG 覆盖 assets/pets/ 里的文件即可，代码不用改。

用法:
    python tools/make_pet_placeholders.py
    python tools/make_pet_placeholders.py --size 768
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)      # 为了 import app.pet_layout（拼装位置共用一套数字）
PETS_DIR = os.path.join(ROOT, "assets", "pets")
ICON_PATH = os.path.join(ROOT, "assets", "icon.png")

SS = 4  # 超采样倍数：先画 4 倍大再缩小，边缘才平滑（相当于抗锯齿）

INK = (58, 44, 38, 255)
WHITE = (255, 255, 255, 255)

# 每只宠物的配色。头和身子都从这里取色，保证拼起来是一套。
PALETTES = {
    "cat": {
        "fur": (244, 170, 96, 255), "dark": (206, 124, 58, 255),
        "belly": (252, 225, 192, 255), "inner": (247, 178, 168, 255),
        "beak": (250, 196, 84, 255),
    },
    "dog": {
        "fur": (186, 132, 84, 255), "dark": (140, 94, 56, 255),
        "belly": (236, 212, 186, 255), "inner": (238, 138, 150, 255),
        "beak": (250, 196, 84, 255),
    },
    "rabbit": {
        "fur": (222, 226, 236, 255), "dark": (168, 172, 186, 255),
        "belly": (250, 252, 255, 255), "inner": (248, 182, 196, 255),
        "beak": (250, 196, 84, 255),
    },
    "bird": {
        "fur": (92, 168, 232, 255), "dark": (54, 118, 178, 255),
        "belly": (208, 236, 252, 255), "inner": (250, 196, 84, 255),
        "beak": (250, 196, 84, 255),
    },
}


def _canvas(size):
    """返回 (图像, 画笔, 画布边长)。坐标一律用 0~1 的比例，乘 s 得到像素。"""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), s


def _finish(img, size):
    return img.resize((size, size), Image.LANCZOS)


def _poly(d, s, points, fill, outline=None, width=0.012):
    d.polygon([(x * s, y * s) for x, y in points],
              fill=fill, outline=outline, width=max(1, int(width * s)))


def _oval(d, s, cx, cy, rx, ry, fill, outline=None, width=0.012):
    d.ellipse([(cx - rx) * s, (cy - ry) * s, (cx + rx) * s, (cy + ry) * s],
              fill=fill, outline=outline, width=max(1, int(width * s)))


def _eyes(d, s, cx_list, cy, rx=0.055, ry=0.075):
    for cx in cx_list:
        _oval(d, s, cx, cy, rx, ry, INK)
        _oval(d, s, cx - 0.018, cy - 0.028, 0.018, 0.018, WHITE)


"""---------------- 头 ----------------"""


def build_cat(size, kind="cat"):
    """小猫：橘色，尖耳朵 + 胡须。"""
    img, d, s = _canvas(size)
    pal = PALETTES["cat"]
    fur, dark, pink = pal["fur"], pal["dark"], pal["inner"]

    _poly(d, s, [(0.20, 0.44), (0.28, 0.09), (0.54, 0.26)], fur, dark)
    _poly(d, s, [(0.80, 0.44), (0.72, 0.09), (0.46, 0.26)], fur, dark)
    _poly(d, s, [(0.28, 0.36), (0.32, 0.18), (0.45, 0.27)], pink)
    _poly(d, s, [(0.72, 0.36), (0.68, 0.18), (0.55, 0.27)], pink)

    _oval(d, s, 0.50, 0.55, 0.37, 0.35, fur, dark)
    _eyes(d, s, (0.36, 0.64), 0.50)

    _poly(d, s, [(0.465, 0.635), (0.535, 0.635), (0.50, 0.69)], pink)
    for x0, x1, a0, a1 in ((0.42, 0.50, 0, 90), (0.50, 0.58, 90, 180)):
        d.arc([x0 * s, 0.655 * s, x1 * s, 0.755 * s], a0, a1, fill=INK,
              width=max(1, int(0.010 * s)))

    for dy in (-0.035, 0.015, 0.065):
        d.line([(0.31 * s, (0.665 + dy) * s), (0.11 * s, (0.63 + dy * 1.7) * s)],
               fill=dark, width=max(1, int(0.008 * s)))
        d.line([(0.69 * s, (0.665 + dy) * s), (0.89 * s, (0.63 + dy * 1.7) * s)],
               fill=dark, width=max(1, int(0.008 * s)))
    return img


def build_dog(size, kind="dog"):
    """小狗：棕色，垂耳 + 浅色口鼻。"""
    img, d, s = _canvas(size)
    pal = PALETTES["dog"]
    fur, dark, muzzle = pal["fur"], pal["dark"], pal["belly"]

    _oval(d, s, 0.20, 0.56, 0.16, 0.27, dark)
    _oval(d, s, 0.80, 0.56, 0.16, 0.27, dark)

    _oval(d, s, 0.50, 0.52, 0.34, 0.34, fur, dark)
    _oval(d, s, 0.50, 0.665, 0.17, 0.145, muzzle)
    _eyes(d, s, (0.37, 0.63), 0.48, rx=0.05, ry=0.065)
    _oval(d, s, 0.50, 0.585, 0.06, 0.045, INK)

    d.arc([0.44 * s, 0.63 * s, 0.56 * s, 0.73 * s], 0, 180, fill=(120, 78, 48, 255),
          width=max(1, int(0.010 * s)))
    _oval(d, s, 0.50, 0.755, 0.045, 0.045, pal["inner"])
    return img


def build_rabbit(size, kind="rabbit"):
    """小兔：浅灰，长耳朵 + 粉内耳。"""
    img, d, s = _canvas(size)
    pal = PALETTES["rabbit"]
    fur, dark, pink = pal["fur"], pal["dark"], pal["inner"]

    _oval(d, s, 0.385, 0.27, 0.085, 0.25, fur, dark)
    _oval(d, s, 0.615, 0.27, 0.085, 0.25, fur, dark)
    _oval(d, s, 0.385, 0.275, 0.042, 0.185, pink)
    _oval(d, s, 0.615, 0.275, 0.042, 0.185, pink)

    _oval(d, s, 0.50, 0.66, 0.34, 0.32, fur, dark)
    _eyes(d, s, (0.37, 0.63), 0.62, rx=0.05, ry=0.065)
    _poly(d, s, [(0.47, 0.745), (0.53, 0.745), (0.50, 0.795)], pink)

    for dy in (-0.03, 0.02):
        d.line([(0.32 * s, (0.775 + dy) * s), (0.12 * s, (0.75 + dy * 1.6) * s)],
               fill=dark, width=max(1, int(0.007 * s)))
        d.line([(0.68 * s, (0.775 + dy) * s), (0.88 * s, (0.75 + dy * 1.6) * s)],
               fill=dark, width=max(1, int(0.007 * s)))
    return img


def build_bird(size, kind="bird"):
    """小鸟：蓝色，尖喙 + 呆毛 + 腮红。"""
    img, d, s = _canvas(size)
    pal = PALETTES["bird"]
    fur, dark, beak = pal["fur"], pal["dark"], pal["beak"]
    cheek = (244, 150, 160, 200)

    _poly(d, s, [(0.45, 0.26), (0.52, 0.04), (0.60, 0.26)], fur, dark)
    _oval(d, s, 0.50, 0.56, 0.33, 0.32, fur, dark)
    _eyes(d, s, (0.38, 0.62), 0.52, rx=0.055, ry=0.07)
    _poly(d, s, [(0.405, 0.615), (0.595, 0.615), (0.50, 0.75)], beak, (214, 150, 40, 255))
    _oval(d, s, 0.245, 0.70, 0.055, 0.04, cheek)
    _oval(d, s, 0.755, 0.70, 0.055, 0.04, cheek)
    return img


HEADS = {
    "cat": build_cat,
    "dog": build_dog,
    "rabbit": build_rabbit,
    "bird": build_bird,
}


"""---------------- 身子与四肢（按物种）----------------"""


def build_body(size, kind):
    """身子：四足是"坐着的屁股 + 胸口 + 尾巴"，小鸟是蛋形 + 尾羽。"""
    if kind == "bird":
        return _bird_body(size)
    return _quadruped_body(size, kind)


def _quadruped_body(size, kind):
    """坐姿的身子。注意：部件图里 PIL 的 y=0 是这个方框的**上边**，
    所以"屁股/后脚"要画在 y 大的地方，"胸口"画在 y 小的地方。"""
    img, d, s = _canvas(size)
    pal = PALETTES[kind]
    fur, dark, belly = pal["fur"], pal["dark"], pal["belly"]

    # 尾巴（先画，压在身子后面）：从右侧露出来一小截，别跑到脸旁边
    _oval(d, s, 0.90, 0.60, 0.085, 0.085, fur, dark)
    _oval(d, s, 0.92, 0.45, 0.06, 0.075, fur, dark)
    # 屁股 / 后腿（下半部分，宽底座）
    _oval(d, s, 0.50, 0.72, 0.40, 0.24, fur, dark)
    # 胸口（上半部分，窄一点）
    _oval(d, s, 0.50, 0.38, 0.27, 0.29, fur, dark)
    # 肚皮
    _oval(d, s, 0.50, 0.55, 0.16, 0.22, belly)
    # 露在底座两侧的后脚（最下面）
    _oval(d, s, 0.19, 0.88, 0.13, 0.075, belly, dark)
    _oval(d, s, 0.81, 0.88, 0.13, 0.075, belly, dark)
    return img


def _bird_body(size):
    """小鸟的蛋形身子 + 尾羽（尾羽在右上，翘起来）。"""
    img, d, s = _canvas(size)
    pal = PALETTES["bird"]
    fur, dark, belly = pal["fur"], pal["dark"], pal["belly"]

    _poly(d, s, [(0.60, 0.62), (0.99, 0.76), (0.97, 0.46), (0.64, 0.44)], fur, dark)
    _oval(d, s, 0.50, 0.52, 0.30, 0.36, fur, dark)
    _oval(d, s, 0.50, 0.58, 0.19, 0.24, belly)
    return img


def build_limb(size, kind, role):
    """四肢 / 翅膀：按角色画不同形状。"""
    if role == "wing":
        return _wing(size)
    if role == "claw":
        return _claw(size)
    return _paw(size, kind)


def _paw(size, kind):
    """坐姿四足的前爪：一条短前腿，脚掌在最下面。"""
    img, d, s = _canvas(size)
    pal = PALETTES[kind]
    fur, dark, belly = pal["fur"], pal["dark"], pal["belly"]

    d.rounded_rectangle([0.30 * s, 0.05 * s, 0.70 * s, 0.90 * s],
                        radius=0.19 * s, fill=fur, outline=dark,
                        width=max(1, int(0.07 * s)))
    _oval(d, s, 0.50, 0.82, 0.21, 0.12, belly)
    return img


def _wing(size):
    """小鸟的翅膀：圆润的叶形（左右对称，不用镜像）。"""
    img, d, s = _canvas(size)
    pal = PALETTES["bird"]
    fur, dark, belly = pal["fur"], pal["dark"], pal["belly"]

    _poly(d, s, [(0.50, 0.02), (0.76, 0.13), (0.93, 0.40), (0.87, 0.71),
                 (0.63, 0.93), (0.37, 0.93), (0.13, 0.71), (0.07, 0.40),
                 (0.24, 0.13)], fur, dark)
    _poly(d, s, [(0.50, 0.16), (0.70, 0.25), (0.81, 0.44), (0.76, 0.67),
                 (0.58, 0.84), (0.42, 0.84), (0.24, 0.67), (0.19, 0.44),
                 (0.30, 0.25)], belly, width=0.008)
    return img


def _claw(size):
    """小鸟的小爪子：细细一条腿 + 三个朝下的脚趾（不是粗腿）。"""
    img, d, s = _canvas(size)
    dark = PALETTES["bird"]["dark"]

    d.line([(0.50 * s, 0.04 * s), (0.50 * s, 0.58 * s)],
           fill=dark, width=max(1, int(0.06 * s)))
    for dx in (-0.24, 0.0, 0.24):
        d.line([(0.50 * s, 0.56 * s), ((0.50 + dx) * s, 0.92 * s)],
               fill=dark, width=max(1, int(0.05 * s)))
    return img


def build_full(size, kind):
    """按物种骨架拼一张全身静态图（菜单卡片和安卓悬浮窗直接用这张）。"""
    from app import pet_layout

    species = pet_layout.species_of(kind)

    def render(role, side, side_px):
        if role == "body":
            return _finish(build_body(side_px, kind), side_px)
        if role == "head":
            return _finish(HEADS[kind](side_px, kind), side_px)
        return _finish(build_limb(side_px, kind, role), side_px)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for part in pet_layout.layout_for(species):
        _x, top, side = pet_layout.to_top_down(part.rect)
        side_px = max(8, int(size * side))
        part_img = render(part.role, part.side, side_px)
        img.alpha_composite(part_img, (int(size * _x), int(size * top)))
    return img


def build_icon(size):
    """应用图标：圆角底色 + 小猫头像（不透明，Android 会用系统遮罩再切一次）。"""
    s = size * SS
    bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(bg)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=(38, 46, 66, 255))
    d.rounded_rectangle([int(s * 0.06)] * 2 + [int(s * 0.94)] * 2,
                        radius=int(s * 0.18), fill=(46, 122, 106, 255))

    pet = build_cat(size).resize((int(s * 0.74), int(s * 0.74)), Image.LANCZOS)
    bg.alpha_composite(pet, (int(s * 0.13), int(s * 0.14)))
    return bg


def _save(img, path, size):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if img.size != (size, size):
        img = img.resize((size, size), Image.LANCZOS)
    img.save(path, "PNG", optimize=True)
    return os.path.getsize(path)


def build_assets(pets_dir, head_size):
    """生成所有宠物素材，返回产物列表 [(文件名, 字节数)]。"""
    from app import pet_layout

    body_size = max(128, head_size // 2)
    limb_size = max(64, head_size // 4)
    full_size = max(192, int(head_size * 0.75))
    written = []

    for kind in HEADS:
        species = pet_layout.species_of(kind)
        roles = ["paw"] if species == "quadruped" else ["wing", "claw"]
        targets = [(HEADS[kind], head_size, "{0}.png".format(kind), None),
                   (build_body, body_size, "{0}_body.png".format(kind), None)]
        for role in roles:
            targets.append((build_limb, limb_size,
                            "{0}_{1}.png".format(kind, role), role))
        targets.append((build_full, full_size, "{0}_full.png".format(kind), None))

        for builder, size, name, role in targets:
            path = os.path.join(pets_dir, name)
            if role is None:
                image = builder(size, kind)
            else:
                image = builder(size, kind, role)
            written.append((name, _save(image, path, size)))

    icon_path = os.path.join(ROOT, "assets", "icon.png")
    written.append(("icon.png", _save(build_icon(head_size), icon_path, head_size)))
    return written


def main():
    parser = argparse.ArgumentParser(description="生成占位宠物素材")
    parser.add_argument("--size", type=int, default=512, help="头部边长（默认 512）")
    args = parser.parse_args()

    written = build_assets(PETS_DIR, args.size)
    total = 0
    for name, size in written:
        total += size
        print("wrote assets\\pets\\{0} ({1} bytes)".format(name, size))
    print("done, {0} files, {1:.1f} KB total".format(len(written), total / 1024.0))


if __name__ == "__main__":
    main()
