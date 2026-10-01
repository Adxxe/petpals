"""预设宠物名录。

这里只有数据，没有任何逻辑：菜单会把 PETS 里的每一条渲染成一张卡片。
要加新宠物，就在 PETS 里加一条，并把同名 PNG 放进 assets/pets/。
"""

import os

from dataclasses import dataclass

from app import pet_layout
from app.resources import asset_path


@dataclass(frozen=True)
class Pet:
    id: str
    name_zh: str
    name_en: str
    image: str          # 相对 assets/ 的路径
    accent: tuple       # 卡片底色（RGBA 0~1），让每只宠物有点区分

    def image_path(self):
        """头像（小天地里拼装用）。"""
        return asset_path(*self.image.split("/"))

    def body_path(self):
        return asset_path("pets", "{0}_body.png".format(self.id))

    def limb_path(self, role):
        """四足是 paw（前爪），小鸟是 wing / claw（翅膀 / 小爪子）。"""
        return asset_path("pets", "{0}_{1}.png".format(self.id, role))

    def full_path(self):
        """全身静态图：菜单卡片和安卓悬浮窗用这张。"""
        return asset_path("pets", "{0}_full.png".format(self.id))

    def species(self):
        return pet_layout.species_of(self.id)


PETS = (
    Pet("cat", "小猫", "Kitten", "pets/cat.png", (0.96, 0.67, 0.38, 1)),
    Pet("dog", "小狗", "Puppy", "pets/dog.png", (0.73, 0.52, 0.33, 1)),
    Pet("rabbit", "小兔", "Bunny", "pets/rabbit.png", (0.85, 0.87, 0.93, 1)),
    Pet("bird", "小鸟", "Birdie", "pets/bird.png", (0.36, 0.66, 0.91, 1)),
)


def get_pet(pet_id):
    """按 id 取宠物；找不到返回 None。"""
    for pet in PETS:
        if pet.id == pet_id:
            return pet
    return None
