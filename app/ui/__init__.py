"""界面层。

对外只暴露 build_app()，其它模块不要直接 import 这里的子模块。
"""

from app.ui.app import ShellApp, build_app

__all__ = ["ShellApp", "build_app"]
