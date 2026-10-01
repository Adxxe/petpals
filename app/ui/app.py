"""应用本体：一个 ScreenManager + 主菜单 / 宠物小天地两个页面。

物理返回键（Android 返回键 = 键值 27）的处理：
  * 在小天地里 -> 回主菜单；
  * 已经在主菜单 -> 退出应用（这是安卓上返回键该有的行为，
    不能像以前那样什么都不做，否则用户没法用返回键退出）。
"""

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, SlideTransition

from app import config, perf
from app.fonts import register_app_font
from app.ui.menu import MENU_SCREEN, MainMenuScreen
from app.ui.playground import PLAYGROUND_SCREEN, PlaygroundScreen

BACK_KEYS = (27, 1001)  # 27=ESC/安卓返回键；1001 是部分设备/手柄上报的返回键
TRANSITION_SECONDS = 0.15


class ShellApp(App):
    title = config.APP_TITLE_EN

    def build(self):
        # 必须在创建 Label 之前注册字体
        register_app_font()
        self.selected_pet = None

        manager = ScreenManager()
        manager.transition = SlideTransition(duration=TRANSITION_SECONDS)
        manager.add_widget(MainMenuScreen(on_select=self.show_pet))
        manager.add_widget(PlaygroundScreen(on_back=self.show_menu))
        self.manager = manager

        # 启动页是静止的主菜单：先按 30 帧跑（见 app/perf.py）
        perf.set_fps_cap(perf.FPS_IDLE)

        Window.bind(on_keyboard=self._on_keyboard)
        return manager

    def show_pet(self, pet):
        """选中某只宠物，带着它进小天地。"""
        self.selected_pet = pet
        self.manager.get_screen(PLAYGROUND_SCREEN).set_pet(pet)
        self.manager.current = PLAYGROUND_SCREEN

    def show_menu(self):
        self.manager.current = MENU_SCREEN

    def _on_keyboard(self, _window, key, *_args):
        if key in BACK_KEYS:
            if self.manager.current != MENU_SCREEN:
                self.show_menu()
            else:
                self.stop()
            return True
        return False


def build_app():
    """创建应用实例（Android 和桌面共用这一个入口）。"""
    return ShellApp()
