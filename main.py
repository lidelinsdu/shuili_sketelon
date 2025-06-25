from fastapi import FastAPI
app = FastAPI()


@app.get('/')
def hello():
    return '欢迎来到我的Flask应用！'

@app.get('/inflow_predict')
def inflow_predict():
    return "hello world"

@app.get('/water_predict')
def water_predict():
    return "hello world"

@app.get('/water_allocation')
def water_allocation():
    return "hello world"

@app.get('/water_dispatch')
def water_dispatch():
    return "hello world"

@app.get('/flood_drought_defend')
def flood_drought_defend():
    return "hello world"
