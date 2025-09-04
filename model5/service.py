import datetime as dt
import os
from typing import List, Optional
import utils.file_path_processor

import yaml
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from starlette.responses import FileResponse

from model5.algorithm import nir_red_to_smi, get_dynamic_smi, get_continuous_dry_day, \
    get_rain_avg_lap_rate, write_tiff_file, get_file_name, zipDir
from model5.togeoJSON import generate_geoJSON

router_5 = APIRouter(
    prefix="/model5",
    tags=["水旱灾害防御模型"]
)


class FileInfo(BaseModel):
    filename: str
    file_extension: str
    file_size: int


with open("config/configuration_local.yaml", 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)['model5']


@router_5.get('/get_smi')
async def flood_drought_defend_get_smi(red_tif_dir: str, nir_tif_dir: str) :
    """
    获取对应遥感图像的土壤含水量
    \n:param red_tif_dir: 红波tif路径
    \n:param nir_tif_dir: 近红外tif路径
    \n:return: geojson文件
    """
    with open("config/configuration_local.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)['model5']
    geojson_save_dir = config['geojson-save-dir']
    if not os.path.exists(geojson_save_dir):
        os.makedirs(geojson_save_dir)
    smi, data_info = nir_red_to_smi(red_tif_dir, nir_tif_dir)

    tiff_path = get_file_name(red_tif_dir)
    write_tiff_file(smi, data_info, tiff_path)

    output_geojson_path = geojson_save_dir + tiff_path.split('/')[-1].replace('.tif', '.geojson')
    success = generate_geoJSON(tiff_path, output_geojson_path)
    headers = {"Content-Disposition": f"attachment; filename={output_geojson_path.split('/')[-1]}"}
    if success:
        return FileResponse(output_geojson_path, media_type="application/geo+json", headers=headers)
    else:
        return "Error"


@router_5.get('/download_file')
async def download_file(file_path):
    if os.path.exists(file_path):
        filename = file_path.split('/')[-1]
        headers = {"Content-Disposition": f"attachment; filename={filename}"}
        return FileResponse(file_path, media_type="image/tiff", headers=headers)
    else:
        return {"error": "文件不存在"}


@router_5.get('/dynamic_smi')
def dynamic_smi(data: dict):
    """
    获取连续多个tif土壤含水量数组，以得到动态土壤水分演变
    \n:param data: 包含一个file_list数组，数组中每个json对象都是{"red_dir":"","nir_dir":""}
    \n:return: smi_list
    """
    file_list = data["file_list"]
    folder_path = get_dynamic_smi(file_list)
    output_dir = folder_path + '.zip'
    zipDir(folder_path, output_dir)
    return FileResponse(output_dir, media_type="application/zip")

@router_5.get('/get_continuous_no_rain_day')
def get_continuous_no_rain_day():
    """
    获得连续无雨日
    \n:return: 连续无语日列表和无雨天数
    """
    encoded_data = get_continuous_dry_day()
    return encoded_data


@router_5.get('/get_rain_avg_lap_rate')
def get_rain_avg_lap_rate_service(span: str, stage_inflow, date=None, history_file_dir: Optional[str] = None) -> str:
    """
    计算降雨距平指数
    \n:param span: 时间跨度['year', 'month', 'xun']
    \n:param stage_inflow: 当前阶段降雨量，单位：毫米mm
    \n:param date: 日期，默认为当前日期
    \n:return: 降雨平均指数
    """
    if date is None:
        date = dt.datetime.now()
    if type(date) == str:
        date = dt.datetime.strptime(date, "%Y-%m-%d")
    if not span in ['year', 'month', 'xun']:
        return "span输入错误"
    rate = get_rain_avg_lap_rate(span, stage_inflow, date, history_file_dir)
    return rate


@router_5.post('/upload_file')
async def upload_file(files: List[UploadFile] = File(...)):
    full_path_list = []
    for file in files:
        file_content = await file.read()  # 读取文件
        save_file = config['upload-save-dir']
        filename = file.filename
        full_path = os.path.join(save_file, filename)
        with open(full_path, "wb") as tiff:
            tiff.write(file_content)
        full_path_list.append(full_path)
    return {
        "file_path": full_path_list,
    }
