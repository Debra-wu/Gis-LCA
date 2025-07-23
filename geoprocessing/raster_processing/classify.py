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
from sklearn.cluster import KMeans
from .constants import print_crs_info, EPSG_27700_WKT

def classify_natural_breaks(raster_path, out_path, n_class=5):
    with rasterio.open(raster_path) as src:
        print_crs_info(f"Input classified raster {raster_path}", src.crs)
        data = src.read(1)
        profile = src.profile
        nodata = src.nodata

    valid_mask = (data != nodata) & (~np.isnan(data))
    valid_data = data[valid_mask].reshape(-1, 1)

    if valid_data.size == 0:
        raise ValueError("Input raster has no valid data for classification!")

    kmeans = KMeans(n_clusters=n_class, random_state=0).fit(valid_data)
    centers = sorted(kmeans.cluster_centers_.flatten())
    thresholds = [(centers[i] + centers[i + 1]) / 2 for i in range(len(centers) - 1)]

    scores = [1, 0.75, 0.5, 0.25, 0]
    classified = np.zeros_like(data, dtype=np.float32)
    for i, t in enumerate(thresholds):
        if i == 0:
            classified[(data <= t) & valid_mask] = scores[-1 - i]
        else:
            classified[(data > thresholds[i - 1]) & (data <= t) & valid_mask] = scores[-1 - i]
    classified[(data > thresholds[-1]) & valid_mask] = scores[0]

    # 添加透明通道
    alpha_band = (valid_mask * 255).astype(np.uint8)
    output_data = np.stack([classified, alpha_band], axis=0)

    profile.update(
        dtype=rasterio.float32,
        nodata=0,
        crs=rasterio.crs.CRS.from_wkt(EPSG_27700_WKT),
        count=2
    )

    print_crs_info(f"Output classified raster {out_path}", profile["crs"])

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(output_data)

    return out_path


def reclassify_landuse(landuse_path, out_path):
    with rasterio.open(landuse_path) as src:
        print_crs_info(f"Input land use raster {landuse_path}", src.crs)
        data = src.read(1)
        profile = src.profile

    reclass = {
        1: 4, 2: 4,
        3: 3, 4: 3, 5: 3, 6: 3, 7: 3,
        8: 2, 9: 2, 10: 2, 11: 2, 12: 2, 13: 2, 14: 2,
        15: 2, 16: 2, 17: 2, 18: 2, 19: 2,
        20: 5, 21: 5
    }

    out = np.zeros_like(data, dtype=np.float32)
    for k, v in reclass.items():
        out[data == k] = 6 - v

    # 添加透明通道
    alpha_band = (out > 0).astype(np.uint8) * 255
    output_data = np.stack([out, alpha_band], axis=0)

    profile.update(
        dtype=rasterio.float32,
        nodata=0,
        crs=rasterio.crs.CRS.from_wkt(EPSG_27700_WKT),
        count=2
    )

    print_crs_info(f"Output reclassified land use raster {out_path}", profile["crs"])

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(output_data)

    return out_path