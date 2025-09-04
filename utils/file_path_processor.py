import os
import sys
import yaml

def resource_path(relative_path):
    """ 获取打包后资源的正确路径 """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的路径
        return os.path.join(sys._MEIPASS, relative_path)
    # 普通运行时路径
    return os.path.join(os.path.dirname(__file__), relative_path)

# 使用
config_file = resource_path('config/configuration.yaml')
