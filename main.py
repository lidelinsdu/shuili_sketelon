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


app.include_router(router_1)
app.include_router(router_2)
app.include_router(router_3)
app.include_router(router_4)
app.include_router(router_5)


@app.get('/')
def hello():
    return '欢迎来到我的fastAPI应用！'




@router_4.get('/water_dispatch')
def water_dispatch():
    return "hello world"


if __name__ == '__main__':
    uvicorn.run(app, port=8081)
