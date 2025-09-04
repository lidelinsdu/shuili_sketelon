import uvicorn
from fastapi import FastAPI, APIRouter

from model1.service import router_1
from model2.service import router_2
from model3.service import router_3
from model5.service import router_5

app = FastAPI()



router_4 = APIRouter(
    prefix="/model4",
    tags=["输配水调度模型"]
)

router_default = APIRouter(
    prefix="/utils",
    tags=["工具API"]
)

@router_default.get('/get_current_dir')
def get_current_dir():
    return os.getcwd()

app.include_router(router_1)
app.include_router(router_2)
app.include_router(router_3)
app.include_router(router_4)
app.include_router(router_5)
app.include_router(router_default)

@app.get('/')
def hello():
    return '欢迎来到我的fastAPI应用！'


# @router_4.get('/water_dispatch')
# def water_dispatch():
#     return "hello world"


import os
import sys

# 修复 PyInstaller 打包后 GDAL_DATA 路径
if getattr(sys, 'frozen', False):
    # 我们在 PyInstaller 打包的环境中
    bundle_dir = sys._MEIPASS
    os.environ['GDAL_DATA'] = os.path.join(bundle_dir, 'gdal')
    os.environ['PROJ_LIB'] = os.path.join(bundle_dir, 'proj')
    # 可选：设置日志级别
    os.environ['CPL_LOG'] = '/dev/null'

if __name__ == '__main__':
    uvicorn.run(app, port=8081, host='0.0.0.0',)
