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
from rasterio.mask import mask
import numpy as np
import geopandas as gpd
from .constants import EPSG_27700_WKT

def crop_raster_to_boundary(input_raster, boundary_shp, output_raster):
    """
    裁剪栅格数据到边界范围内，使用完整WKT字符串定义坐标系，并添加透明通道
    """
    try:
        with rasterio.open(input_raster) as src:
            # 读取边界矢量
            boundary = gpd.read_file(boundary_shp)

            # 打印栅格和边界的原始CRS信息（用于调试）
            print(f"Original CRS of raster: {src.crs}")
            print(f"Original CRS of boundary: {boundary.crs}")

            # 将边界重投影到目标WKT
            print(f"Reprojecting boundary to OSGB 1936/ British National Grid")
            boundary = boundary.to_crs(EPSG_27700_WKT)

            # 提取边界几何
            geom = boundary.geometry.unary_union

            # 使用mask函数裁剪栅格
            out_image, out_transform = mask(
                src,
                [geom],
                crop=True,
                all_touched=True,
                nodata=src.nodata
            )

            # 获取原始栅格的元数据
            out_meta = src.meta.copy()

            # 更新元数据中的变换参数、尺寸和CRS（使用WKT）
            out_meta.update({
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "nodata": src.nodata,
                "crs": rasterio.crs.CRS.from_wkt(EPSG_27700_WKT)
            })

            # 确保数据类型与原始一致
            if src.dtypes[0] in ['uint8', 'int8', 'uint16', 'int16']:
                if out_image.dtype != src.dtypes[0]:
                    if np.all(np.mod(out_image, 1) == 0):
                        out_image = out_image.astype(src.dtypes[0])
                    else:
                        print(f"Warning: Cropped data contains decimal values, cannot safely convert back to type{src.dtypes[0]}")
                out_meta.update({"dtype": src.dtypes[0]})

            # **添加透明通道**
            alpha_band = np.ones((out_image.shape[1], out_image.shape[2]), dtype=np.uint8) * 255
            for i in range(out_image.shape[0]):
                alpha_band[out_image[i] == src.nodata] = 0

            # 将透明通道添加到输出图像
            out_image = np.vstack((out_image, alpha_band[np.newaxis, :, :]))

            # 更新波段数
            out_meta.update({"count": out_image.shape[0]})

            # 写入裁剪后的栅格
            with rasterio.open(output_raster, "w", **out_meta) as dest:
                dest.write(out_image)

        print(f"Raster cropping completed: {output_raster} (OSGB 1936 / British National Grid)")
        return output_raster

    except Exception as e:
        print(f"Error occurs while raster cropping: {str(e)}")
        raise e
