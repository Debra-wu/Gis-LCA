
# Operational Carbon emission

# 导入数据
from LCA.manufacturing_data.AWE_manufacturing_data import impact_assessment_result_dict as AWE_manu
from LCA.manufacturing_data.PEM_manufacturing_data import impact_assessment_result_dict as PEM_manu
from LCA.manufacturing_data.SOE_manufacturing_data import impact_assessment_result_dict as SOE_manu

from LCA.operation_data.AWE_ammonia_data import impact_assessment_result_dict as AWE_op
from LCA.operation_data.PEM_ammonia_data import impact_assessment_result_dict as PEM_op
from LCA.operation_data.SOE_ammonia_data import impact_assessment_result_dict as SOE_op

from LCA.economy_data import opex_data
from LCA.economy_data import capex_data

# 提取 Global warming 数据
AWE_manu_emission = AWE_manu["Global warming"]["amount"]
PEM_manu_emission = PEM_manu["Global warming"]["amount"]
SOE_manu_emission = SOE_manu["Global warming"]["amount"]

AWE_op_emission = AWE_op["Global warming"]["amount"]
PEM_op_emission = PEM_op["Global warming"]["amount"]
SOE_op_emission = SOE_op["Global warming"]["amount"]

# 计算总碳排放
AWE_total_emission = AWE_manu_emission * 0.188 + AWE_op_emission
PEM_total_emission = PEM_manu_emission * 0.188 + PEM_op_emission
SOE_total_emission = SOE_manu_emission * 0.188 + SOE_op_emission


print(AWE_total_emission, PEM_total_emission, SOE_total_emission)

solar_opex_data=opex_data["Real case of solar energy in the UK (Yara/BASF)"]["amount"]
wind_opex_data=opex_data["Real case of wind energy in the UK (Yara/BASF)"]["amount"]

solar_capex_data=capex_data["Real case of solar energy in the UK (Yara/BASF)"]["amount"]
wind_capex_data=capex_data["Real case of wind energy in the UK (Yara/BASF)"]["amount"]

print(solar_opex_data, wind_opex_data)
print(solar_capex_data, wind_capex_data)