import rasterio
import matplotlib.pyplot as plt

# 打开 tif 文件
with rasterio.open('C:/Users/13096/OneDrive/Desktop/gis data processed/suitability_score.tif') as src:
    img = src.read(1)  # 读取第一个波段（可以是1~n）

# 显示图像
plt.imshow(img, cmap='viridis')  # 可改为 'viridis' 或其他配色方案
plt.colorbar()
plt.title('Suitable Places for Green Ammonia Factory')
plt.show()
