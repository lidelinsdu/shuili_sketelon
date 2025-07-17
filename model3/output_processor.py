import os

# 在output_processor.py文件开头添加
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams['font.family'] = 'SimHei'  # 设置字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 处理负号显示

class OutputProcessor:
    """水资源配置结果输出处理与可视化模块"""

    def __init__(self, model):
        self.model = model
        self.output_folder = model.output_folder

        # 访问模型的属性
        self.districts = model.districts
        self.water_sources = model.water_sources
        self.source_priority = model.source_priority
        self.source_cost = model.source_cost
        self.district_efficiency = model.district_efficiency
        self.daily_supply = model.daily_supply
        self.daily_demand = model.daily_demand
        self.yearly_supply = model.yearly_supply
        self.yearly_demand = model.yearly_demand

    def output_yearly_result(self, result):
        """输出年度水资源配置结果到文件"""
        year = result["year"]
        output_dir = os.path.join(self.output_folder, f"{year}年")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 从树结构定义获取父节点列表
        tree_df = pd.read_excel("model3/tree1.xlsx")
        parent_nodes = tree_df[tree_df["是否父节点"] == 1]["ID"].tolist()
        
        # 构建节点与其父节点的映射
        child_to_parent = dict(zip(tree_df['ID'], tree_df['上一节点ID']))

        # 创建结果DataFrame - 水源到父节点的分配
        allocation_data = []
        for s in self.water_sources:
            if s in result["allocation"]:
                for parent, value in result["allocation"][s].items():
                    allocation_value = float(value) if value is not None else 0.0
                    allocation_data.append({
                        "水源": s,
                        "父节点": parent,
                        "配水量(万m³)": round(allocation_value, 2)
                    })

        allocation_df = pd.DataFrame(allocation_data)
        
        # 创建节点统计信息DataFrame - 包含所有节点（父节点和子节点）
        node_data = []
        
        # 如果有节点分配结果，处理所有节点
        if "node_allocation" in result:
            all_nodes = result["node_allocation"].keys()
            for node in all_nodes:
                # 获取父节点（如果有）
                parent = child_to_parent.get(node)
                parent_name = parent if pd.notna(parent) else "无"
                
                # 判断是否为父节点
                is_parent = 1 if node in parent_nodes else 0
                
                # 获取节点分配的水量
                allocation_value = result["node_allocation"].get(node, 0)
                allocation_value = float(allocation_value) if allocation_value is not None else 0.0
                
                # 获取需水量、缺水量和满足率（父节点在result中，子节点需计算）
                if node in parent_nodes and node in result["supply"]:
                    demand_value = self.yearly_demand.loc[f"{year}"].get(node, 0)
                    supply_value = result["supply"].get(node, 0)
                    shortage_value = result["shortage"].get(node, 0)
                    satisfaction_value = result["satisfaction"].get(node, 0)
                else:
                    # 子节点需求和缺水量计算
                    demand_value = self.yearly_demand.loc[f"{year}"].get(node, 0)
                    demand_value = float(demand_value) if demand_value is not None else 0.0
                    supply_value = allocation_value
                    shortage_value = max(0, demand_value - supply_value)
                    satisfaction_value = (supply_value / demand_value) * 100 if demand_value > 0 else 100
                
                # 获取效率
                efficiency_value = self.district_efficiency.get(node, 0.8)
                
                # 确保所有值为Python标量
                demand_value = float(demand_value) if demand_value is not None else 0.0
                supply_value = float(supply_value) if supply_value is not None else 0.0
                shortage_value = float(shortage_value) if shortage_value is not None else 0.0
                satisfaction_value = float(satisfaction_value) if satisfaction_value is not None else 0.0
                efficiency_value = float(efficiency_value) if efficiency_value is not None else 0.0
                
                node_data.append({
                    "节点ID": node,
                    "父节点": parent_name,
                    "是否父节点": is_parent,
                    "总需水量(万m³)": round(demand_value, 2),
                    "实际供水量(万m³)": round(supply_value, 2),
                    "缺水量(万m³)": round(shortage_value, 2),
                    "需水满足率(%)": round(satisfaction_value, 2),
                    "效率(%)": round(efficiency_value * 100, 2)
                })
            
            # 按照是否为父节点和节点ID排序
            node_df = pd.DataFrame(node_data)
            node_df = node_df.sort_values(by=["是否父节点", "节点ID"], ascending=[False, True])
        else:
            # 仅显示父节点统计信息
            for parent in parent_nodes:
                if parent in result["supply"]:
                    demand_value = self.yearly_demand.loc[f"{year}"].get(parent, 0)
                    supply_value = result["supply"].get(parent, 0)
                    shortage_value = result["shortage"].get(parent, 0)
                    satisfaction_value = result["satisfaction"].get(parent, 0)
                    
                    # 假设父节点有效率
                    efficiency_value = self.district_efficiency.get(parent, 0.8)

                    # Convert to Python scalars
                    demand_value = float(demand_value) if demand_value is not None else 0.0
                    supply_value = float(supply_value) if supply_value is not None else 0.0
                    shortage_value = float(shortage_value) if shortage_value is not None else 0.0
                    satisfaction_value = float(satisfaction_value) if satisfaction_value is not None else 0.0
                    efficiency_value = float(efficiency_value) if efficiency_value is not None else 0.0

                    node_data.append({
                        "节点ID": parent,
                        "父节点": "无",
                        "是否父节点": 1,
                        "总需水量(万m³)": round(demand_value, 2),
                        "实际供水量(万m³)": round(supply_value, 2),
                        "缺水量(万m³)": round(shortage_value, 2),
                        "需水满足率(%)": round(satisfaction_value, 2),
                        "效率(%)": round(efficiency_value * 100, 2)
                    })
            
            node_df = pd.DataFrame(node_data)

        # 创建水源统计信息DataFrame
        source_data = []
        for s in self.water_sources:
            supply_value = self.yearly_supply.loc[f"{year}"].get(s, 0)
            allocation_sum = 0
            if s in result["allocation"]:
                allocation_sum = sum(float(v) if v is not None else 0.0 for v in result["allocation"][s].values())
            utilization_value = result["utilization"].get(s, 0)
            priority_value = self.source_priority[s]
            cost_value = self.source_cost[s]

            # Convert to Python scalars
            supply_value = float(supply_value) if supply_value is not None else 0.0
            utilization_value = float(utilization_value) if utilization_value is not None else 0.0
            priority_value = int(priority_value) if priority_value is not None else 0
            cost_value = float(cost_value) if cost_value is not None else 0.0

            source_data.append({
                "水源": s,
                "总可供水量(万m³)": round(supply_value, 2),
                "实际供水量(万m³)": round(allocation_sum, 2),
                "利用率(%)": round(utilization_value, 2),
                "优先级": priority_value,
                "单位成本(元/m³)": round(cost_value, 2)
            })

        source_df = pd.DataFrame(source_data)

        # 创建水源条目信息DataFrame
        flow_rows = []
        # 遍历每个节点的水流记录
        for node, flows in result["node_flow_records"].items():
            # 处理入水条目（即该节点的来水）
            for entry in flows.get("in", []):
                # 记录：节点ID、类型（入水）、对方节点（来源）、水量
                flow_rows.append({"节点ID": node, "类型": "入水", "对方节点": entry["from"],
                                  "水量(万m³)": round(entry["amount"], 2)})
            # 处理出水条目（即该节点的去水）
            for entry in flows.get("out", []):
                # 记录：节点ID、类型（出水）、对方节点（去向）、水量
                flow_rows.append(
                    {"节点ID": node, "类型": "出水", "对方节点": entry["to"], "水量(万m³)": round(entry["amount"], 2)})
        # 汇总为DataFrame
        flow_df = pd.DataFrame(flow_rows)
        # 写入Excel新sheet

        # 保存到Excel
        file_list = []
        output_file = os.path.join(output_dir, f"{year}年度水资源配置方案.xlsx")
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            allocation_df.to_excel(writer, sheet_name="水源到父节点配水详情", index=False)
            node_df.to_excel(writer, sheet_name="节点统计信息", index=False)
            source_df.to_excel(writer, sheet_name="水源统计信息", index=False)
            flow_df.to_excel(writer, sheet_name="节点水流条目明细", index=False)

        print(f"已保存{year}年度水资源配置方案至 {output_file}")

        # 创建配水量可视化图表
        self._plot_allocation_chart(result, output_dir, f"{year}年度水资源配置")

        sankey_file = None
        # 如果有节点分配结果，创建节点分配树状图
        if "node_allocation" in result:
            sankey_file = self._plot_node_allocation_tree(result, output_dir, f"{year}年度节点分配")
        file_list.append(output_file)
        file_list.append(sankey_file)
        return file_list

    def _output_monthly_result(self, result):
        """输出月度水资源配置结果到文件"""
        year = result["year"]
        month = result["month"]
        output_dir = os.path.join(self.output_folder, f"{year}年", f"{month}月")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 从树结构定义获取父节点列表
        tree_df = pd.read_excel("model3/tree1.xlsx")
        parent_nodes = tree_df[tree_df["是否父节点"] == 1]["ID"].tolist()
        
        # 构建节点与其父节点的映射
        child_to_parent = dict(zip(tree_df['ID'], tree_df['上一节点ID']))

        # 创建结果DataFrame - 水源到父节点的分配
        allocation_data = []
        for s in self.water_sources:
            if s in result["allocation"]:
                for parent, value in result["allocation"][s].items():
                    allocation_value = float(value) if value is not None else 0.0
                    allocation_data.append({
                        "水源": s,
                        "父节点": parent,
                        "配水量(万m³)": round(allocation_value, 2)
                    })

        allocation_df = pd.DataFrame(allocation_data)
        
        # 提取月度供需数据
        start_date = pd.to_datetime(result["start_date"])
        end_date = pd.to_datetime(result["end_date"])
        monthly_demand = self.daily_demand.loc[start_date:end_date].sum()
        monthly_supply = self.daily_supply.loc[start_date:end_date].sum()
        
        # 创建节点统计信息DataFrame - 包含所有节点（父节点和子节点）
        node_data = []
        
        # 如果有节点分配结果，处理所有节点
        if "node_allocation" in result:
            all_nodes = result["node_allocation"].keys()
            for node in all_nodes:
                # 获取父节点（如果有）
                parent = child_to_parent.get(node)
                parent_name = parent if pd.notna(parent) else "无"
                
                # 判断是否为父节点
                is_parent = 1 if node in parent_nodes else 0
                
                # 获取节点分配的水量
                allocation_value = result["node_allocation"].get(node, 0)
                allocation_value = float(allocation_value) if allocation_value is not None else 0.0
                
                # 获取需水量、缺水量和满足率（父节点在result中，子节点需计算）
                if node in parent_nodes and node in result["supply"]:
                    demand_value = monthly_demand.get(node, 0)
                    supply_value = result["supply"].get(node, 0)
                    shortage_value = result["shortage"].get(node, 0)
                    satisfaction_value = result["satisfaction"].get(node, 0)
                else:
                    # 子节点需求和缺水量计算
                    demand_value = monthly_demand.get(node, 0)
                    demand_value = float(demand_value) if demand_value is not None else 0.0
                    supply_value = allocation_value
                    shortage_value = max(0, demand_value - supply_value)
                    satisfaction_value = (supply_value / demand_value) * 100 if demand_value > 0 else 100
                
                # 获取效率
                efficiency_value = self.district_efficiency.get(node, 0.8)
                
                node_data.append({
                    "节点ID": node,
                    "父节点": parent_name,
                    "是否父节点": is_parent,
                    "总需水量(万m³)": round(demand_value, 2),
                    "实际供水量(万m³)": round(supply_value, 2),
                    "缺水量(万m³)": round(shortage_value, 2),
                    "需水满足率(%)": round(satisfaction_value, 2),
                    "效率(%)": round(efficiency_value * 100, 2)
                })
            
            # 按照是否为父节点和节点ID排序
            node_df = pd.DataFrame(node_data)
            node_df = node_df.sort_values(by=["是否父节点", "节点ID"], ascending=[False, True])
        else:
            # 仅显示父节点统计信息
            for parent in parent_nodes:
                if parent in result["supply"]:
                    node_data.append({
                        "节点ID": parent,
                        "父节点": "无",
                        "是否父节点": 1,
                        "总需水量(万m³)": round(monthly_demand.get(parent, 0), 2),
                        "实际供水量(万m³)": round(result["supply"].get(parent, 0), 2),
                        "缺水量(万m³)": round(result["shortage"].get(parent, 0), 2),
                        "需水满足率(%)": round(result["satisfaction"].get(parent, 0), 2),
                        "效率(%)": round(self.district_efficiency.get(parent, 0.8) * 100, 2)
                    })
            
            node_df = pd.DataFrame(node_data)

        # 创建水源统计信息DataFrame
        source_data = []
        for s in self.water_sources:
            allocation_sum = 0
            if s in result["allocation"]:
                allocation_sum = sum(result["allocation"][s].values())
                
            source_data.append({
                "水源": s,
                "总可供水量(万m³)": round(monthly_supply.get(s, 0), 2),
                "实际供水量(万m³)": round(allocation_sum, 2),
                "利用率(%)": round(result["utilization"].get(s, 0), 2),
                "优先级": self.source_priority[s],
                "单位成本(元/m³)": self.source_cost[s]
            })

        source_df = pd.DataFrame(source_data)
        file_list = []
        # 保存到Excel
        output_file = os.path.join(output_dir, f"{year}年{month}月水资源配置方案.xlsx")
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            allocation_df.to_excel(writer, sheet_name="水源到父节点配水详情", index=False)
            node_df.to_excel(writer, sheet_name="节点统计信息", index=False)
            source_df.to_excel(writer, sheet_name="水源统计信息", index=False)
            # 添加配置方案信息
            info_df = pd.DataFrame([{
                "开始日期": result["start_date"],
                "结束日期": result["end_date"],
                "状态": result["status"],
                #"目标函数值": round(result["objective"], 2)
            }])
            info_df.to_excel(writer, sheet_name="配置信息", index=False)
            # 新增：节点水流明细
            # 如果结果中包含节点水流记录，则生成节点水流明细表
            # 结构为：每个节点的所有入水（from）和出水（to）条目，分别记录
            if "node_flow_records" in result:
                # 用于存放所有节点的水流明细条目
                flow_rows = []
                # 遍历每个节点的水流记录
                for node, flows in result["node_flow_records"].items():
                    # 处理入水条目（即该节点的来水）
                    for entry in flows.get("in", []):
                        # 记录：节点ID、类型（入水）、对方节点（来源）、水量
                        flow_rows.append({"节点ID": node, "类型": "入水", "对方节点": entry["from"], "水量(万m³)": round(entry["amount"], 2)})
                    # 处理出水条目（即该节点的去水）
                    for entry in flows.get("out", []):
                        # 记录：节点ID、类型（出水）、对方节点（去向）、水量
                        flow_rows.append({"节点ID": node, "类型": "出水", "对方节点": entry["to"], "水量(万m³)": round(entry["amount"], 2)})
                # 汇总为DataFrame
                flow_df = pd.DataFrame(flow_rows)
                # 写入Excel新sheet
                flow_df.to_excel(writer, sheet_name="节点水流明细", index=False)

        print(f"已保存{year}年{month}月水资源配置方案至 {output_file}")

        # 创建配水量可视化图表
        self._plot_allocation_chart(result, output_dir, f"{year}年{month}月水资源配置")
        sankey_file = None
        # 如果有节点分配结果，创建节点分配树状图
        if "node_allocation" in result:
            sankey_file = self._plot_node_allocation_tree(result, output_dir, f"{year}年{month}月节点分配")
        file_list.append(output_file)
        file_list.append(sankey_file)
        return file_list

    def _output_dekad_result(self, result):
        """输出旬水资源配置结果到文件"""
        year = result["year"]
        month = result["month"]
        dekad_name = result["dekad_name"]
        output_dir = os.path.join(self.output_folder, f"{year}年", f"{month}月")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 从树结构定义获取父节点列表
        tree_df = pd.read_excel("model3/tree1.xlsx")
        parent_nodes = tree_df[tree_df["是否父节点"] == 1]["ID"].tolist()
        
        # 构建节点与其父节点的映射
        child_to_parent = dict(zip(tree_df['ID'], tree_df['上一节点ID']))

        # 创建结果DataFrame - 水源到父节点的分配
        allocation_data = []
        for s in self.water_sources:
            if s in result["allocation"]:
                for parent, value in result["allocation"][s].items():
                    allocation_value = float(value) if value is not None else 0.0
                    allocation_data.append({
                        "水源": s,
                        "父节点": parent,
                        "配水量(万m³)": round(allocation_value, 2)
                    })

        allocation_df = pd.DataFrame(allocation_data)
        
        # 提取旬供需数据
        start_date = pd.to_datetime(result["start_date"])
        end_date = pd.to_datetime(result["end_date"])
        dekad_demand = self.daily_demand.loc[start_date:end_date].sum()
        dekad_supply = self.daily_supply.loc[start_date:end_date].sum()
        
        # 创建节点统计信息DataFrame - 包含所有节点（父节点和子节点）
        node_data = []
        
        # 如果有节点分配结果，处理所有节点
        if "node_allocation" in result:
            all_nodes = result["node_allocation"].keys()
            for node in all_nodes:
                # 获取父节点（如果有）
                parent = child_to_parent.get(node)
                parent_name = parent if pd.notna(parent) else "无"
                
                # 判断是否为父节点
                is_parent = 1 if node in parent_nodes else 0
                
                # 获取节点分配的水量
                allocation_value = result["node_allocation"].get(node, 0)
                allocation_value = float(allocation_value) if allocation_value is not None else 0.0
                
                # 获取需水量、缺水量和满足率（父节点在result中，子节点需计算）
                if node in parent_nodes and node in result["supply"]:
                    demand_value = dekad_demand.get(node, 0)
                    supply_value = result["supply"].get(node, 0)
                    shortage_value = result["shortage"].get(node, 0)
                    satisfaction_value = result["satisfaction"].get(node, 0)
                else:
                    # 子节点需求和缺水量计算
                    demand_value = dekad_demand.get(node, 0)
                    demand_value = float(demand_value) if demand_value is not None else 0.0
                    supply_value = allocation_value
                    shortage_value = max(0, demand_value - supply_value)
                    satisfaction_value = (supply_value / demand_value) * 100 if demand_value > 0 else 100
                
                # 获取效率
                efficiency_value = self.district_efficiency.get(node, 0.8)
                
                node_data.append({
                    "节点ID": node,
                    "父节点": parent_name,
                    "是否父节点": is_parent,
                    "总需水量(万m³)": round(demand_value, 2),
                    "实际供水量(万m³)": round(supply_value, 2),
                    "缺水量(万m³)": round(shortage_value, 2),
                    "需水满足率(%)": round(satisfaction_value, 2),
                    "效率(%)": round(efficiency_value * 100, 2)
                })
            
            # 按照是否为父节点和节点ID排序
            node_df = pd.DataFrame(node_data)
            node_df = node_df.sort_values(by=["是否父节点", "节点ID"], ascending=[False, True])
        else:
            # 仅显示父节点统计信息
            for parent in parent_nodes:
                if parent in result["supply"]:
                    node_data.append({
                        "节点ID": parent,
                        "父节点": "无",
                        "是否父节点": 1,
                        "总需水量(万m³)": round(dekad_demand.get(parent, 0), 2),
                        "实际供水量(万m³)": round(result["supply"].get(parent, 0), 2),
                        "缺水量(万m³)": round(result["shortage"].get(parent, 0), 2),
                        "需水满足率(%)": round(result["satisfaction"].get(parent, 0), 2),
                        "效率(%)": round(self.district_efficiency.get(parent, 0.8) * 100, 2)
                    })
            
            node_df = pd.DataFrame(node_data)

        # 创建水源统计信息DataFrame
        source_data = []
        for s in self.water_sources:
            allocation_sum = 0
            if s in result["allocation"]:
                allocation_sum = sum(result["allocation"][s].values())
                
            source_data.append({
                "水源": s,
                "总可供水量(万m³)": round(dekad_supply.get(s, 0), 2),
                "实际供水量(万m³)": round(allocation_sum, 2),
                "利用率(%)": round(result["utilization"].get(s, 0), 2),
                "优先级": self.source_priority[s],
                "单位成本(元/m³)": self.source_cost[s]
            })

        source_df = pd.DataFrame(source_data)

        file_list = []
        # 保存到Excel
        output_file = os.path.join(output_dir, f"{year}年{month}月{dekad_name}水资源配置方案.xlsx")
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            allocation_df.to_excel(writer, sheet_name="水源到父节点配水详情", index=False)
            node_df.to_excel(writer, sheet_name="节点统计信息", index=False)
            source_df.to_excel(writer, sheet_name="水源统计信息", index=False)

            # 添加配置方案信息
            info_df = pd.DataFrame([{
                "开始日期": result["start_date"],
                "结束日期": result["end_date"],
                "状态": result["status"],
                "干旱等级": result.get("drought_level", "正常")
            }])
            info_df.to_excel(writer, sheet_name="配置信息", index=False)
            # 新增：节点水流明细
            # 如果结果中包含节点水流记录，则生成节点水流明细表
            # 结构为：每个节点的所有入水（from）和出水（to）条目，分别记录
            if "node_flow_records" in result:
                # 用于存放所有节点的水流明细条目
                flow_rows = []
                # 遍历每个节点的水流记录
                for node, flows in result["node_flow_records"].items():
                    # 处理入水条目（即该节点的来水）
                    for entry in flows.get("in", []):
                        # 记录：节点ID、类型（入水）、对方节点（来源）、水量
                        flow_rows.append({"节点ID": node, "类型": "入水", "对方节点": entry["from"], "水量(万m³)": round(entry["amount"], 2)})
                    # 处理出水条目（即该节点的去水）
                    for entry in flows.get("out", []):
                        # 记录：节点ID、类型（出水）、对方节点（去向）、水量
                        flow_rows.append({"节点ID": node, "类型": "出水", "对方节点": entry["to"], "水量(万m³)": round(entry["amount"], 2)})
                # 汇总为DataFrame
                flow_df = pd.DataFrame(flow_rows)
                # 写入Excel新sheet
                flow_df.to_excel(writer, sheet_name="节点水流明细", index=False)

        print(f"已保存{year}年{month}月{dekad_name}水资源配置方案至 {output_file}")

        # 创建配水量可视化图表
        self._plot_allocation_chart(result, output_dir, f"{year}年{month}月{dekad_name}水资源配置")
        sankey_file = None
        # 如果有节点分配结果，创建节点分配树状图
        if "node_allocation" in result:
            sankey_file = self._plot_node_allocation_tree(result, output_dir, f"{year}年{month}月{dekad_name}节点分配")
        file_list.append(output_file)
        file_list.append(sankey_file)
        return file_list

    def _plot_allocation_chart(self, result, output_dir, title):
        """创建配水量可视化图表"""
        plt.figure(figsize=(14, 10))
        
        # 从树结构定义获取父节点列表
        tree_df = pd.read_excel("model3/tree1.xlsx")
        parent_nodes = tree_df[tree_df["是否父节点"] == 1]["ID"].tolist()

        # 1. 创建父节点需水量与实际供水量对比图
        plt.subplot(2, 2, 1)
        nodes = []
        demand_values = []
        supply_values = []

        if "year" in result and "month" not in result:
            # 年度配置
            year = result["year"]
            for parent in parent_nodes:
                if parent in result["supply"]:
                    nodes.append(parent)
                    demand_value = self.yearly_demand.loc[f"{year}"].get(parent, 0)
                    demand_values.append(float(demand_value) if demand_value is not None else 0.0)
                    supply_value = result["supply"].get(parent, 0)
                    # Convert to Python float
                    supply_values.append(float(supply_value) if supply_value is not None else 0.0)
        elif "start_date" in result and "end_date" in result:
            # 月度、旬或应急配置
            start = pd.to_datetime(result["start_date"])
            end = pd.to_datetime(result["end_date"])
            period_demand = self.daily_demand.loc[start:end].sum()

            for parent in parent_nodes:
                if parent in result["supply"]:
                    nodes.append(parent)
                    demand_value = period_demand.get(parent, 0)
                    # Convert to Python float
                    demand_values.append(float(demand_value) if demand_value is not None else 0.0)
                    supply_value = result["supply"].get(parent, 0)
                    # Convert to Python float
                    supply_values.append(float(supply_value) if supply_value is not None else 0.0)

        x = range(len(nodes))
        plt.bar(x, demand_values, width=0.4, label="需水量", color="skyblue", alpha=0.8)
        plt.bar([i + 0.4 for i in x], supply_values, width=0.4, label="实际供水量", color="orange", alpha=0.8)

        plt.xlabel("节点")
        plt.ylabel("水量(万m³)")
        plt.title("节点需水量与实际供水量对比")
        plt.xticks([i + 0.2 for i in x], nodes)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # 2. 创建水源利用率饼图
        plt.subplot(2, 2, 2)
        sources = []
        usage_values = []

        for s in self.water_sources:
            if s in result["allocation"] and sum(result["allocation"][s].values()) > 0:
                sources.append(s)
                usage_sum = sum(result["allocation"][s].values())
                usage_values.append(usage_sum)

        if usage_values:  # 确保有数据
            plt.pie(usage_values, labels=sources, autopct='%1.1f%%', startangle=90, shadow=True)
            plt.axis('equal')
            plt.title("各水源配水量占比")
        else:
            plt.text(0.5, 0.5, "无配水数据", ha='center', va='center')
            plt.axis('off')
            plt.title("各水源配水量占比")

        # 3. 创建需水满足率柱状图
        plt.subplot(2, 2, 3)
        satisfaction_values = [result["satisfaction"].get(node, 0) for node in nodes]

        plt.bar(x, satisfaction_values, color="green", alpha=0.7)
        plt.axhline(y=100, color='r', linestyle='-', alpha=0.5)
        plt.xlabel("节点")
        plt.ylabel("满足率(%)")
        plt.title("节点需水满足率")
        plt.xticks(x, nodes)
        plt.ylim(0, max(110, max(satisfaction_values) * 1.1) if satisfaction_values else 110)
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # 4. 创建各水源到各父节点的配水量堆叠图
        plt.subplot(2, 2, 4)
        bottom = np.zeros(len(nodes))

        for s in self.water_sources:
            if s in result["allocation"]:
                values = [result["allocation"][s].get(node, 0) for node in nodes]
                plt.bar(x, values, bottom=bottom, label=s, alpha=0.7)
                bottom += np.array(values)

        plt.xlabel("节点")
        plt.ylabel("配水量(万m³)")
        plt.title("各节点的水源构成")
        plt.xticks(x, nodes)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # 设置总标题
        plt.suptitle(title, fontsize=16)
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        # 保存图表
        file_name = title.replace(" ", "_").replace(":", "").replace("-", "_").replace("(", "").replace(")", "")
        output_file = os.path.join(output_dir, f"{file_name}.png")
        plt.savefig(output_file, dpi=300)
        plt.close()

        print(f"已保存可视化图表至 {output_file}")

    def _plot_node_allocation_tree(self, result, output_dir, title):
        """创建节点分配树状图
        
        使用networkx和matplotlib库创建树状图，显示水资源从父节点到子节点的分配情况
        """
        try:
            import networkx as nx
            
            # 从树结构定义获取节点关系
            tree_df = pd.read_excel("model3/tree1.xlsx")
            
            # 构建父节点到子节点的映射
            parent_to_children = {}
            for idx, row in tree_df.iterrows():
                parent = row['上一节点ID']
                child = row['ID']
                if pd.notna(parent):  # 忽略根节点（无父节点）
                    parent_to_children.setdefault(parent, []).append(child)
            
            # 构建节点与其父节点的映射
            child_to_parent = dict(zip(tree_df['ID'], tree_df['上一节点ID']))
            
            # 获取所有根节点（没有父节点的节点）
            root_nodes = [row['ID'] for idx, row in tree_df.iterrows() if pd.isna(row['上一节点ID'])]
            
            # 创建有向图
            G = nx.DiGraph()
            
            # 添加节点和边
            node_allocations = result["node_allocation"]
            for node, value in node_allocations.items():
                # 添加节点，并设置属性
                G.add_node(node, 
                           allocation=round(float(value) if value is not None else 0.0, 2),
                           is_parent=1 if node in parent_to_children else 0)
            
            # 添加边并计算边的权重（水量传输量）
            edge_flows = {}
            for child, parent in child_to_parent.items():
                if pd.notna(parent) and child in G.nodes and parent in G.nodes:
                    # 边的权重为子节点分配到的水量
                    flow = G.nodes[child]["allocation"]
                    G.add_edge(parent, child, flow=flow)
                    edge_flows[(parent, child)] = flow
            
            # 为每个根节点创建一个子图
            fig = plt.figure(figsize=(16, 12))
            
            # 如果树很复杂，可能需要多个图来展示
            for i, root in enumerate(root_nodes):
                if root not in G.nodes:
                    continue
                    
                # 获取以root为根的子树
                subtree_nodes = [root] + list(nx.descendants(G, root))
                subtree = G.subgraph(subtree_nodes)
                
                # 计算节点位置（使用分层布局）
                try:
                    pos = nx.drawing.nx_agraph.graphviz_layout(subtree, prog='dot')
                except:
                    # 如果graphviz不可用，使用内置布局算法
                    pos = nx.spring_layout(subtree, seed=42)
                
                # 创建子图
                ax = plt.subplot(1, len(root_nodes), i+1)
                
                # 绘制节点 - 水量较多的节点绘制为更大的圆
                node_sizes = [300 + 200 * G.nodes[n]["allocation"] for n in subtree.nodes()]
                node_colors = ['#ff9999' if G.nodes[n]['is_parent'] else '#99ccff' for n in subtree.nodes()]
                nx.draw_networkx_nodes(subtree, pos, node_size=node_sizes, node_color=node_colors, alpha=0.8)
                
                # 绘制边 - 水量较多的边绘制为更粗的线
                edge_widths = [1 + 2 * G.edges[edge]["flow"] for edge in subtree.edges()]
                nx.draw_networkx_edges(subtree, pos, width=edge_widths, alpha=0.7, edge_color='gray', 
                                      arrows=True, arrowsize=15, arrowstyle='-|>', connectionstyle='arc3,rad=0.1')
                
                # 节点标签：节点ID + 分配水量
                labels = {n: f"{n}\n{G.nodes[n]['allocation']}万m³" for n in subtree.nodes()}
                nx.draw_networkx_labels(subtree, pos, labels=labels, font_size=10, font_color='black', font_weight='bold')
                
                # 边标签：显示水量流向
                edge_labels = {(u, v): f"{G.edges[u, v]['flow']:.2f}" for u, v in subtree.edges()}
                nx.draw_networkx_edge_labels(subtree, pos, edge_labels=edge_labels, font_size=8, alpha=0.7)
                
                # 设置子图标题
                total_root_allocation = G.nodes[root]["allocation"]
                total_children_allocation = sum(G.edges[root, child]["flow"] for child in subtree.neighbors(root) if (root, child) in G.edges)
                remaining = total_root_allocation - total_children_allocation
                
                ax.set_title(f"根节点: {root} (获得: {total_root_allocation}万m³, 分配: {total_children_allocation:.2f}万m³, 余量: {remaining:.2f}万m³)", 
                           fontsize=12)
                ax.axis('off')
            
            # 设置总标题
            plt.suptitle(title, fontsize=16)
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            
            # 添加图例
            # 创建图例（自定义）
            legend_ax = fig.add_axes([0.85, 0.02, 0.1, 0.1])
            legend_ax.axis('off')
            legend_ax.add_patch(plt.Rectangle((0, 0.8), 0.2, 0.2, fc='#ff9999', alpha=0.8))
            legend_ax.add_patch(plt.Rectangle((0, 0.4), 0.2, 0.2, fc='#99ccff', alpha=0.8))
            legend_ax.text(0.3, 0.8, '父节点', fontsize=10)
            legend_ax.text(0.3, 0.4, '子节点', fontsize=10)
            legend_ax.text(0, 0, '节点大小和连线粗细代表水量大小', fontsize=10)
            
            # 保存图表
            file_name = title.replace(" ", "_").replace(":", "").replace("-", "_").replace("(", "").replace(")", "")
            output_file = os.path.join(output_dir, f"{file_name}_树状图.png")
            plt.savefig(output_file, dpi=300)
            plt.close()
            
            print(f"已保存节点分配树状图至 {output_file}")
            
            # 额外创建一个水量分配桑基图
            sankey_file_name = self._plot_sankey_diagram(result, output_dir, title)
            return sankey_file_name
            
        except ImportError:
            print("警告：无法导入networkx库，无法绘制节点分配树状图")
            print("请安装networkx库：pip install networkx matplotlib pydot pygraphviz")
        except Exception as e:
            print(f"绘制节点分配树状图时出错：{str(e)}")

            
    def _plot_sankey_diagram(self, result, output_dir, title):
        """创建水量分配桑基图
        
        使用plotly库创建桑基图，显示水资源从水源到父节点再到子节点的流动
        """
        try:
            import plotly.graph_objects as go
            
            # 从树结构定义获取节点关系
            tree_df = pd.read_excel("model3/tree1.xlsx")
            
            # 构建节点与其父节点的映射
            child_to_parent = dict(zip(tree_df['ID'], tree_df['上一节点ID']))
            
            # 所有节点的分配结果
            node_allocations = result["node_allocation"]
            
            # 创建桑基图数据
            source = []  # 源节点索引
            target = []  # 目标节点索引
            value = []   # 流量值
            
            # 所有出现在图中的节点
            all_nodes = set()
            
            # 添加水源到父节点的流动
            for s in self.water_sources:
                if s not in result["allocation"]:
                    continue
                    
                for parent, flow in result["allocation"][s].items():
                    if flow > 0:
                        all_nodes.add(s)
                        all_nodes.add(parent)
            
            # 添加父节点到子节点的流动
            for child, parent in child_to_parent.items():
                if pd.notna(parent) and child in node_allocations and parent in node_allocations:
                    child_allocation = node_allocations[child]
                    if child_allocation > 0:
                        all_nodes.add(parent)
                        all_nodes.add(child)
            
            # 创建节点索引映射
            node_list = list(all_nodes)
            node_indices = {node: i for i, node in enumerate(node_list)}
            
            # 添加水源到父节点的流动
            for s in self.water_sources:
                if s not in result["allocation"]:
                    continue
                    
                for parent, flow in result["allocation"][s].items():
                    if flow > 0:
                        source.append(node_indices[s])
                        target.append(node_indices[parent])
                        value.append(flow)
            
            # 添加父节点到子节点的流动
            for child, parent in child_to_parent.items():
                if pd.notna(parent) and child in node_allocations and parent in node_allocations:
                    child_allocation = node_allocations[child]
                    if child_allocation > 0:
                        source.append(node_indices[parent])
                        target.append(node_indices[child])
                        value.append(child_allocation)
            
            # 创建自定义节点标签
            node_labels = []
            for node in node_list:
                if node in self.water_sources:
                    node_labels.append(f"水源: {node} ({sum(result['allocation'].get(node, {}).values()):.2f}万m³)")
                elif node in child_to_parent and pd.isna(child_to_parent[node]):
                    # 根节点
                    node_labels.append(f"根节点: {node} ({node_allocations.get(node, 0):.2f}万m³)")
                else:
                    # 普通节点
                    node_labels.append(f"节点: {node} ({node_allocations.get(node, 0):.2f}万m³)")
            
            # 创建桑基图
            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=node_labels,
                ),
                link=dict(
                    source=source,
                    target=target,
                    value=value,
                )
            )])
            
            # 设置标题
            fig.update_layout(title_text=f"{title} - 水量分配流向图", font_size=12)
            
            # 保存图表
            file_name = title.replace(" ", "_").replace(":", "").replace("-", "_").replace("(", "").replace(")", "")
            output_file = os.path.join(output_dir, f"{file_name}_桑基图.html")
            fig.write_html(output_file)
            
            print(f"已保存水量分配桑基图至 {output_file}")
            return output_file
            
        except ImportError:
            print("警告：无法导入plotly库，无法绘制水量分配桑基图")
            print("请安装plotly库：pip install plotly")
        except Exception as e:
            print(f"绘制水量分配桑基图时出错：{str(e)}")