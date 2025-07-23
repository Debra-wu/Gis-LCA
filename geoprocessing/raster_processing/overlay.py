import os
import pyproj

# 自动设置 PROJ_LIB 路径
proj_data_dir = pyproj.datadir.get_data_dir()
os.environ["PROJ_LIB"] = proj_data_dir
print(f"[INFO] PROJ_LIB set to: {proj_data_dir}")

from pyproj import CRS

try:
    crs = CRS.from_epsg(27700)
    print("✅ Successfully loaded EPSG:27700")
    print(crs)
except Exception as e:
    print(f"⚠️ Failed to load EPSG:27700, using WKT string instead: {e}")

import rasterio
import numpy as np
from .constants import print_crs_info, EPSG_27700_WKT

def weighted_overlay(raster_paths, weights, out_path):
    layers = []
    profile = None
    for path in raster_paths:
        with rasterio.open(path) as src:
            print_crs_info(f"Input raster for weighted overlay {path}", src.crs)
            data = src.read(1).astype(float)  # 只读取数据波段
            profile = src.profile
            nodata = src.nodata
            data = np.where((data == nodata) | np.isnan(data), 0, data)
            layers.append(data)

    weighted_sum = np.zeros_like(layers[0])
    for i, layer in enumerate(layers):
        weighted_sum += layer * weights[i]

    max_val = np.nanmax(weighted_sum)
    score = (weighted_sum / max_val) * 100 if max_val != 0 else weighted_sum

    # 添加透明通道
    alpha_band = (score > 0).astype(np.uint8) * 255
    output_data = np.stack([score.astype(np.float32), alpha_band], axis=0)

    profile.update(
        dtype=rasterio.float32,
        nodata=0,
        crs=rasterio.crs.CRS.from_wkt(EPSG_27700_WKT),
        count=2
    )

    print_crs_info(f"Output weighted overlay raster {out_path}", profile["crs"])

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(output_data)

    return out_path
