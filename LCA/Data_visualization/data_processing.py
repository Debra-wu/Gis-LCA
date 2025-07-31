
# Operational Carbon emission

# 导入数据
from LCA.manufacturing_data.AWE_manufacturing_data import impact_assessment_result_dict as AWE_manu
from LCA.manufacturing_data.PEM_manufacturing_data import impact_assessment_result_dict as PEM_manu
from LCA.manufacturing_data.SOE_manufacturing_data import impact_assessment_result_dict as SOE_manu

from LCA.operation_data.AWE_ammonia_data import impact_assessment_result_dict as AWE_op
from LCA.operation_data.PEM_ammonia_data import impact_assessment_result_dict as PEM_op
from LCA.operation_data.SOE_ammonia_data import impact_assessment_result_dict as SOE_op

from LCA.economy_data import opex_data,location_factors
from LCA.economy_data import capex_data

def cost_to_capacity_scaling(C1, S1, S2, n):
    C2 = C1 * (S2 / S1) ** n
    return C2

def location_factor_cost(C_origin, location_factor):
    C_target = C_origin * location_factor
    return C_target

def cost_index_adjustment(C_base, CEPCI_base, CEPCI_target):
    C_target = C_base * (CEPCI_target / CEPCI_base)
    return C_target


def total_emission(manu_emission, op_emission):
    return manu_emission*0.188 + op_emission

# 假设目标容量为 100
target_capacity = 100
scaling_exponent = 0.7  # 可根据经验修改，通常在 0.6~0.85 之间

# 用于存储最终转换为 UK 的数据
adjusted_capex_to_UK = {}
adjusted_opex_to_UK = {}

# CAPEX 处理
for tech, data in capex_data.items():
    original_cost = data["amount"]
    original_capacity = data["capacity"]
    location = data["location"]

    # Step 1: Cost-to-Capacity Scaling
    scaled_cost = cost_to_capacity_scaling(C1=original_cost, S1=original_capacity, S2=target_capacity, n=scaling_exponent)

    # Step 2: Location Factor to UK
    location_factor = location_factors['UK_Edinburgh'] / location_factors[location]
    adjusted_cost = location_factor_cost(C_origin=scaled_cost, location_factor=location_factor)

    # 保存结果
    adjusted_capex_to_UK[tech] = adjusted_cost

# OPEX 处理
for tech, data in opex_data.items():
    if "amount" not in data or "capacity" not in data:
        continue  # 跳过不适用的条目，如 electricity price from wind

    original_cost = data["amount"]
    original_capacity = data["capacity"]
    location = data["location"]

    # Step 1: Cost-to-Capacity Scaling
    scaled_cost = cost_to_capacity_scaling(C1=original_cost, S1=original_capacity, S2=target_capacity, n=scaling_exponent)

    # Step 2: Location Factor to UK
    location_factor = location_factors['UK_Edinburgh'] / location_factors[location]
    adjusted_cost = location_factor_cost(C_origin=scaled_cost, location_factor=location_factor)

    # 保存结果
    adjusted_opex_to_UK[tech] = adjusted_cost
    # 单独处理 excluding energy generation 的电价（solar 和 wind）
    if "excluding energy generation" in opex_data:
        excl = opex_data["excluding energy generation"]
        if "electricity price from solar" in excl:
            adjusted_opex_to_UK["electricity price from solar"] = excl["electricity price from solar"]
        if "electricity price from wind" in excl:
            adjusted_opex_to_UK["electricity price from wind"] = excl["electricity price from wind"]

# 输出结果
# print("Adjusted CAPEX to UK (at 100 kt/y scale):")
# for tech, cost in adjusted_capex_to_UK.items():
#     print(f"  {tech}: {cost:.2f} Million USD")
#
# print("\nAdjusted OPEX to UK (at 100 kt/y scale):")
# for tech, cost in adjusted_opex_to_UK.items():
#     if "electricity price" in tech:
#         print(f"  {tech}: {cost:.2f} £/MWh")
#     else:
#         print(f"  {tech}: {cost:.2f} USD/t")



import os

impact_keys = [
    "Global warming",
    "Terrestrial acidification",
    "Marine eutrophication",
    "Freshwater eutrophication",
    "Fine particulate matter formation",
    "Fossil resource scarcity",
    "Mineral resource scarcity"
]

manufacturing_data = {
    "AWE": AWE_manu,
    "PEM": PEM_manu,
    "SOE": SOE_manu,
}

operation_data = {
    "AWE": AWE_op,
    "PEM": PEM_op,
    "SOE": SOE_op,
}

def total_emission(manu, op):
    return manu * 0.188 + op

# 构建总结果
total_emission_data = {}

for impact_key in impact_keys:
    total_emission_data[impact_key] = {}
    for tech in manufacturing_data:
        try:
            manu_value = manufacturing_data[tech][impact_key]["amount"]
            op_value = operation_data[tech][impact_key]["amount"]
            total = total_emission(manu_value, op_value)
            total_emission_data[impact_key][tech] = total
        except KeyError:
            total_emission_data[impact_key][tech] = None  # 或者 0, 或者 continue

# 输出为 .py 文件
import os

# ⚠️ Make sure adjusted_capex_to_UK and adjusted_opex_to_UK already exist
# You can place this at the end of your data_processing.py

# 输出为 .py 文件（包含时间信息）
output_path = os.path.join("data_collection", "economy_result_data", "adjusted_economic_summary.py")
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w") as f:
    f.write("# Auto-generated adjusted economic summary\n\n")

    # CAPEX section
    f.write("# Adjusted CAPEX data (Unit: Million USD, standardized to UK, at 100 kt/y capacity)\n")
    f.write("adjusted_capex = {\n")
    for tech, cost in adjusted_capex_to_UK.items():
        time = capex_data[tech]["time"]
        f.write(f"    {repr(tech)}: {{'value': {cost:.2f}, 'time': {time}}},\n")
    f.write("}\n\n")

    # OPEX section
    f.write("# Adjusted OPEX data (Unit: USD/t for general, £/MWh for electricity price)\n")
    f.write("adjusted_opex = {\n")
    for tech, cost in adjusted_opex_to_UK.items():
        if tech in opex_data:
            time = opex_data[tech]["time"]
            f.write(f"    {repr(tech)}: {{'value': {cost:.2f}, 'time': {time}}},\n")
        else:
            # For 'electricity price from solar/wind' fallback default year from excluding energy generation
            time = opex_data["excluding energy generation"]["time"]
            f.write(f"    {repr(tech)}: {{'value': {cost:.2f}, 'time': {time}}},\n")
    f.write("}\n")






# ⚠️ Make sure adjusted_capex_to_UK and adjusted_opex_to_UK already exist
# You can place this at the end of your data_processing.py

import os

# ⚠️ Make sure adjusted_capex_to_UK and adjusted_opex_to_UK already exist
# You can place this at the end of your data_processing.py

output_path = os.path.join("LCA", "economy_result_data", "total_emission_summary.py")
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w") as f:
    f.write("# Auto-generated total emission summary\n")
    f.write("total_emission_data = {\n")
    for impact_key, tech_dict in total_emission_data.items():
        f.write(f"    {repr(impact_key)}: {{\n")
        for tech, value in tech_dict.items():
            if value is not None:
                f.write(f"        {repr(tech)}: {value:.6f},\n")
            else:
                f.write(f"        {repr(tech)}: None,\n")
        f.write("    },\n")
    f.write("}\n")


