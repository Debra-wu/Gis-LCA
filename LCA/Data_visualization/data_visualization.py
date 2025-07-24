from LCA.Data_visualization.data_processing import AWE_total_emission, PEM_total_emission, SOE_total_emission, solar_capex_data,solar_opex_data,wind_capex_data,wind_opex_data


construction_carbon_emission=750000000*6.511178959100128/30/750000000

import tkinter as tk
from tkinter import ttk, messagebox

class EmissionCostPopup:
    def __init__(self, master):
        self.top = tk.Toplevel(master)
        self.top.title("Carbon Emission & Cost")

        self.electrolyzers = ["AWE", "PEM", "SOE"]
        self.energy_sources = ["wind energy", "solar energy"]

        tk.Label(self.top, text="Select Electrolyzer Type:").grid(row=0, column=0, padx=10, pady=5)
        self.electrolyzer_var = tk.StringVar(value=self.electrolyzers[0])
        ttk.Combobox(self.top, textvariable=self.electrolyzer_var, values=self.electrolyzers, state="readonly").grid(row=0, column=1)

        tk.Label(self.top, text="Select Energy Source:").grid(row=1, column=0, padx=10, pady=5)
        self.energy_var = tk.StringVar(value=self.energy_sources[0])
        ttk.Combobox(self.top, textvariable=self.energy_var, values=self.energy_sources, state="readonly").grid(row=1, column=1)

        tk.Button(self.top, text="View Data", command=self.display_results).grid(row=2, column=0, columnspan=2, pady=10)

    def display_results(self):
        electrolyzer = self.electrolyzer_var.get()
        energy = self.energy_var.get()

        try:
            # 1. Operational emission
            if electrolyzer == "AWE":
                op_emission = AWE_total_emission
            elif electrolyzer == "PEM":
                op_emission = PEM_total_emission
            elif electrolyzer == "SOE":
                op_emission = SOE_total_emission
            else:
                raise ValueError("Unknown electrolyzer type.")

            # 2. Construction emission（固定值）
            construction_emission = 6.511178959100128 / 30  # 约 0.2170

            # 3. CAPEX 和 OPEX
            if energy == "wind energy":
                if electrolyzer == "AWE":
                    capex = wind_capex_data_AWE = wind_capex_data
                    opex = wind_opex_data_AWE = wind_opex_data
                elif electrolyzer == "PEM":
                    capex = wind_capex_data_PEM = wind_capex_data
                    opex = wind_opex_data_PEM = wind_opex_data
                elif electrolyzer == "SOE":
                    capex = wind_capex_data_SOE = wind_capex_data
                    opex = wind_opex_data_SOE = wind_opex_data
            elif energy == "solar energy":
                if electrolyzer == "AWE":
                    capex = solar_capex_data_AWE = solar_capex_data
                    opex = solar_opex_data_AWE = solar_opex_data
                elif electrolyzer == "PEM":
                    capex = solar_capex_data_PEM = solar_capex_data
                    opex = solar_opex_data_PEM = solar_opex_data
                elif electrolyzer == "SOE":
                    capex = solar_capex_data_SOE = solar_capex_data
                    opex = solar_opex_data_SOE = solar_opex_data
            else:
                raise ValueError("Unknown energy type.")

            # 4. 打印结果
            result = (
                f"Electrolyzer: {electrolyzer}\n"
                f"Energy Source: {energy}\n\n"
                f"Operational Emission: {op_emission:.4f} kg PM2.5 eq\n"
                f"Construction Emission: {construction_emission:.4f} kg PM2.5 eq\n"
                f"CAPEX: {capex:.4f} £/kg NH3\n"
                f"OPEX: {opex:.4f} £/kg NH3"
            )

            messagebox.showinfo("Result", result)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve data: {e}")





root = tk.Tk()
tk.Button(root, text="Open Emission & Cost Viewer", command=lambda: EmissionCostPopup(root)).pack(pady=20)
root.mainloop()
