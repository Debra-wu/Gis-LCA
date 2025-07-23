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
from rasterio.features import rasterize
import numpy as np
import geopandas as gpd
from .constants import print_crs_info, EPSG_27700_WKT

def buffer_and_rasterize(shp_path, ref_raster_path, breaks, scores, reverse=False, out_path="buffered.tif"):
    gdf = gpd.read_file(shp_path)
    print_crs_info(f"Buffered input vector {shp_path}", gdf.crs)

    with rasterio.open(ref_raster_path) as ref:
        print_crs_info(f"Reference raster {ref_raster_path}", ref.crs)
        transform = ref.transform
        out_shape = (ref.height, ref.width)
        profile = ref.profile

    # 将矢量重投影到目标WKT
    gdf = gdf.to_crs(EPSG_27700_WKT)

    distance = [0] + breaks
    classes = scores if not reverse else scores[::-1]
    result = np.zeros(out_shape, dtype=np.float32)

    for i in range(len(distance) - 1):
        d1, d2 = distance[i], distance[i + 1]
        buffered = gdf.buffer(d2).difference(gdf.buffer(d1))
        geoms = [geom for geom in buffered if geom.is_valid]

        if not geoms:
            continue

        mask_layer = rasterize(
            [(geom, classes[i]) for geom in geoms],
            out_shape=out_shape,
            transform=transform,
            fill=0,
            dtype=np.float32
        )
        result = np.maximum(result, mask_layer)

    # 添加透明通道
    alpha_band = (result > 0).astype(np.uint8) * 255
    output_data = np.stack([result, alpha_band], axis=0)

    profile.update(
        dtype=rasterio.float32,
        nodata=0,
        crs=rasterio.crs.CRS.from_wkt(EPSG_27700_WKT),
        count=2
    )

    print_crs_info(f"Output buffered raster {out_path}", profile["crs"])

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(output_data)

    return out_path
