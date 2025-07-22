
from constants import RI_dict
import tkinter as tk
from tkinter import messagebox
import numpy as np

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