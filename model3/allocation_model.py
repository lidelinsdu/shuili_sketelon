from datetime import timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pulp
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.core.problem import ElementwiseProblem
from pymoo.factory import get_reference_directions
from pymoo.optimize import minimize

from model3.model_base import WaterResourceBase

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


class WaterResourceAllocation(WaterResourceBase):
    """水资源多目标配置模型

    基于"缺水最少、损耗最小"原则的水资源配置模型，支持年、月、旬三级配置方案
    以及"年度配置-动态调整抗旱应急"的动态调整机制
    """

    def allocate_water_yearly(self, year, tree_file, output=True):
        """生成年度水资源配置方案

        参数:
            year (int): 年份
            output (bool): 是否输出结果到文件

        返回:
            dict: 年度配置结果
        """
        print(f"正在使用LP算法生成{year}年度水资源配置方案...")

        # 提取年度数据
        start_date = pd.Timestamp(f"{year}-01-01")
        end_date = pd.Timestamp(f"{year}-12-31")

        # 确保日期在数据范围内
        if start_date < self.start_date or end_date > self.end_date:
            print(f"警告：请求的年份 {year} 部分或全部超出数据范围")
            return None

        # 提取年度供需数据
        yearly_demand = self.daily_demand.loc[start_date:end_date].sum()
        yearly_supply = self.daily_supply.loc[start_date:end_date].sum()

        # 创建优化模型
        model = pulp.LpProblem(f"Water_Allocation_{year}", pulp.LpMinimize)

        # 定义决策变量：从水源s到灌区d的配水量
        allocation = {}
        for s in self.water_sources:
            for d in self.districts:
                allocation[(s, d)] = pulp.LpVariable(f"Allocation_{s}_{d}", lowBound=0)

        # 定义缺水量变量
        shortage = {}
        for d in self.districts:
            shortage[d] = pulp.LpVariable(f"Shortage_{d}", lowBound=0)

        # 目标函数：最小化加权缺水量和损耗
        # 权重考虑：水源优先级、单位成本、灌溉效率
        objective = pulp.lpSum([
            # 缺水量部分，给予较高权重
            100 * shortage[d] for d in self.districts
        ]) + pulp.lpSum([
            # 损耗部分，考虑成本和灌溉效率
            allocation[(s, d)] * self.source_cost[s] * (1 - self.district_efficiency[d])
            for s in self.water_sources for d in self.districts
        ])

        model += objective

        # 约束条件1：每个灌区的总配水量加上缺水量等于需水量
        for d in self.districts:
            model += (
                    pulp.lpSum([allocation[(s, d)] for s in self.water_sources]) + shortage[d]
                    == yearly_demand[d]
            )

        # 约束条件2：每个水源的总配水量不超过可供水量
        for s in self.water_sources:
            model += (
                    pulp.lpSum([allocation[(s, d)] for d in self.districts])
                    <= yearly_supply[s]
            )

        # 约束条件3：按水源优先级分配，高优先级水源优先使用
        # 通过为低优先级水源添加惩罚成本实现
        for s in self.water_sources:
            for d in self.districts:
                model += allocation[(s, d)] <= yearly_supply[s] * (1 + 0.1 * (self.source_priority[s] - 1))

        # 求解模型
        model.solve(pulp.PULP_CBC_CMD(msg=False))

        # 整理结果
        result = {
            "year": year,
            "status": pulp.LpStatus[model.status],
            "objective": pulp.value(model.objective),
            "allocation": {},
            "shortage": {},
            "efficiency": {},
            "utilization": {}
        }

        # 提取分配结果
        for s in self.water_sources:
            result["allocation"][s] = {}
            for d in self.districts:
                result["allocation"][s][d] = allocation[(s, d)].value()

        # 计算每个灌区的缺水量
        for d in self.districts:
            result["shortage"][d] = shortage[d].value()

        # 计算每个灌区的实际供水量和需水满足率
        result["supply"] = {}
        result["satisfaction"] = {}
        for d in self.districts:
            result["supply"][d] = sum(result["allocation"][s][d] for s in self.water_sources)
            result["satisfaction"][d] = (result["supply"][d] / yearly_demand[d]) * 100 if yearly_demand[d] > 0 else 100

        # 计算每个水源的利用率
        for s in self.water_sources:
            result["utilization"][s] = sum(result["allocation"][s][d] for d in self.districts) / yearly_supply[
                s] * 100 if yearly_supply[s] > 0 else 0

        # 输出结果到文件
        if output:
            from output_processor import OutputProcessor
            processor = OutputProcessor(self)
            processor.output_yearly_result(result, tree_file)

        return result

    def allocate_water_monthly(self, year, month, tree_file, output=True):
        """生成月度水资源配置方案

        参数:
            year (int): 年份
            month (int): 月份
            output (bool): 是否输出结果到文件

        返回:
            dict: 月度配置结果
        """
        print(f"正在使用LP算法生成{year}年{month}月水资源配置方案...")

        # 提取月度数据范围
        start_date = pd.Timestamp(f"{year}-{month:02d}-01")
        if month == 12:
            end_date = pd.Timestamp(f"{year}-{month:02d}-31")
        else:
            end_date = pd.Timestamp(f"{year}-{month + 1:02d}-01") - timedelta(days=1)

        # 确保日期在数据范围内
        if start_date < self.start_date or end_date > self.end_date:
            print(f"警告：请求的月份 {year}-{month:02d} 部分或全部超出数据范围")
            return None

        # 提取月度供需数据
        monthly_demand = self.daily_demand.loc[start_date:end_date].sum()
        monthly_supply = self.daily_supply.loc[start_date:end_date].sum()

        # 创建优化模型
        model = pulp.LpProblem(f"Water_Allocation_{year}_{month}", pulp.LpMinimize)

        # 定义决策变量：从水源s到灌区d的配水量
        allocation = {}
        for s in self.water_sources:
            for d in self.districts:
                allocation[(s, d)] = pulp.LpVariable(f"Allocation_{s}_{d}", lowBound=0)

        # 定义缺水量变量
        shortage = {}
        for d in self.districts:
            shortage[d] = pulp.LpVariable(f"Shortage_{d}", lowBound=0)

        # 目标函数：最小化加权缺水量和损耗
        objective = pulp.lpSum([
            # 缺水量部分，给予较高权重
            100 * shortage[d] for d in self.districts
        ]) + pulp.lpSum([
            # 损耗部分，考虑成本和灌溉效率
            allocation[(s, d)] * self.source_cost[s] * (1 - self.district_efficiency[d])
            for s in self.water_sources for d in self.districts
        ])

        model += objective

        # 约束条件1：每个灌区的总配水量加上缺水量等于需水量
        for d in self.districts:
            model += (
                    pulp.lpSum([allocation[(s, d)] for s in self.water_sources]) + shortage[d]
                    == monthly_demand[d]
            )

        # 约束条件2：每个水源的总配水量不超过可供水量
        for s in self.water_sources:
            model += (
                    pulp.lpSum([allocation[(s, d)] for d in self.districts])
                    <= monthly_supply[s]
            )

        # 约束条件3：按水源优先级分配
        for s in self.water_sources:
            for d in self.districts:
                model += allocation[(s, d)] <= monthly_supply[s] * (1 + 0.1 * (self.source_priority[s] - 1))

        # 求解模型
        model.solve(pulp.PULP_CBC_CMD(msg=False))

        # 整理结果
        result = {
            "year": year,
            "month": month,
            "status": pulp.LpStatus[model.status],
            "objective": pulp.value(model.objective),
            "allocation": {},
            "shortage": {},
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }

        # 提取分配结果
        for s in self.water_sources:
            result["allocation"][s] = {}
            for d in self.districts:
                result["allocation"][s][d] = allocation[(s, d)].value()

        # 计算每个灌区的缺水量
        for d in self.districts:
            result["shortage"][d] = shortage[d].value()

        # 计算每个灌区的实际供水量和需水满足率
        result["supply"] = {}
        result["satisfaction"] = {}
        for d in self.districts:
            result["supply"][d] = sum(result["allocation"][s][d] for s in self.water_sources)
            result["satisfaction"][d] = (result["supply"][d] / monthly_demand[d]) * 100 if monthly_demand[
                                                                                               d] > 0 else 100

        # 计算每个水源的利用率
        result["utilization"] = {}
        for s in self.water_sources:
            result["utilization"][s] = sum(result["allocation"][s][d] for d in self.districts) / monthly_supply[
                s] * 100 if monthly_supply[s] > 0 else 0

        # 输出结果到文件
        if output:
            from output_processor import OutputProcessor
            processor = OutputProcessor(self)
            processor._output_monthly_result(result, tree_file)

        return result

    def allocate_water_dekad(self, year, month, dekad, tree_file, output=True):
        """生成旬水资源配置方案

        参数:
            year (int): 年份
            month (int): 月份
            dekad (int): 旬（1-上旬, 2-中旬, 3-下旬）
            output (bool): 是否输出结果到文件

        返回:
            dict: 旬配置结果
        """
        dekad_name = {1: "上旬", 2: "中旬", 3: "下旬"}[dekad]
        print(f"正在使用LP算法生成{year}年{month}月{dekad_name}水资源配置方案...")

        # 确定旬的起止日期
        if dekad == 1:  # 上旬：1-10日
            start_day = 1
            end_day = 10
        elif dekad == 2:  # 中旬：11-20日
            start_day = 11
            end_day = 20
        else:  # 下旬：21日至月底
            start_day = 21
            # 计算月底
            if month in [1, 3, 5, 7, 8, 10, 12]:
                end_day = 31
            elif month in [4, 6, 9, 11]:
                end_day = 30
            else:  # 2月
                # 处理闰年
                if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                    end_day = 29
                else:
                    end_day = 28

        # 设置起止日期
        start_date = pd.Timestamp(f"{year}-{month:02d}-{start_day:02d}")
        end_date = pd.Timestamp(f"{year}-{month:02d}-{end_day:02d}")

        # 确保日期在数据范围内
        if start_date < self.start_date or end_date > self.end_date:
            print(f"警告：请求的旬 {year}-{month:02d}-{dekad_name} 部分或全部超出数据范围")
            return None

        # 提取旬供需数据
        dekad_demand = self.daily_demand.loc[start_date:end_date].sum()
        dekad_supply = self.daily_supply.loc[start_date:end_date].sum()

        # 创建优化模型
        model = pulp.LpProblem(f"Water_Allocation_{year}_{month}_{dekad}", pulp.LpMinimize)

        # 定义决策变量：从水源s到灌区d的配水量
        allocation = {}
        for s in self.water_sources:
            for d in self.districts:
                allocation[(s, d)] = pulp.LpVariable(f"Allocation_{s}_{d}", lowBound=0)

        # 定义缺水量变量
        shortage = {}
        for d in self.districts:
            shortage[d] = pulp.LpVariable(f"Shortage_{d}", lowBound=0)

        # 目标函数：最小化加权缺水量和损耗
        objective = pulp.lpSum([
            # 缺水量部分，给予较高权重
            100 * shortage[d] for d in self.districts
        ]) + pulp.lpSum([
            # 损耗部分，考虑成本和灌溉效率
            allocation[(s, d)] * self.source_cost[s] * (1 - self.district_efficiency[d])
            for s in self.water_sources for d in self.districts
        ])

        model += objective

        # 约束条件1：每个灌区的总配水量加上缺水量等于需水量
        for d in self.districts:
            model += (
                    pulp.lpSum([allocation[(s, d)] for s in self.water_sources]) + shortage[d]
                    == dekad_demand[d]
            )

        # 约束条件2：每个水源的总配水量不超过可供水量
        for s in self.water_sources:
            model += (
                    pulp.lpSum([allocation[(s, d)] for d in self.districts])
                    <= dekad_supply[s]
            )

        # 约束条件3：按水源优先级分配
        for s in self.water_sources:
            for d in self.districts:
                model += allocation[(s, d)] <= dekad_supply[s] * (1 + 0.1 * (self.source_priority[s] - 1))

        # 求解模型
        model.solve(pulp.PULP_CBC_CMD(msg=False))

        # 整理结果
        result = {
            "year": year,
            "month": month,
            "dekad": dekad,
            "dekad_name": dekad_name,
            "status": pulp.LpStatus[model.status],
            "objective": pulp.value(model.objective),
            "allocation": {},
            "shortage": {},
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }

        # 提取分配结果
        for s in self.water_sources:
            result["allocation"][s] = {}
            for d in self.districts:
                result["allocation"][s][d] = allocation[(s, d)].value()

        # 计算每个灌区的缺水量
        for d in self.districts:
            result["shortage"][d] = shortage[d].value()

        # 计算每个灌区的实际供水量和需水满足率
        result["supply"] = {}
        result["satisfaction"] = {}
        for d in self.districts:
            result["supply"][d] = sum(result["allocation"][s][d] for s in self.water_sources)
            result["satisfaction"][d] = (result["supply"][d] / dekad_demand[d]) * 100 if dekad_demand[d] > 0 else 100

        # 计算每个水源的利用率
        result["utilization"] = {}
        for s in self.water_sources:
            result["utilization"][s] = sum(result["allocation"][s][d] for d in self.districts) / dekad_supply[
                s] * 100 if dekad_supply[s] > 0 else 0

        # 输出结果到文件
        if output:
            from output_processor import OutputProcessor
            processor = OutputProcessor(self)
            processor._output_dekad_result(result, tree_file)

        return result


class WaterResourceNSGAIII(WaterResourceBase):
    """基于NSGA-III的水资源多目标配置模型
    
    使用NSGA-III算法进行多目标优化，考虑：
    1. 最小化缺水量
    2. 最小化输水损耗
    3. 考虑水源优先级
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class WaterAllocationProblem(ElementwiseProblem):
        def __init__(self, water_sources, districts, yearly_supply, yearly_demand, source_cost, district_efficiency,
                     source_priority, source_to_parent, parent_nodes):
            """
            初始化水资源多目标分配问题
            参数说明：
                water_sources: 所有水源名称列表
                districts: 所有灌区/节点名称列表
                yearly_supply: 每个水源的年度可供水量（Series或dict）
                yearly_demand: 每个父节点的年度需水量（Series或dict）
                source_cost: 每个水源的单位水成本
                district_efficiency: 每个节点的灌溉效率
                source_priority: 每个水源的优先级
                source_to_parent: 水源到父节点的映射
                parent_nodes: 树结构中的所有父节点ID
            """
            self.water_sources = water_sources
            self.districts = districts
            self.supply = yearly_supply
            self.demand = yearly_demand
            self.source_cost = source_cost
            self.district_efficiency = district_efficiency
            self.source_priority = source_priority
            self.source_to_parent = source_to_parent
            self.parent_nodes = parent_nodes

            # 创建水源-父节点的允许分配关系（只允许水源分配给其父节点）
            self.allowed_source_parent = {}
            for s in water_sources:
                if s in self.source_to_parent:
                    parent = self.source_to_parent[s]
                    # 只有节点是父节点，才允许
                    if parent in self.parent_nodes:
                        self.allowed_source_parent[s] = parent

            # 只为允许的分配定义变量（变量索引为(source_idx, parent)）
            self.var_indices = []  # (source_idx, parent) 对的索引
            for i, s in enumerate(water_sources):
                if s in self.allowed_source_parent:
                    parent = self.allowed_source_parent[s]
                    if parent in yearly_demand.index:  # 确保父节点在需水量数据中
                        self.var_indices.append((i, parent))

            # 定义决策变量数量（每个允许的水源-父节点分配为一个变量）,也就是多少个（水源-父节点）的数量
            n_var = len(self.var_indices)

            # 每个变量的上界为对应水源的可供水量
            xu = []
            for i, s in enumerate(water_sources):
                if any(idx[0] == i for idx in self.var_indices):
                    xu.append(yearly_supply[s])

            if n_var > 0:  # 存在有效分配变量
                super().__init__(
                    n_var=n_var,  # 决策变量个数
                    n_obj=2,  # 两个目标：缺水量和损耗
                    n_constr=len(self.parent_nodes) + len(water_sources),  # 约束数=父节点数+水源数
                    xl=0.0,  # 变量下界
                    xu=np.array(xu)  # 变量上界
                )
            else:
                # 如果没有有效的分配，设置一个伪问题，防止算法报错
                super().__init__(
                    n_var=1,
                    n_obj=2,
                    n_constr=1,
                    xl=0.0,
                    xu=1.0
                )
                print("警告：没有找到有效的水源-父节点分配关系")

        def _evaluate(self, x, out, *args, **kwargs):
            # 如果没有有效的分配关系，直接返回极大目标值和不满足的约束
            if len(self.var_indices) == 0:
                out["F"] = [1e6, 1e6]  # 高缺水量和高损耗
                out["G"] = [1]  # 不满足约束
                return

            # 构建水源到父节点的分配矩阵 allocation[source][parent] = 分配量
            allocation = {}
            for idx, (source_idx, parent) in enumerate(self.var_indices):
                source = self.water_sources[source_idx]
                if source not in allocation:
                    allocation[source] = {}
                allocation[source][parent] = x[idx]

            # 计算每个父节点的总配水量
            parent_allocation = {parent: 0 for parent in self.parent_nodes if parent in self.demand.index}
            for source, parent_dict in allocation.items():
                for parent, amount in parent_dict.items():
                    if parent in parent_allocation:
                        parent_allocation[parent] += amount

            # 目标1：总缺水量（所有父节点的需水量-实际获得水量，不能为负）
            shortage = {parent: max(0, self.demand[parent] - parent_allocation.get(parent, 0))
                        for parent in self.parent_nodes if parent in self.demand.index}
            f1 = sum(shortage.values())

            # 目标2：总损耗（所有分配量*水源成本*（1-父节点效率））
            # 假设父节点有类似于灌区的效率
            parent_efficiency = {parent: self.district_efficiency.get(parent, 0.8) for parent in self.parent_nodes}

            loss = 0
            for source, parent_dict in allocation.items():
                for parent, amount in parent_dict.items():
                    # 损耗=分配量*水源成本*（1-效率）
                    loss_coefficient = self.source_cost[source] * (1 - parent_efficiency.get(parent, 0.8))
                    loss += amount * loss_coefficient

            f2 = loss

            # 约束条件：
            # 1. 每个父节点的总配水量不超过需水量（parent_allocation[parent] <= demand[parent]）
            g1 = [parent_allocation.get(parent, 0) - self.demand.get(parent, 0)
                  for parent in self.parent_nodes if parent in self.demand.index]

            # 2. 每个水源的总配水量不超过可供水量（source_usage[source] <= supply[source]）
            source_usage = {source: 0 for source in self.water_sources}
            for source, parent_dict in allocation.items():
                source_usage[source] = sum(parent_dict.values())

            g2 = [source_usage.get(source, 0) - self.supply.get(source, 0) for source in self.water_sources]

            out["F"] = [f1, f2]  # 目标函数（[总缺水量, 总损耗]）
            out["G"] = np.concatenate([g1, g2])  # 约束条件（<=0）

    def distribute_water_to_children(self, parent_allocation, demand_period, allocation=None):
        """
        根据父节点获得的水量，依照树状结构和各子节点的需水量从上至下进行水资源分配，并记录每个节点的来水和出水条目。
        
        参数:
            parent_allocation (dict): 父节点分配结果，格式为 {父节点ID: 配水量}
            demand_period: 对应时间段的需水量数据（Series或dict）
            allocation: dict, 记录水源到父节点的分配明细
        返回:
            dict: 所有节点（包括父节点和子节点）的配水量结果
        """
        print("正在根据父节点配水量向子节点分配水资源...")

        # 构建父节点到子节点的映射，便于递归分配
        parent_to_children = {}
        for idx, row in self.tree_structure.iterrows():
            parent = row['上一节点ID']
            child = row['ID']
            if pd.notna(parent):  # 忽略根节点（无父节点）
                parent_to_children.setdefault(parent, []).append(child)

        # all_node_allocation用于存储所有节点的最终分配水量
        all_node_allocation = {}
        # node_flow_records用于记录每个节点的来水（in）和出水（out）条目
        node_flow_records = {}

        # 先将父节点的分配结果添加到最终分配结果中，并初始化flow记录
        for parent, amount in parent_allocation.items():
            all_node_allocation[parent] = amount
            # 初始化flow记录结构
            if parent not in node_flow_records:
                node_flow_records[parent] = {"in": [], "out": []}
            # allocation参数必须传递
            if allocation is not None:
                for s in self.water_sources:
                    alloc = allocation.get(s, {}).get(parent, 0)
                    if alloc > 0:
                        node_flow_records[parent]["in"].append({"from": s, "amount": alloc})

        # 递归函数：将父节点的水量分配给其直接子节点
        def distribute_to_children(parent, available_water):
            # 如果该父节点没有子节点，则直接返回0
            if parent not in parent_to_children:
                return 0
            children = parent_to_children[parent]
            # 获取所有子节点的需水量
            children_demand = {}
            for child in children:
                if child in demand_period:
                    children_demand[child] = max(0, demand_period[child])
                else:
                    children_demand[child] = 0
            total_demand = sum(children_demand.values())
            if total_demand <= 0:
                # 如果总需水量为零，则所有子节点分配为0，并记录流向
                for child in children:
                    all_node_allocation[child] = 0
                    # 初始化flow记录
                    if child not in node_flow_records:
                        node_flow_records[child] = {"in": [], "out": []}
                    # 来水为0
                    node_flow_records[child]["in"].append({"from": parent, "amount": 0})
                    # 父节点出水为0
                    node_flow_records[parent]["out"].append({"to": child, "amount": 0})
                return 0
            # 创建LP模型进行优化分配
            model = pulp.LpProblem(f"Water_Distribution_{parent}", pulp.LpMinimize)
            # 定义决策变量：每个子节点获得的水量
            allocation = {}
            for child in children:
                allocation[child] = pulp.LpVariable(f"Allocation_{child}", lowBound=0)
            # 定义缺水量变量
            shortage = {}
            for child in children:
                shortage[child] = pulp.LpVariable(f"Shortage_{child}", lowBound=0)
            # 定义总分配量变量，确保不超过可用水量
            total_allocated = pulp.LpVariable(f"Total_Allocated_{parent}", lowBound=0, upBound=available_water)
            # 目标函数：最小化所有子节点的缺水量
            model += pulp.lpSum([100 * shortage[child] for child in children])
            # 约束1：所有子节点分配量之和等于总分配量，且不超过可用水量和总需水量
            model += pulp.lpSum([allocation[child] for child in children]) == total_allocated
            model += total_allocated <= min(available_water, total_demand)
            # 约束2：每个子节点的分配量+缺水量=需水量
            for child in children:
                model += allocation[child] + shortage[child] == children_demand[child]
            # 求解模型
            solver = pulp.PULP_CBC_CMD(msg=False)
            model.solve(solver)
            if model.status != pulp.LpStatusOptimal:
                # 如果无法求解，则按需水量比例分配
                print(f"警告：节点 {parent} 的分配模型无法求解，将按需水量比例分配")
                total_allocated_value = min(available_water, total_demand)
                if total_demand > 0:
                    for child in children:
                        ratio = children_demand[child] / total_demand
                        all_node_allocation[child] = total_allocated_value * ratio
                else:
                    for child in children:
                        all_node_allocation[child] = 0
                total_allocated_to_children = sum(all_node_allocation[child] for child in children)
            else:
                # 提取最优解结果
                total_allocated_value = total_allocated.value()
                total_allocated_value = min(total_allocated_value, available_water)
                total_allocated_to_children = 0
                for child in children:
                    child_allocation = allocation[child].value()
                    child_allocation = max(0, min(child_allocation, children_demand[child],
                                                  available_water - total_allocated_to_children))
                    all_node_allocation[child] = child_allocation
                    total_allocated_to_children += child_allocation
                # 检查总分配量是否与模型解一致，若不一致则修正
                if abs(total_allocated_to_children - total_allocated_value) > 1e-6:
                    print(f"警告：节点 {parent} 的分配结果与模型解不一致，将进行修正")
                    if total_allocated_to_children > 0:
                        correction_factor = total_allocated_value / total_allocated_to_children
                        for child in children:
                            all_node_allocation[child] *= correction_factor
                        total_allocated_to_children = total_allocated_value
            # 记录流向：父节点出水到子节点，子节点来水自父节点
            for child in children:
                alloc = all_node_allocation[child]
                # 初始化flow记录结构
                if parent not in node_flow_records:
                    node_flow_records[parent] = {"in": [], "out": []}
                if child not in node_flow_records:
                    node_flow_records[child] = {"in": [], "out": []}
                # 父节点出水到子节点
                node_flow_records[parent]["out"].append({"to": child, "amount": alloc})
                # 子节点来水自父节点
                node_flow_records[child]["in"].append({"from": parent, "amount": alloc})
            # 递归分配给每个子节点的下级
            remaining_water = available_water - total_allocated_to_children
            for child in children:
                child_allocated = distribute_to_children(child, all_node_allocation[child])
            # 返回本层分配给所有子节点的总水量
            return total_allocated_to_children

        # 从每个最顶层父节点开始分配
        for parent, amount in parent_allocation.items():
            total_allocated = distribute_to_children(parent, amount)
            print(f"父节点 {parent} 获得 {amount:.2f} 万m³水量，分配给子节点 {total_allocated:.2f} 万m³")
        # 保存flow记录到self，便于后续输出
        self.node_flow_records = node_flow_records
        return all_node_allocation

    def allocate_water_yearly(self, year, tree_file, output=True):
        """生成年度水资源配置方案

        参数:
            year (int): 年份
            output (bool): 是否输出结果到文件

        返回:
            dict: 年度配置结果
        """
        print(f"正在使用NSGA-III算法生成{year}年度水资源配置方案...")

        # 提取年度数据
        start_date = pd.Timestamp(f"{year}-01-01")
        end_date = pd.Timestamp(f"{year}-12-31")

        # 确保日期在数据范围内
        if start_date < self.start_date or end_date > self.end_date:
            print(f"警告：请求的年份 {year} 部分或全部超出数据范围")
            return None

        # 提取年度供需数据
        yearly_demand = self.daily_demand.loc[start_date:end_date].sum()
        yearly_supply = self.daily_supply.loc[start_date:end_date].sum()

        # 定义问题
        problem = self.WaterAllocationProblem(
            self.water_sources, self.districts, yearly_supply, yearly_demand,
            self.source_cost, self.district_efficiency, self.source_priority, self.source_to_parent, self.parent_nodes
        )

        # 创建NSGA-III算法实例
        ref_dirs = get_reference_directions("das-dennis", 2, n_partitions=12)  # 2个目标的参考方向
        algorithm = NSGA3(
            pop_size=100,
            ref_dirs=ref_dirs,
            n_offsprings=50,
            eliminate_duplicates=True
        )

        # 运行优化
        res = minimize(
            problem,
            algorithm,
            termination=('n_gen', 200),  # 迭代200代
            seed=1,
            verbose=False
        )

        # 从帕累托前沿中选择一个解（例如缺水量最小的解）
        best_idx = np.argmin(res.F[:, 0])  # 选择缺水量最小的解

        # 重建分配结果
        allocation_result = {}
        for idx, (source_idx, parent) in enumerate(problem.var_indices):
            source = self.water_sources[source_idx]
            if source not in allocation_result:
                allocation_result[source] = {}
            allocation_result[source][parent] = res.X[best_idx][idx]

        # 整理结果
        result = {
            "year": year,
            "status": "Optimal",
            "objective": {"shortage": res.F[best_idx, 0], "loss": res.F[best_idx, 1]},
            "pareto_front": res.F.tolist(),  # Add the entire Pareto front
            "allocation": allocation_result,
            "shortage": {},
            "supply": {},
            "satisfaction": {},
            "utilization": {}
        }

        # 计算父节点的供水量、缺水量和满足率
        parent_nodes = problem.parent_nodes
        parent_allocation = {}  # 存储父节点获得的总配水量
        for parent in parent_nodes:
            if parent in yearly_demand.index:
                result["supply"][parent] = sum(
                    result["allocation"].get(s, {}).get(parent, 0) for s in self.water_sources)
                parent_allocation[parent] = result["supply"][parent]
                result["shortage"][parent] = max(0, yearly_demand[parent] - result["supply"][parent])
                result["satisfaction"][parent] = (result["supply"][parent] / yearly_demand[parent]) * 100 if \
                    yearly_demand[parent] > 0 else 100

        # 计算水源利用率
        for s in self.water_sources:
            if s in result["allocation"]:
                total_allocation = sum(result["allocation"][s].values())
                result["utilization"][s] = total_allocation / yearly_supply[s] * 100 if yearly_supply[s] > 0 else 0
            else:
                result["utilization"][s] = 0

        # 向下分配到子节点
        print("开始向子节点分配水资源...")
        all_node_allocation = self.distribute_water_to_children(parent_allocation, yearly_demand, result["allocation"])
        result["node_allocation"] = all_node_allocation
        result["node_flow_records"] = self.node_flow_records
        file_dir_name = None
        if output:
            from model3.output_processor import OutputProcessor
            processor = OutputProcessor(self)
            file_dir_name = processor.output_yearly_result(result, tree_file)  # 调用年度结果输出方法

        return result, file_dir_name

    def allocate_water_monthly(self, year, month, tree_file, output=True):
        """生成月度水资源配置方案（NSGA-III优化）"""
        print(f"正在使用NSGA-III算法生成{year}年{month}月水资源配置方案...")

        start_date = pd.Timestamp(f"{year}-{month:02d}-01")
        end_date = pd.Timestamp(f"{year}-{month + 1:02d}-01") - timedelta(days=1) if month < 12 else pd.Timestamp(
            f"{year}-12-31")

        if start_date < self.start_date or end_date > self.end_date:
            print(f"警告：请求的月份 {year}-{month:02d} 部分或全部超出数据范围")
            return None

        monthly_demand = self.daily_demand.loc[start_date:end_date].sum()
        monthly_supply = self.daily_supply.loc[start_date:end_date].sum()

        # 定义问题
        problem = self.WaterAllocationProblem(
            self.water_sources, self.districts, monthly_supply, monthly_demand,
            self.source_cost, self.district_efficiency, self.source_priority, self.source_to_parent, self.parent_nodes
        )

        # 创建NSGA-III算法实例
        ref_dirs = get_reference_directions("das-dennis", 2, n_partitions=12)
        algorithm = NSGA3(pop_size=100, ref_dirs=ref_dirs, n_offsprings=50, eliminate_duplicates=True)

        # 运行优化
        res = minimize(problem, algorithm, ('n_gen', 200), seed=1, verbose=False)

        # 选择一个解
        best_idx = np.argmin(res.F[:, 0])

        # 重建分配结果
        allocation_result = {}
        for idx, (source_idx, parent) in enumerate(problem.var_indices):
            source = self.water_sources[source_idx]
            if source not in allocation_result:
                allocation_result[source] = {}
            allocation_result[source][parent] = res.X[best_idx][idx]

        # 整理结果
        result = {
            "year": year,
            "month": month,
            "status": "Optimal",
            "objective": {"shortage": res.F[best_idx, 0], "loss": res.F[best_idx, 1]},
            "pareto_front": res.F.tolist(),  # Add this
            "allocation": allocation_result,
            "shortage": {},
            "supply": {},
            "satisfaction": {},
            "utilization": {},
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }

        # 计算父节点的供水量、缺水量和满足率
        parent_nodes = problem.parent_nodes
        parent_allocation = {}  # 存储父节点获得的总配水量
        for parent in parent_nodes:
            if parent in monthly_demand.index:
                result["supply"][parent] = sum(
                    result["allocation"].get(s, {}).get(parent, 0) for s in self.water_sources)
                parent_allocation[parent] = result["supply"][parent]
                result["shortage"][parent] = max(0, monthly_demand[parent] - result["supply"][parent])
                result["satisfaction"][parent] = (result["supply"][parent] / monthly_demand[parent]) * 100 if \
                    monthly_demand[parent] > 0 else 100

        # 计算水源利用率
        for s in self.water_sources:
            if s in result["allocation"]:
                total_allocation = sum(result["allocation"][s].values())
                result["utilization"][s] = total_allocation / monthly_supply[s] * 100 if monthly_supply[s] > 0 else 0
            else:
                result["utilization"][s] = 0

        # 向下分配到子节点
        print("开始向子节点分配水资源...")
        all_node_allocation = self.distribute_water_to_children(parent_allocation, monthly_demand, result["allocation"])
        result["node_allocation"] = all_node_allocation
        result["node_flow_records"] = self.node_flow_records
        file_dir_name = None
        if output:
            from model3.output_processor import OutputProcessor
            processor = OutputProcessor(self)
            file_dir_name = processor._output_monthly_result(result, tree_file)

        return result, file_dir_name

    def allocate_water_dekad(self, year, month, dekad, tree_file, output=True):
        """生成旬水资源配置方案（NSGA-III优化）"""
        dekad_name = {1: "上旬", 2: "中旬", 3: "下旬"}[dekad]
        print(f"正在生成{year}年{month}月{dekad_name}水资源配置方案...")

        # 确定旬的起止日期
        if dekad == 1:
            start_day, end_day = 1, 10
        elif dekad == 2:
            start_day, end_day = 11, 20
        else:
            start_day = 21
            end_day = 31 if month in [1, 3, 5, 7, 8, 10, 12] else 30 if month in [4, 6, 9, 11] else 29 if (
                    (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)) else 28

        start_date = pd.Timestamp(f"{year}-{month:02d}-{start_day:02d}")
        end_date = pd.Timestamp(f"{year}-{month:02d}-{end_day:02d}")

        if start_date < self.start_date or end_date > self.end_date:
            print(f"警告：请求的旬 {year}-{month:02d}-{dekad_name} 部分或全部超出数据范围")
            return None

        dekad_demand = self.daily_demand.loc[start_date:end_date].sum()
        dekad_supply = self.daily_supply.loc[start_date:end_date].sum()

        # 定义问题
        problem = self.WaterAllocationProblem(
            self.water_sources, self.districts, dekad_supply, dekad_demand,
            self.source_cost, self.district_efficiency, self.source_priority, self.source_to_parent, self.parent_nodes
        )

        # 创建NSGA-III算法实例
        ref_dirs = get_reference_directions("das-dennis", 2, n_partitions=12)
        algorithm = NSGA3(pop_size=100, ref_dirs=ref_dirs, n_offsprings=50, eliminate_duplicates=True)

        # 运行优化
        res = minimize(problem, algorithm, ('n_gen', 200), seed=1, verbose=False)

        # 选择一个解
        best_idx = np.argmin(res.F[:, 0])

        # 重建分配结果
        allocation_result = {}
        for idx, (source_idx, parent) in enumerate(problem.var_indices):
            source = self.water_sources[source_idx]
            if source not in allocation_result:
                allocation_result[source] = {}
            allocation_result[source][parent] = res.X[best_idx][idx]

        # 整理结果
        result = {
            "year": year,
            "month": month,
            "dekad": dekad,
            "dekad_name": dekad_name,
            "status": "Optimal",
            "objective": {"shortage": res.F[best_idx, 0], "loss": res.F[best_idx, 1]},
            "pareto_front": res.F.tolist(),  # Add this
            "allocation": allocation_result,
            "shortage": {},
            "supply": {},
            "satisfaction": {},
            "utilization": {},
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }

        # 计算父节点的供水量、缺水量和满足率
        parent_nodes = problem.parent_nodes
        parent_allocation = {}  # 存储父节点获得的总配水量
        for parent in parent_nodes:
            if parent in dekad_demand.index:
                result["supply"][parent] = sum(
                    result["allocation"].get(s, {}).get(parent, 0) for s in self.water_sources)
                parent_allocation[parent] = result["supply"][parent]
                result["shortage"][parent] = max(0, dekad_demand[parent] - result["supply"][parent])
                result["satisfaction"][parent] = (result["supply"][parent] / dekad_demand[parent]) * 100 if \
                    dekad_demand[parent] > 0 else 100

        # 计算水源利用率
        for s in self.water_sources:
            if s in result["allocation"]:
                total_allocation = sum(result["allocation"][s].values())
                result["utilization"][s] = total_allocation / dekad_supply[s] * 100 if dekad_supply[s] > 0 else 0
            else:
                result["utilization"][s] = 0

        # 向下分配到子节点
        print("开始向子节点分配水资源...")
        all_node_allocation = self.distribute_water_to_children(parent_allocation, dekad_demand, result["allocation"])
        result["node_allocation"] = all_node_allocation
        result["node_flow_records"] = self.node_flow_records
        file_dir_name = None
        if output:
            from model3.output_processor import OutputProcessor
            processor = OutputProcessor(self)
            file_dir_name = processor._output_dekad_result(result, tree_file)

        return result, file_dir_name
