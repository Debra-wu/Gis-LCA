import os
import rasterio
from rasterio.features import rasterize
from rasterio.mask import mask
from rasterio.warp import reproject, Resampling
import numpy as np
import geopandas as gpd
from shapely.geometry import mapping
from sklearn.cluster import KMeans


def print_crs_info(name, crs):
    print(f"[INFO] {name} CRS: {crs}")


def crop_raster_to_boundary(raster_path, boundary_shp, out_path):
    try:
        with rasterio.open(raster_path) as src:
            print_crs_info(f"裁剪输入栅格 {raster_path}", src.crs)

        gdf = gpd.read_file(boundary_shp)
        print_crs_info(f"边界矢量 {boundary_shp}", gdf.crs)

        if gdf.empty:
            raise ValueError("边界矢量为空！")

        geoms = [mapping(geom) for geom in gdf.geometry if geom.is_valid]

        with rasterio.open(raster_path) as src:
            out_image, out_transform = mask(src, geoms, crop=True)
            out_meta = src.meta.copy()

            if src.nodata is None or np.isnan(src.nodata):
                nodata_val = 0
                out_image = np.where(np.isnan(out_image), nodata_val, out_image)
            else:
                nodata_val = src.nodata

            if not np.any(out_image != nodata_val):
                raise ValueError("裁剪后无有效数据（全为 nodata）")

            out_meta.update({
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "nodata": nodata_val,
                "dtype": out_image.dtype,
                "crs": src.crs  # 强制赋予坐标系
            })

            print_crs_info(f"输出裁剪栅格 {out_path}", out_meta["crs"])

            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with rasterio.open(out_path, "w", **out_meta) as dest:
                dest.write(out_image)

        return out_path

    except Exception as e:
        raise RuntimeError(f"裁剪失败: {e}")


def clip_vector_to_boundary(vector_path, boundary_shp, out_path):
    gdf = gpd.read_file(vector_path)
    print_crs_info(f"矢量数据 {vector_path}", gdf.crs)

    boundary = gpd.read_file(boundary_shp)
    print_crs_info(f"边界矢量 {boundary_shp}", boundary.crs)

    if gdf.empty:
        raise ValueError(f"矢量数据{vector_path}为空！")
    if boundary.empty:
        raise ValueError(f"边界矢量{boundary_shp}为空！")

    if gdf.crs != boundary.crs:
        gdf = gdf.to_crs(boundary.crs)
        print_crs_info(f"矢量数据重投影至边界矢量 CRS", gdf.crs)

    clipped = gpd.clip(gdf, boundary)

    if clipped.empty:
        raise ValueError(f"裁剪后矢量数据为空！")

    clipped.crs = boundary.crs

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    clipped.to_file(out_path)

    print_crs_info(f"输出裁剪矢量 {out_path}", clipped.crs)

    return out_path


def compute_slope(dem_path, out_path, grid_size):
    with rasterio.open(dem_path) as src:
        print_crs_info(f"输入DEM {dem_path}", src.crs)
        dem = src.read(1).astype(float)
        profile = src.profile
        crs = src.crs

    dx = np.gradient(dem, axis=1) / grid_size
    dy = np.gradient(dem, axis=0) / grid_size
    slope = np.sqrt(dx**2 + dy**2)
    slope_degrees = np.arctan(slope) * (180.0 / np.pi)

    valid_mask = ~np.isnan(slope_degrees)
    breaks = np.percentile(slope_degrees[valid_mask], [25, 50, 75])
    score = np.ones_like(slope_degrees, dtype=np.uint8)
    score[(slope_degrees > breaks[0]) & valid_mask] = 3
    score[(slope_degrees > breaks[1]) & valid_mask] = 2
    score[(slope_degrees > breaks[2]) & valid_mask] = 1

    profile.update(dtype=rasterio.uint8, nodata=0, crs=crs)

    score = np.where(valid_mask, score, 0)

    print_crs_info(f"输出坡度栅格 {out_path}", profile["crs"])

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(score, 1)

    return out_path


def buffer_and_rasterize(shp_path, ref_raster_path, breaks, reverse=False, out_path="buffered.tif"):
    gdf = gpd.read_file(shp_path)
    print_crs_info(f"缓冲输入矢量 {shp_path}", gdf.crs)

    with rasterio.open(ref_raster_path) as ref:
        print_crs_info(f"参考栅格 {ref_raster_path}", ref.crs)
        transform = ref.transform
        out_shape = (ref.height, ref.width)
        profile = ref.profile
        crs = ref.crs

    distance = [0] + breaks
    classes = list(range(len(breaks), 0, -1)) if not reverse else list(range(1, len(breaks) + 1))
    result = np.zeros(out_shape, dtype=np.uint8)

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
            dtype=np.uint8
        )
        result = np.maximum(result, mask_layer)

    profile.update(dtype=rasterio.uint8, nodata=0, crs=crs)

    print_crs_info(f"输出缓冲栅格 {out_path}", profile["crs"])

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(result, 1)

    return out_path


def classify_natural_breaks(raster_path, out_path, n_class=4):
    with rasterio.open(raster_path) as src:
        print_crs_info(f"输入分类栅格 {raster_path}", src.crs)
        data = src.read(1)
        profile = src.profile
        nodata = src.nodata
        crs = src.crs

    valid_mask = (data != nodata) & (~np.isnan(data))
    valid_data = data[valid_mask].reshape(-1, 1)

    if valid_data.size == 0:
        raise ValueError("输入栅格无有效数据用于分类！")

    kmeans = KMeans(n_clusters=n_class, random_state=0).fit(valid_data)
    centers = sorted(kmeans.cluster_centers_.flatten())
    thresholds = [(centers[i] + centers[i + 1]) / 2 for i in range(len(centers) - 1)]

    classified = np.zeros_like(data, dtype=np.uint8)
    for i, t in enumerate(thresholds):
        classified[(data > t) & valid_mask] = i + 2
    classified[(data <= thresholds[0]) & valid_mask] = 1

    profile.update(dtype=rasterio.uint8, nodata=0, crs=crs)

    print_crs_info(f"输出分类栅格 {out_path}", profile["crs"])

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(classified, 1)

    return out_path


def reclassify_landuse(landuse_path, out_path):
    with rasterio.open(landuse_path) as src:
        print_crs_info(f"输入土地利用栅格 {landuse_path}", src.crs)
        data = src.read(1)
        profile = src.profile
        crs = src.crs

    reclass = {
        1: 4, 2: 4,
        3: 3, 4: 3, 5: 3, 6: 3, 7: 3,
        8: 2, 9: 2, 10: 2, 11: 2, 12: 2, 13: 2, 14: 2,
        15: 2, 16: 2, 17: 2, 18: 2, 19: 2,
        20: 5, 21: 5
    }

    out = np.zeros_like(data, dtype=np.uint8)
    for k, v in reclass.items():
        out[data == k] = 6 - v

    profile.update(dtype=rasterio.uint8, nodata=0, crs=crs)

    out = np.where(np.isnan(data), 0, out)

    print_crs_info(f"输出重分类土地利用栅格 {out_path}", profile["crs"])

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(out, 1)

    return out_path


def weighted_overlay(raster_paths, weights, out_path):
    layers = []
    profile = None
    crs = None
    for path in raster_paths:
        with rasterio.open(path) as src:
            print_crs_info(f"加权叠加输入栅格 {path}", src.crs)
            data = src.read(1).astype(float)
            profile = src.profile
            crs = src.crs
            nodata = src.nodata
            data = np.where((data == nodata) | np.isnan(data), 0, data)
            layers.append(data)

    weighted_sum = np.zeros_like(layers[0])
    for i, layer in enumerate(layers):
        weighted_sum += layer * weights[i]

    max_val = np.nanmax(weighted_sum)
    score = (weighted_sum / max_val) * 100 if max_val != 0 else weighted_sum

    profile.update(dtype=rasterio.float32, nodata=0, crs=crs)

    print_crs_info(f"输出加权叠加栅格 {out_path}", profile["crs"])

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(score.astype(np.float32), 1)

    return out_path


def align_raster_to_template(src_path, template_path, out_path, resampling_method=Resampling.nearest):
    """
    将 src_path 栅格对齐（重投影+重采样）到 template_path 的空间范围、分辨率和投影
    """
    if os.path.exists(out_path):
        print_crs_info(f"对齐输出已存在 {out_path}", None)
        return out_path

    with rasterio.open(template_path) as template:
        template_transform = template.transform
        template_crs = template.crs
        template_shape = (template.height, template.width)
        print_crs_info(f"模板栅格 {template_path}", template_crs)

    with rasterio.open(src_path) as src:
        print_crs_info(f"待对齐输入栅格 {src_path}", src.crs)
        data = src.read(1)
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

        print_crs_info(f"输出对齐栅格 {out_path}", profile["crs"])

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with rasterio.open(out_path, 'w', **profile) as dst:
            dst.write(destination, 1)

    return out_path
