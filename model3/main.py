#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
水资源多目标配置模型主程序

基于"缺水最少、损耗最小"原则的水资源配置模型，支持年、月、旬三级配置方案
以及"年度配置-动态调整抗旱应急"的动态调整机制
"""

import argparse

import yaml

from model3.allocation_model import WaterResourceNSGAIII


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="水资源多目标配置模型")
    with open('config/configuration.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)['model3']
    default_data_file = config['default-data-file']
    # 基础参数
    parser.add_argument("--data", type=str, default=default_data_file, help="水资源原始数据文件路径")
    output_dir = config['output-dir']

    parser.add_argument("--output", type=str, default=output_dir, help="结果输出文件夹")

    # 功能模式选择
    parser.add_argument("--mode", type=str, choices=["annual", "monthly", "dekad"],
                        required=True,
                        help="运行模式：annual-年度配置，monthly-月度配置，dekad-旬配置")

    # 时间参数
    parser.add_argument("--year", type=int, help="年份，用于annual、monthly、dekad、multi模式")
    parser.add_argument("--month", type=int, help="月份，用于monthly、dekad模式")
    parser.add_argument("--dekad", type=int, choices=[1, 2, 3], help="旬：1-上旬，2-中旬，3-下旬，用于dekad模式")

    args = parser.parse_args()

    # 参数验证
    if args.mode in ["annual", "monthly", "dekad", "multi"] and args.year is None:
        parser.error(f"{args.mode}模式需要指定--year参数")

    if args.mode in ["monthly", "dekad"] and args.month is None:
        parser.error(f"{args.mode}模式需要指定--month参数")

    if args.mode == "dekad" and args.dekad is None:
        parser.error("dekad模式需要指定--dekad参数")

    return args


def main():
    # 解析命令行参数
    args = parse_args()

    storage_water_input = {
        "N5": 10,
        "A2": 25,
        # 可添加更多节点需求
    }
    # 创建模型实例
    model = WaterResourceNSGAIII(args.data, args.output, storage_water_input=storage_water_input)
    result = None
    file_dir_name = None
    # 根据运行模式执行相应功能
    if args.mode == "annual":
        result, file_dir_name = model.allocate_water_yearly(args.year)
        print(f"已完成{args.year}年度水资源配置")

    elif args.mode == "monthly":
        result, file_dir_name = model.allocate_water_monthly(args.year, args.month)
        print(f"已完成{args.year}年{args.month}月水资源配置")

    elif args.mode == "dekad":
        result, file_dir_name = model.allocate_water_dekad(args.year, args.month, args.dekad)
        dekad_name = {1: "上旬", 2: "中旬", 3: "下旬"}[args.dekad]
        print(f"已完成{args.year}年{args.month}月{dekad_name}水资源配置")

    print("程序执行完成！")
    return file_dir_name, result


if __name__ == "__main__":
    storage_water_input = {
        "节点1": 1000,
        "节点2": 500,
        # 可添加更多节点需求
    }
    main()