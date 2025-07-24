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
from rasterio.mask import mask
from rasterio.warp import reproject, Resampling
import numpy as np
import geopandas as gpd
from shapely.geometry import mapping
from sklearn.cluster import KMeans
import concurrent.futures
from tqdm import tqdm

# 定义EPSG:27700的完整WKT字符串
EPSG_27700_WKT = """
PROJCS["OSGB 1936 / British National Grid",
    GEOGCS["OSGB 1936",
        DATUM["OSGB_1936",
            SPHEROID["Airy 1830",6377563.396,299.3249646,
                AUTHORITY["EPSG","7001"]],
            TOWGS84[446.448,-125.157,542.06,0.15,0.247,0.842,-20.489],
            AUTHORITY["EPSG","6277"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.0174532925199433,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4277"]],
    PROJECTION["Transverse_Mercator"],
    PARAMETER["latitude_of_origin",49],
    PARAMETER["central_meridian",-2],
    PARAMETER["scale_factor",0.9996012717],
    PARAMETER["false_easting",400000],
    PARAMETER["false_northing",-100000],
    UNIT["metre",1,
        AUTHORITY["EPSG","9001"]],
    AXIS["Easting",EAST],
    AXIS["Northing",NORTH],
    AUTHORITY["EPSG","27700"]]
"""


def print_crs_info(name, crs):
    print(f"[INFO] {name} CRS: {crs}")


def clip_vector_to_boundary(vector_path, boundary_shp, out_path, use_spatial_index=True, n_threads=4):
    """
    裁剪矢量数据到边界范围内，支持空间索引和多线程优化
    """
    gdf = gpd.read_file(vector_path)
    print_crs_info(f"Vector data {vector_path}", gdf.crs)

    boundary = gpd.read_file(boundary_shp)
    print_crs_info(f"Boundary Vector {boundary_shp}", boundary.crs)

    if gdf.empty:
        raise ValueError(f"Vector data{vector_path}is empty！")
    if boundary.empty:
        raise ValueError(f"Boundary Vector{boundary_shp}is empty！")

    # 统一使用WKT进行坐标转换
    if gdf.crs != boundary.crs:
        try:
            # 尝试将矢量重投影到边界CRS
            gdf = gdf.to_crs(boundary.crs)
            print_crs_info(f"Reprojected vector data to boundary CRS", gdf.crs)
        except:
            # 转换失败时强制使用目标WKT
            print(f"[WARNING] Failed to convert directly, forcefully using EPSG:27700 WKT")
            gdf = gdf.to_crs(EPSG_27700_WKT)
            boundary = boundary.to_crs(EPSG_27700_WKT)

    # 合并所有边界为单个几何对象
    boundary_geom = boundary.geometry.unary_union

    # 使用空间索引筛选可能相交的要素
    if use_spatial_index and len(gdf) > 100:  # 要素数量较少时可能不需要空间索引
        print("[INFO] Using R-Tree spatial index to accelerate clipping...")
        spatial_index = gdf.sindex
        possible_matches_index = list(spatial_index.intersection(boundary_geom.bounds))
        possible_matches = gdf.iloc[possible_matches_index]

        # 精确筛选
        precise_matches = possible_matches[possible_matches.intersects(boundary_geom)]
    else:
        print("[INFO] Spatial index not used, clipping directly...")
        precise_matches = gdf[gdf.intersects(boundary_geom)]

    def clip_geometry(row):
        """对单个几何对象进行裁剪"""
        try:
            return row.geometry.intersection(boundary_geom)
        except Exception as e:
            print(f"[WARNING] Error occurred while clipping geometry: {e}")
            return None

    # 使用多线程并行处理几何对象
    if n_threads > 1 and len(precise_matches) > 100:
        print(f"[INFO] Using{min(n_threads, os.cpu_count() or 1)}threads for parallel clipping...")
        clipped_geometries = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(n_threads, os.cpu_count() or 1)) as executor:
            # 提交任务
            future_to_idx = {executor.submit(clip_geometry, row): idx
                             for idx, row in precise_matches.iterrows()}

            # 收集结果
            for future in tqdm(concurrent.futures.as_completed(future_to_idx),
                               total=len(future_to_idx), desc="Clipping progress"):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                    if result and not result.is_empty:
                        clipped_geometries.append((idx, result))
                except Exception as e:
                    print(f"[ERROR] Error occurred in thread execution: {e}")

        # 重新构建GeoDataFrame
        if clipped_geometries:
            indices, geometries = zip(*clipped_geometries)
            clipped = precise_matches.loc[list(indices)].copy()
            clipped['geometry'] = geometries
        else:
            clipped = gpd.GeoDataFrame(columns=precise_matches.columns, geometry=[])
    else:
        # 单线程处理
        print("[INFO] Clipping using single thread...")
        clipped = precise_matches.copy()
        valid_geometries = []

        for idx, row in tqdm(clipped.iterrows(), total=len(clipped), desc="Clipping progress"):
            geom = clip_geometry(row)
            if geom and not geom.is_empty:
                valid_geometries.append(geom)
            else:
                valid_geometries.append(None)

        # 过滤无效几何对象
        clipped['geometry'] = valid_geometries
        clipped = clipped.dropna(subset=['geometry'])

    if clipped.empty:
        raise ValueError(f"Vector data is empty after clipping!")

    # 设置输出CRS为EPSG:27700（使用WKT）
    clipped = clipped.to_crs(EPSG_27700_WKT)
    print_crs_info(f"Output clipped vector {out_path}", clipped.crs)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    clipped.to_file(out_path)

    return out_path


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