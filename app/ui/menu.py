"""主菜单：从预设宠物里挑一只。

布局：背景图（一张整图，不占额外控件）在最底层，上面是标题 / 副标题 /
2 列卡片网格 / 离线提示。卡片用 size_hint 自适应，换机型不用改像素。
"""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from app import catalog, i18n, perf, theme
from app.fonts import ui_font_name
from app.resources import asset_path
from app.ui.widgets import PetCard

MENU_SCREEN = "menu"
GRID_COLUMNS = 2


class MainMenuScreen(Screen):
    def __init__(self, on_select=None, **kwargs):
        super().__init__(name=MENU_SCREEN, **kwargs)
        font = ui_font_name()
        self.cards = []

        root = FloatLayout()
        # 先加的在下层：背景图先加，内容后加
        self.background = Image(source=asset_path("ui", "bg_menu.png"), fit_mode="fill")
        root.add_widget(self.background)

        content = BoxLayout(orientation="vertical",
                            padding=(theme.PAD, dp(30), theme.PAD, theme.PAD),
                            spacing=dp(6))
        content.add_widget(self._line(i18n.app_title(), theme.TITLE_SIZE,
                                      theme.TEXT, dp(52), font))
        content.add_widget(self._line(i18n.menu_subtitle(), theme.SUBTITLE_SIZE,
                                      theme.TEXT_DIM, dp(22), font))

        grid = GridLayout(cols=GRID_COLUMNS, spacing=theme.GAP)
        self.grid = grid
        for pet in catalog.PETS:
            card = PetCard(pet, i18n.pet_name(pet), on_select=on_select, font_name=font)
            self.cards.append(card)
            grid.add_widget(card)
        content.add_widget(grid)

        content.add_widget(self._line(i18n.offline_hint(), theme.HINT_SIZE,
                                      theme.TEXT_DIM, dp(24), font))
        root.add_widget(content)
        self.add_widget(root)

    def on_pre_enter(self):
        # 主菜单是完全静止的（没有动画、没有定时器），30 帧就够，
        # 省一半的 GPU 和电。有动画的小天地会自己切回 60。
        perf.set_fps_cap(perf.FPS_IDLE)

    @staticmethod
    def _line(text, size, color, height, font):
        label = Label(text=text, font_size=size, color=color,
                      size_hint_y=None, height=height)
        if font:
            label.font_name = font
        return label
