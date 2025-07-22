

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