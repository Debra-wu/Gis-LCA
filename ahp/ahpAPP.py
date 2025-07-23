
from constants import criteria_structure
from ahp_core import AHPMatrixInput
from ahp_core import generate_consistent_matrix
import tkinter as tk
from tkinter import messagebox
import json


class AHPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AHP-Based Site Suitability Analysis Tool for Green Ammonia Plants")

        self.criteria = list(criteria_structure.keys())
        self.weights = {}
        self.final_weights = {}

        tk.Label(root, text="Step 1: Fill in the criteria-level comparison matrix").pack()
        tk.Button(root, text="Edit Criteria Matrix", command=self.edit_criteria).pack(pady=5)

        tk.Label(root, text="Step 2: Fill in the comparison matrix for each criterion").pack()
        for c in self.criteria:
            tk.Button(root, text=f"Edit '{c}' Subcriteria", command=lambda c=c: self.edit_subcriteria(c)).pack()
            # lambda c=c: 是为了绑定循环中当前的c值，防止闭包变量被覆盖

        tk.Button(root, text="Calculate and Show Final Weights", command=self.calculate_final).pack(pady=10)

        # 新增自动计算按钮
        tk.Button(root, text="Auto-generate All Weights", command=self.auto_calculate).pack(pady=5)

    def edit_criteria(self):
        AHPMatrixInput(self.root, "Criteria", self.criteria, self.save_weights)

    def edit_subcriteria(self, criterion):
        items = criteria_structure[criterion]
        AHPMatrixInput(self.root, criterion, items, self.save_weights)

    def save_weights(self, name, weight_dict):
        self.weights[name] = weight_dict

    def calculate_final(self):
        if "Criteria" not in self.weights:
            messagebox.showerror("Error", "Please fill in the criteria-level comparison matrix first.")
            return

        missing = [c for c in self.criteria if c not in self.weights]
        if missing:
            messagebox.showerror("Error", f"The following subcriteria matrices are missing：{missing}")
            return

        self.final_weights.clear()
        for crit, sub_weights in self.weights.items():
            if crit == "Criteria":
                continue
            parent_weight = self.weights["Criteria"].get(crit, 0)
            for sub, w in sub_weights.items():
                self.final_weights[sub] = round(w * parent_weight, 4)

        msg = "\n".join([f"{k}: {v}" for k, v in self.final_weights.items()])
        messagebox.showinfo("Final Weights for All Factors (for GIS weighted overlay)", msg)
        with open("weights.json", "w", encoding="utf-8") as f:
            json.dump(self.final_weights, f, ensure_ascii=False, indent=2)

    def auto_calculate(self):
        self.weights.clear()
        # 自动为准则层生成一致性矩阵
        n_crit = len(self.criteria)
        A, w = generate_consistent_matrix(n_crit)
        self.weights["Criteria"] = {self.criteria[i]: round(w[i], 4) for i in range(n_crit)}

        # 为每个准则层也生成一致性子矩阵
        for crit in self.criteria:
            subfactors = criteria_structure[crit]
            A_sub, w_sub = generate_consistent_matrix(len(subfactors))
            self.weights[crit] = {subfactors[i]: round(w_sub[i], 4) for i in range(len(subfactors))}

        # 自动展示结果
        self.calculate_final()