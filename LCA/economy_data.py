# capex_data = {
#     "Solar energy (single-axis tracking)": {"amount": 493, "unit": "USD/MWp,DC"},
#     "Electrolytic cell": {"amount": 655, "unit": "USD/kW input"},
#     "Haber-Bosch synthesis": {"amount": 3300, "unit": "USD/kg NH3/hr"},
#     "Air Separation Unit (ASU)": {"amount": 1450, "unit": "USD/kg N2/hr"},
#     "Lithium-ion battery": {"amount": 218, "unit": "USD/kWh"},
#     "Desalination of seawater": {"amount": 5.72, "unit": "USD/m³/yr"},
#     "Overall LCOA": {"amount": 634, "unit": "USD/t NH3"},
#     "Cost of carbon-neutral ammonia in UK": {"amount": None, "unit": None},
#     "Real case of solar energy in the UK (Yara/BASF)": {"amount": 0.488, "unit": "billion GBP"},
#     "Real case of wind energy in the UK (Yara/BASF)": {"amount": 0.7, "unit": "billion GBP"}
# }

# opex_data = {
#     "Solar energy (single-axis tracking)": {"amount": 6800, "unit": "USD/MWp,DC/yr"},
#     "Electrolytic cell": {"amount": 1.5, "unit": "% of CAPEX"},
#     "Haber-Bosch synthesis": {"amount": None, "unit": None},
#     "Air Separation Unit (ASU)": {"amount": [15.51, 18.98], "unit": "USD/t"},
#     "Lithium-ion battery": {"amount": None, "unit": None},
#     "Desalination of seawater": {"amount": [0.34, 0.57], "unit": "USD/t"},
#     "Overall LCOA": {"amount": None, "unit": None},
#     "Cost of carbon-neutral ammonia in UK": {"amount": [0.22, 0.57], "unit": "GBP/kg"},
#     "Real case of solar energy in the UK (Yara/BASF)": {"amount": 0.0025, "unit": "GBP/kg"},
#     "Real case of wind energy in the UK (Yara/BASF)": {"amount": 0.005, "unit": "GBP/kg"}
# }

capex_data_1 = {
    "Hydro": {"capacity": 175, "amount": 327,"unit": "Million USD", "location": "Brasil", "time":2019},
    "Solar/Wind": {"capacity": 200, "amount": 2124,"unit": "Million USD", "location": "Spain","time":2020},
    "excluding energy generation": {"capacity": 650, "amount": 1210,"unit": "Million USD", "location": "Denmark", "time":2021}
}
opex_data_1 = {
    "Hydro": {"capacity": 175, "amount": 298,"unit": "USD/t", "location": "Brasil","time":2019},
    "Solar/Wind": {"capacity": 291, "amount": 1020.5,"unit": "USD/t", "location": "UK_Edinburgh","time":2025},
    "excluding energy generation": {"electricity price from wind": 53,"unit": " £/MWh", "electricity price from solar": 47,"location": "UK_Edinburgh","time":2025}

}

capacity_unit="kt/y"

USD_to_GB_2019=(0.8318+0.7422)/2

USD_to_GB_2020=(0.8702+0.7314)/2

USD_to_GB_2021=(0.7571+0.7029)/2

USD_to_GB_2025=0.7676

capex_data = {
    "Hydro": {"capacity": 175, "amount": 327*USD_to_GB_2019,"unit": "Million GBP", "location": "Brasil", "time":2019},
    "Solar/Wind": {"capacity": 200, "amount": 2124*USD_to_GB_2020,"unit": "Million GBP", "location": "Spain","time":2020},
    "excluding energy generation": {"capacity": 650*USD_to_GB_2021, "amount": 1210,"unit": "Million GBP", "location": "Denmark", "time":2021}
}
opex_data = {
    "Hydro": {"capacity": 175, "amount": 298*USD_to_GB_2019/1000,"unit": "GBP/kg", "location": "Brasil","time":2019},
    "Solar/Wind": {"capacity": 291, "amount": 1020.5*USD_to_GB_2025/1000,"unit": "GBP/kg", "location": "UK_Edinburgh","time":2025},
    "excluding energy generation": {"electricity price from wind": 53,"unit": " £/MWh", "electricity price from solar": 47,"location": "UK_Edinburgh","time":2025}

}
# 🌍 Location factor 中值（目标地 / 原地）
location_factors = {
    'Brasil': (0.88 + 0.96) / 2,          # 0.92
    'Spain': (0.92 + 0.94) / 2,           # 0.93
    'Denmark': (1.05 + 1.09) / 2,         # 1.07
    'UK_Edinburgh': (1.03 + 1.06) / 2     # 1.045
}

# 示例：从 Spain 调整到 UK_Edinburgh
# 目标地 / 原地
location_factor_Spain_to_UK = location_factors['UK_Edinburgh'] / location_factors['Spain']  # ≈ 1.1237
location_factor_Denmark_to_UK = location_factors['UK_Edinburgh'] / location_factors['Denmark']
location_factor_Brasil_to_UK = location_factors['UK_Edinburgh'] / location_factors['Brasil']

