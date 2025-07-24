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

import geopandas as gpd
import concurrent.futures
from tqdm import tqdm

from .constants import print_crs_info
from .constants import EPSG_27700_WKT

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
