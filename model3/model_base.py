import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')  # 忽略所有警告，保证输出简洁

class WaterResourceBase:
    """
    水资源配置模型基础类：数据加载与处理
    主要功能：
    1. 加载水资源相关的原始数据（供水量、需水量、灌区/水源信息、树结构等）
    2. 根据节点类型和用户输入的蓄水需求，动态调整每日需水量
    3. 按照树结构递归汇总各节点的需水量
    4. 计算年、月、旬等不同时间尺度的供需水量统计数据
    """

    def __init__(self, data_file, output_folder="结果输出", storage_water_input=None):
        """
        初始化水资源配置模型基础数据

        参数:
            data_file (str): 水资源原始数据文件路径
            output_folder (str): 结果输出文件夹
            storage_water_input (dict): 用户输入的蓄水需求，格式为 {节点ID: 蓄水需求值}
        """
        self.data_file = data_file  # 原始数据文件路径
        self.output_folder = output_folder  # 结果输出文件夹
        self.storage_water_input = storage_water_input if storage_water_input else {}  # 用户输入的蓄水需求

        # 如果输出文件夹不存在，则自动创建
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # 步骤1：加载原始数据
        self._load_data()
        # 步骤2：根据节点类型和用户输入调整每日需水量
        self.update_demand_by_node_type(self.storage_water_input)
        # 步骤3：按照树结构递归汇总需水量
        self.aggregate_demand_by_tree("model3/tree1.xlsx")
        # 步骤4：读取汇总后的每日需水量，作为后续分析基础
        self.daily_demand = pd.read_excel(self.data_file, sheet_name="每日需水量_汇总", index_col=0)
        # 步骤5：计算年、月、旬等周期数据
        self._calculate_period_data()

        # 打印模型初始化信息
        print(f"模型初始化完成，成功加载 {self.data_file}")
        print(f"数据范围: {self.start_date.strftime('%Y-%m-%d')} 至 {self.end_date.strftime('%Y-%m-%d')}")
        print(f"共 {len(self.districts)} 个灌区、{len(self.water_sources)} 个水源")

    def _load_data(self):
        """
        加载原始数据文件中的各类数据表，并进行必要的预处理和结构映射。
        """
        print("正在加载水资源数据...")

        # 读取每日供水量、每日需水量、灌区信息、水源信息、水源关系、树结构定义
        self.daily_supply = pd.read_excel(self.data_file, sheet_name="每日供水量", index_col=0)
        self.daily_demand = pd.read_excel(self.data_file, sheet_name="每日需水量", index_col=0)
        self.district_info = pd.read_excel(self.data_file, sheet_name="灌区信息")
        self.source_info = pd.read_excel(self.data_file, sheet_name="水源信息")
        self.source_parent_map = pd.read_excel(self.data_file, sheet_name="水源关系")
        self.tree_structure = pd.read_excel("model3/tree1.xlsx")

        # 转换每日供水量和需水量的索引为datetime类型，便于后续时间序列处理
        self.daily_supply.index = pd.to_datetime(self.daily_supply.index)
        self.daily_demand.index = pd.to_datetime(self.daily_demand.index)

        # 获取数据的起止日期
        self.start_date = self.daily_supply.index.min()
        self.end_date = self.daily_supply.index.max()

        # 提取所有灌区和水源的名称列表
        self.districts = self.district_info["灌区名称"].tolist()
        self.water_sources = self.source_info["水源名称"].tolist()

        # 生成完整的日期序列，确保每日数据连续（缺失的日期会补NaN）
        date_range = pd.date_range(start=self.start_date, end=self.end_date, freq='D')
        self.daily_supply = self.daily_supply.reindex(date_range)
        self.daily_demand = self.daily_demand.reindex(date_range)

        # 构建水源优先级和单位成本的字典映射
        self.source_priority = dict(zip(self.source_info["水源名称"], self.source_info["优先级"]))
        self.source_cost = dict(zip(self.source_info["水源名称"], self.source_info["单位水成本(元/m³)"]))

        # 灌区灌溉效率（百分比转小数）
        self.district_efficiency = dict(zip(self.district_info["灌区名称"], self.district_info["灌溉效率(%)"] / 100))

        # 水源与父节点的映射，所有父节点ID列表
        self.source_to_parent = dict(zip(self.source_parent_map["水源名称"], self.source_parent_map["父节点ID"]))
        self.parent_nodes = self.tree_structure[self.tree_structure["是否父节点"] == 1]["ID"].tolist()

        # 节点类型和初始水量的缺失值填充，并建立ID到类型/初始水量的映射
        self.tree_structure["节点类型"] = self.tree_structure["节点类型"].fillna("闸")
        self.tree_structure["初始水量"] = self.tree_structure["初始水量"].fillna(0)
        self.node_type_map = dict(zip(self.tree_structure["ID"], self.tree_structure["节点类型"]))
        self.initial_water_map = dict(zip(self.tree_structure["ID"], self.tree_structure["初始水量"]))

    def update_demand_by_node_type(self, storage_water_input):
        """
        根据节点类型更新每日需水量：
        - 闸/泵：不变
        - 橡胶坝/水库：需水量 = 原需水量 + 蓄水需求 - 初始水量
        """
        for node in self.daily_demand.columns:
            node_type = self.node_type_map.get(node, "闸")  # 获取节点类型，默认为闸
            initial_water = self.initial_water_map.get(node, 0)  # 获取初始水量，默认为0
            storage_water = storage_water_input.get(node, 0)  # 用户输入的蓄水需求，默认为0

            # 只有橡胶坝/水库类型的节点才调整需水量
            if node_type in ["橡胶坝", "水库"]:
                adjustment = storage_water - initial_water  # 需水量调整值
                self.daily_demand[node] = self.daily_demand[node] + adjustment  # 批量调整每日需水量

    def aggregate_demand_by_tree(self, tree_file: str):
        """
        按照树结构递归汇总各节点的需水量，并将结果写入Excel文件的"每日需水量_汇总"sheet。
        """
        print(f"正在加载树结构定义文件：{tree_file}")
        tree_df = pd.read_excel(tree_file)

        # 构建子节点到父节点、父节点到子节点的映射关系
        child_to_parent = dict(zip(tree_df['ID'], tree_df['上一节点ID']))
        all_nodes = set(tree_df['ID'])

        parent_to_children = {}
        for idx, row in tree_df.iterrows():
            parent = row['上一节点ID']
            child = row['ID']
            if pd.notna(parent):
                parent_to_children.setdefault(parent, []).append(child)

        aggregated = {}  # 存储每个节点的汇总需水量
        def post_order_sum(node):
            # 递归后序遍历，先加子节点，再加自身
            if node in self.daily_demand.columns:
                total = self.daily_demand[node].copy()
            else:
                total = pd.Series(0, index=self.daily_demand.index)
            for child in parent_to_children.get(node, []):
                total += post_order_sum(child)
            aggregated[node] = total
            return total

        print("开始进行树结构遍历与需水量汇总...")
        # 找到所有根节点（没有父节点的节点）
        root_nodes = [node for node in all_nodes if pd.isna(child_to_parent.get(node))]
        for root in root_nodes:
            post_order_sum(root)

        # 汇总结果写回 self.daily_demand
        for node, series in aggregated.items():
            self.daily_demand[node] = series

        print("汇总完成。")

        # 汇总结果保存到 Excel 文件的"每日需水量_汇总"sheet
        output_path = self.data_file
        sheet_name = "每日需水量_汇总"
        aggregated_df = pd.DataFrame(aggregated, index=self.daily_demand.index)
        aggregated_df.index = pd.to_datetime(aggregated_df.index)

        with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            aggregated_df.to_excel(writer, sheet_name=sheet_name, index=True)

        print(f"汇总数据已保存至 {output_path} 的 '{sheet_name}' sheet，列名为节点名称。")

    def _calculate_period_data(self):
        """
        计算年、月、旬等不同时间尺度的供需水量统计数据。
        """
        self.yearly_supply = self.daily_supply.resample('Y').sum()  # 年度供水量
        self.yearly_demand = self.daily_demand.resample('Y').sum()  # 年度需水量
        self.monthly_supply = self.daily_supply.resample('M').sum()  # 月度供水量
        self.monthly_demand = self.daily_demand.resample('M').sum()  # 月度需水量
        self._calculate_dekad_data()  # 旬统计

    def _calculate_dekad_data(self):
        """
        计算旬（上旬、中旬、下旬）供需水量统计。
        """
        def get_dekad(date):
            # 根据日期判断属于上旬、中旬还是下旬
            if date.day <= 10:
                return f"{date.year}-{date.month:02d}-上旬"
            elif date.day <= 20:
                return f"{date.year}-{date.month:02d}-中旬"
            else:
                return f"{date.year}-{date.month:02d}-下旬"

        dekad_labels = self.daily_supply.index.map(get_dekad)  # 为每一天打上旬标签
        self.dekad_supply = self.daily_supply.groupby(dekad_labels).sum()  # 按旬统计供水量
        self.dekad_demand = self.daily_demand.groupby(dekad_labels).sum()  # 按旬统计需水量

if __name__ == "__main__":
    # 示例：用户输入的蓄水需求（可根据实际情况修改）
    storage_water_input = {
        "N5": 10,
        "A2": 25,
        # 可添加更多节点需求
    }
    # 实例化模型，自动完成数据加载、调整和统计
    model = WaterResourceBase("data1.xlsx", storage_water_input=storage_water_input)
    print(f"调度方案已生成")
