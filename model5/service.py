from fastapi import APIRouter

from model5.algorithm import nir_red_to_smi, plot_heatmap, get_dynamic_smi

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
    return


@router_5.get('/draw_heatmap')
def draw_heatmap(smi_2d_data):
    """
    绘制热度图
    :param smi_2d_data: 土壤含水量数组
    :return: 热度图文件保存路径
    """
    return plot_heatmap(smi_2d_data)


@router_5.get('/dynamic_smi')
def dynamic_smi(file_list):
    """
    获取连续多个tif土壤含水量数组，以得到动态土壤水分演变
    :param file_list: json数组，每个json对象都是{"red_dir":"","nir_dir":""}
    :return: smi_list
    """
    return get_dynamic_smi(file_list)