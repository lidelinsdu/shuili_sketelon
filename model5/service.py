import io
import json
import os

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from model5.algorithm import nir_red_to_smi, plot_heatmap, get_dynamic_smi, get_continuous_dry_day, \
    get_rain_avg_lap_rate

router_5 = APIRouter(
    prefix="/model5",
    tags=["水旱灾害防御模型"]
)


@router_5.get('/get_smi')
def flood_drought_defend_get_smi(red_tif_dir, nir_tif_dir):
    """
    获取对应遥感图像的土壤含水量数组，分辨率与文件相同
    :param red_tif_dir: 红波tif路径
    :param nir_tif_dir: 近红外tif路径
    :return: 土壤含水量二维数组
    """
    smi = nir_red_to_smi(red_tif_dir, nir_tif_dir)
    buffer = bytearray(smi.tobytes())

    stream = io.BytesIO(buffer)

    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename=data.bin",
            "X-Array-Shape": str(smi.shape),  # 可选：传递形状信息
            "X-Array-Dtype": str(smi.dtype),  # 可选：传递类型信息
        }
    )

class FileInfo(BaseModel):
    filename: str
    file_extension: str
    file_size: int

@router_5.post('/draw_heatmap')
async def draw_heatmap(obj: dict):
    """
    绘制热度图
    :param obj: 包含土壤含水量数组的json
    :return: 热度图文件保存路径
    """
    heatmap_file =  plot_heatmap(obj["smi"], obj["filename"])
    stream = open(heatmap_file, "rb").read() # 返回bytes[]
    filename = heatmap_file.split("/")[-1]
    name, ext = filename.split(".")
    size = os.path.getsize(heatmap_file)
    file_info = FileInfo(filename=filename, file_extension=ext, file_size=size)
    return StreamingResponse(
        io.BytesIO(stream),
        media_type="image/png",
        headers={"FileInfo": file_info.model_dump_json()}
    )



@router_5.get('/dynamic_smi')
def dynamic_smi(file_list):
    """
    获取连续多个tif土壤含水量数组，以得到动态土壤水分演变
    :param file_list: json数组，每个json对象都是{"red_dir":"","nir_dir":""}
    :return: smi_list
    """
    return get_dynamic_smi(file_list)


@router_5.post('/get_continuous_no_rain_day')
def get_continuous_no_rain_day():
    """
    获得连续无雨日
    :return: 连续无语日列表和无雨天数
    """
    encoded_data = json.dumps(get_continuous_dry_day())
    return encoded_data

@router_5.post('/get_rain_avg_lap_rate')
def get_rain_avg_lap_rate_service(span: str, history_avg, precip_list, ):
    """
    计算降雨距平指数
    :param span: 时间跨度['year', 'month', 'xun']
    :param history_avg: 历史同时期的平均雨量
    :param precip_list: 历史降雨数据序列，要和spand对应起来；{"date":"","precip":""}
    :return: 降雨平均指数
    """
    rate = get_rain_avg_lap_rate(span, history_avg, precip_list)
    return rate