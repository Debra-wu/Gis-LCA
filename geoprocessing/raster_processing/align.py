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
from rasterio.warp import reproject, Resampling
import numpy as np
from .constants import print_crs_info

def align_raster_to_template(src_path, template_path, out_path, resampling_method=Resampling.nearest):
    """
    将 src_path 栅格对齐（重投影+重采样）到 template_path 的空间范围、分辨率和投影
    """
    if os.path.exists(out_path):
        print_crs_info(f"Aligned output already exists {out_path}", None)
        return out_path

    with rasterio.open(template_path) as template:
        template_transform = template.transform
        template_crs = template.crs
        template_shape = (template.height, template.width)
        print_crs_info(f"Template raster {template_path}", template_crs)

    with rasterio.open(src_path) as src:
        print_crs_info(f"Input raster to be aligned {src_path}", src.crs)
        data = src.read(1)  # 只读取数据波段
        profile = src.profile

        profile.update({
            'height': template_shape[0],
            'width': template_shape[1],
            'transform': template_transform,
            'crs': template_crs
        })

        destination = np.zeros(template_shape, dtype=profile['dtype'])

        reproject(
            source=data,
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=template_transform,
            dst_crs=template_crs,
            resampling=resampling_method
        )

        # 添加透明通道
        alpha_band = (destination > 0).astype(np.uint8) * 255
        output_data = np.stack([destination, alpha_band], axis=0)

        profile.update(
            dtype=rasterio.uint8,
            nodata=0,
            crs=template_crs,
            count=2
        )

        print_crs_info(f"Output aligned raster {out_path}", profile["crs"])

        with rasterio.open(out_path, 'w', **profile) as dst:
            dst.write(output_data)

    return out_path