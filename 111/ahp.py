import tkinter as tk
from tkinter import messagebox
import numpy as np

# 一致性随机指标（RI）使用的是创始人Thomas Saaty 提供的标准表的前七个random index
# original standard table is {
#     1: 0.0, 2: 0.0, 3: 0.58, 4: 0.9,
#     5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49 ...
# }
# 这个表格是通过大量随机生成的判断矩阵计算得出的平均 CI 值，因此是经验性的
RI_dict = {
    1: 0.0, 2: 0.0, 3: 0.58, 4: 0.9,
    5: 1.12, 6: 1.24, 7: 1.32
}

# 层级结构定义
# 定义每个准则下有哪些因子
# 控制弹窗矩阵输入框的数量；
# 最终用于乘以对应权重，得到因子权重合成值。
criteria_structure = {
    "Energy": ["Solar Energy", "Wind Energy"],
    "Transportation": ["Road Access"],
    "Environment": ["Slope", "Water System"],
    "Regulation": ["Land Use", "Protected Area"]
} # 使得打分更加的主观且透明


def generate_consistent_matrix(n, base_weights=None):
    """生成一致性矩阵"""
    if base_weights is None:
        w = np.random.rand(n) # 如果没有传入 base_weights，就随机生成一个长度为 n 的向量（每个元素在 0~1 之间）
    else:
        w = np.array(base_weights)
    w = w / np.sum(w) # 将权重向量归一化，让所有权重加起来等于 1
    A = np.ones((n, n))
    # 创建一个 n×n 的矩阵 A，并初始化为全 1
    # 注意：对角线一定是 1，因为任何元素与自身相比的重要性为 1
    for i in range(n):
        for j in range(n):
            A[i, j] = w[i] / w[j]
    return A, w


class AHPMatrixInput:
    def __init__(self, master, name, items, callback):
        self.top = tk.Toplevel(master) # 创建一个新弹窗 Toplevel
        self.top.title(f"Pairwise Comparison Matrix - {name}")
        self.name = name
        self.items = items
        self.callback = callback
        self.entries = {}
        self.build_ui() # entries 是一个字典，记录用户在 GUI 中填写的输入框（Entry 对象）

    def build_ui(self):
        n = len(self.items)
        # 处理标题栏的格式
        tk.Label(self.top, text=f"Fill the pairwise comparison matrix for {self.name} （values 1–9）", width=60, anchor="w").grid(row=0, column=0, columnspan=n+1, sticky="w")# sticky="w"防止控件本身在格子中居中
        # anchor="w" 控制文字贴左

        #处理第一行第一列的数据及格式
        for i in range(n):
            tk.Label(self.top, text=self.items[i], width=60).grid(row=i+1, column=0)
            tk.Label(self.top, text=self.items[i], width=15).grid(row=0, column=i+1)

        for i in range(n):
            for j in range(i):
                e = tk.Entry(self.top, width=5)
                e.insert(0, "1")
                e.grid(row=i+1, column=j+1)
                self.entries[(i, j)] = e
            tk.Label(self.top, text="1").grid(row=i+1, column=i+1)

        tk.Button(self.top, text="Calculate Weights", command=self.compute_weights).grid(row=n+2, column=0, columnspan=n+1)

    def compute_weights(self):
        n = len(self.items)
        A = np.ones((n, n)) # 创建一个 n×n 的矩阵，初始值为全 1（因为主对角线是 1）
        for (i, j), e in self.entries.items():
            try:
                val = float(e.get())
                A[i][j] = val
                A[j][i] = 1 / val
            except:
                messagebox.showerror("Error", f"Invalid input: {i+1}-{j+1}")
                return

        eigvals, eigvecs = np.linalg.eig(A)
        max_idx = np.argmax(np.real(eigvals))
        lambda_max = np.real(eigvals[max_idx])
        w = np.real(eigvecs[:, max_idx])
        w = w / np.sum(w)
        # 用 numpy 求解判断矩阵的特征值和特征向量
        # 归一化处理
        CI = (lambda_max - n) / (n - 1)
        CR = CI / RI_dict.get(n, 1.0)

        result = {self.items[i]: round(w[i], 4) for i in range(n)}
        self.callback(self.name, result)

        msg = f"Level：{self.name}\nWeights：{result}\nCI={CI:.4f}, CR={CR:.4f}"
        msg += "\n✅ Consistency is acceptable" if CR < 0.1 else "\n❌ Consistency is poor. Please check your input"
        messagebox.showinfo("Result", msg)
        self.top.destroy()


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


if __name__ == "__main__":
    root = tk.Tk()
    app = AHPApp(root)
    root.mainloop()
