import tkinter as tk
from tkinter import ttk, messagebox

# 从结果模块中导入数据
from .data_collection.impact_result_data.total_emission_summary import total_emission_data
from .data_collection.economy_result_data.adjusted_economic_summary import adjusted_capex, adjusted_opex

# ✅ 只导入字典，不重新运行模型
from .cepci_data import cepci_dict

# ✅ 导入 cost_index_adjustment 函数
from .data_processing import cost_index_adjustment

# Impact category 对应单位（从 LCA impact_assessment_result_dict 提取）
impact_units = {
    "Global warming": "kg CO2 eq",
    "Terrestrial acidification": "kg SO2 eq",
    "Marine eutrophication": "kg N eq",
    "Freshwater eutrophication": "kg P eq",
    "Fine particulate matter formation": "kg PM2.5 eq",
    "Fossil resource scarcity": "kg oil eq",
    "Mineral resource scarcity": "kg Cu eq",
}


class EmissionCostPopup:
    def __init__(self, master):
        self.top = tk.Toplevel(master)
        self.top.title("Carbon Emission & Cost")

        self.electrolyzers = ["AWE", "PEM", "SOE"]
        self.energy_sources = ["hydro", "solar/wind", "excluding energy generation"]
        self.impact_categories = list(total_emission_data.keys())
        self.construction_years = [str(y) for y in range(2025, 2031)]

        # Electrolyzer type
        tk.Label(self.top, text="Select Electrolyzer Type:").grid(row=0, column=0, padx=10, pady=5)
        self.electrolyzer_var = tk.StringVar(value=self.electrolyzers[0])
        ttk.Combobox(self.top, textvariable=self.electrolyzer_var, values=self.electrolyzers, state="readonly").grid(row=0, column=1)

        # Energy source
        tk.Label(self.top, text="Select Energy Source:").grid(row=1, column=0, padx=10, pady=5)
        self.energy_var = tk.StringVar(value=self.energy_sources[0])
        ttk.Combobox(self.top, textvariable=self.energy_var, values=self.energy_sources, state="readonly").grid(row=1, column=1)

        # Environmental impact category
        tk.Label(self.top, text="Select Impact Category:").grid(row=2, column=0, padx=10, pady=5)
        self.impact_var = tk.StringVar(value=self.impact_categories[0])
        ttk.Combobox(self.top, textvariable=self.impact_var, values=self.impact_categories, state="readonly").grid(row=2, column=1)

        # Construction year
        tk.Label(self.top, text="Select Construction Year:").grid(row=3, column=0, padx=10, pady=5)
        self.year_var = tk.StringVar(value=self.construction_years[0])
        ttk.Combobox(self.top, textvariable=self.year_var, values=self.construction_years, state="readonly").grid(row=3, column=1)

        tk.Button(self.top, text="View Data", command=self.display_results).grid(row=4, column=0, columnspan=2, pady=10)

    def display_results(self):
        electrolyzer = self.electrolyzer_var.get()
        energy = self.energy_var.get()
        impact_category = self.impact_var.get()
        construction_year = int(self.year_var.get())

        try:
            # 1. Environmental impact emission
            emission_value = total_emission_data[impact_category].get(electrolyzer)
            if emission_value is None:
                raise ValueError("Emission data not available for selection.")

            # 2. Construction emission（固定）
            construction_emission = 6.511178959100128 / 30

            # 3. 初始化文本
            capex_text = ""
            opex_text = ""
            extra_info = ""
            capex_adjusted = None  # 用于后续统一 capex_per_kg 判断

            if energy == "hydro":
                capex_base = adjusted_capex["Hydro"]
                opex_base = adjusted_opex["Hydro"]

                capex_adjusted = cost_index_adjustment(
                    capex_base["value"],
                    cepci_dict[capex_base["time"]],
                    cepci_dict[construction_year]
                )
                opex_adjusted = cost_index_adjustment(
                    opex_base["value"],
                    cepci_dict[opex_base["time"]],
                    cepci_dict[construction_year]
                )

                capex_text = f"CAPEX (adjusted): {capex_adjusted:.2f} Million GBP\n"
                opex_text = f"OPEX (adjusted): {opex_adjusted:.2f} (GBP/kg)\n"

            elif energy == "solar/wind":
                capex_base = adjusted_capex["Solar/Wind"]
                opex_base = adjusted_opex["Solar/Wind"]

                capex_adjusted = cost_index_adjustment(
                    capex_base["value"],
                    cepci_dict[capex_base["time"]],
                    cepci_dict[construction_year]
                )
                opex_adjusted = cost_index_adjustment(
                    opex_base["value"],
                    cepci_dict[opex_base["time"]],
                    cepci_dict[construction_year]
                )

                capex_text = f"CAPEX (adjusted): {capex_adjusted:.2f} Million GBP\n"
                opex_text = f"OPEX (adjusted): {opex_adjusted:.2f} (GBP/kg)\n"

            elif energy == "excluding energy generation":
                capex_base = adjusted_capex["excluding energy generation"]
                capex_adjusted = cost_index_adjustment(
                    capex_base["value"],
                    cepci_dict[capex_base["time"]],
                    cepci_dict[construction_year]
                )
                capex_per_kg = capex_adjusted * 1e6 / 100_000_000 / 30
                solar = adjusted_opex["electricity price from solar"]
                wind = adjusted_opex["electricity price from wind"]

                solar_adjusted = cost_index_adjustment(
                    solar["value"],
                    cepci_dict[solar["time"]],
                    cepci_dict[construction_year]
                )
                wind_adjusted = cost_index_adjustment(
                    wind["value"],
                    cepci_dict[wind["time"]],
                    cepci_dict[construction_year]
                )

                extra_info = (
                    f"CAPEX (adjusted): {capex_adjusted:.2f} Million GBP\n"
                    f"Electricity Price (Solar, adjusted): {solar_adjusted:.2f} GBP/MWh\n"
                    f"Electricity Price (Wind, adjusted): {wind_adjusted:.2f} GBP/MWh\n"
                    f"CAPEX per kg NH3 (over 30 years): {capex_per_kg:.6f} GBP/kg\n"
                )
            else:
                raise ValueError("Unknown energy type.")

            unit = impact_units.get(impact_category, "kg eq")

            # 4. 构建最终结果文本
            result = (
                f"Electrolyzer: {electrolyzer}\n"
                f"Energy Source: {energy}\n"
                f"Impact Category: {impact_category}\n"
                f"Construction Year: {construction_year}\n\n"
                f"Environmental Impact: {emission_value:.4f} {unit}\n"
                f"Construction Emission: {construction_emission:.4f} kg CO2 eq\n"
                f"{capex_text}{opex_text}"
            )

            # 5. 添加 CAPEX/kg（如适用）
            if capex_adjusted is not None:
                capex_per_kg = capex_adjusted * 1e6 / 100_000_000 / 30
                result += f"CAPEX per kg NH3 (over 30 years): {capex_per_kg:.6f} GBP/kg\n"

            # 6. 额外信息与注释
            result += f"{extra_info}\n(Assuming: 30-year lifetime, 100 kt/year green ammonia plant)"

            messagebox.showinfo("Result", result)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve data:\n{e}")

# Run the tkinter app
if __name__ == "__main__":
    root = tk.Tk()
    root.title("LCA Data Viewer")
    tk.Button(root, text="Open Emission & Cost Viewer", command=lambda: EmissionCostPopup(root)).pack(pady=20)
    root.mainloop()
