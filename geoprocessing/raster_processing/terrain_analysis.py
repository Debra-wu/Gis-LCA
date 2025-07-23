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

def compute_slope(dem_path, out_path, grid_size):
    with rasterio.open(dem_path) as src:
        print_crs_info(f"Input DEM {dem_path}", src.crs)
        dem = src.read(1).astype(float)
        profile = src.profile

    dx = np.gradient(dem, axis=1) / grid_size
    dy = np.gradient(dem, axis=0) / grid_size
    slope = np.sqrt(dx ** 2 + dy ** 2)
    slope_degrees = np.arctan(slope) * (180.0 / np.pi)

    valid_mask = ~np.isnan(slope_degrees)
    breaks = np.percentile(slope_degrees[valid_mask], [25, 50, 75])
    score = np.ones_like(slope_degrees, dtype=np.uint8)
    score[(slope_degrees > breaks[0]) & valid_mask] = 3
    score[(slope_degrees > breaks[1]) & valid_mask] = 2
    score[(slope_degrees > breaks[2]) & valid_mask] = 1

    # 添加透明通道
    alpha_band = (valid_mask * 255).astype(np.uint8)
    output_data = np.stack([score, alpha_band], axis=0)

    profile.update(
        dtype=rasterio.uint8,
        nodata=0,
        crs=rasterio.crs.CRS.from_wkt(EPSG_27700_WKT),
        count=2  # 更新波段数
    )

    print_crs_info(f"Output slope raster {out_path}", profile["crs"])

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(output_data)

    return out_path