import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter.ttk import Progressbar
import raster_processing as rp

class GreenAmmoniaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Green Ammonia Suitability GUI")
        self.inputs = {}

        labels = [
            "Landuse Raster", "DEM Raster", "Solar Raster", "Wind Raster",
            "Roads Shapefile", "Water Shapefile", "Reserves Shapefile", "Boundary Shapefile"
        ]

        for i, label in enumerate(labels):
            tk.Label(root, text=label).grid(row=i, column=0, sticky='e')
            entry = tk.Entry(root, width=60)
            entry.grid(row=i, column=1)
            self.inputs[label] = entry
            tk.Button(root, text="Browse", command=lambda l=label: self.browse_file(l)).grid(row=i, column=2)

        tk.Button(root, text="Run Suitability", command=self.run_threaded).grid(row=len(labels), column=1)

        self.progress = Progressbar(root, orient='horizontal', mode='determinate', length=400)
        self.progress.grid(row=len(labels)+1, column=0, columnspan=3, pady=5)

        self.log_text = scrolledtext.ScrolledText(root, height=15, width=80)
        self.log_text.grid(row=len(labels)+2, column=0, columnspan=3, pady=10)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def set_progress(self, value):
        self.progress["value"] = value
        self.root.update_idletasks()

    def browse_file(self, label):
        path = filedialog.askopenfilename()
        if path:
            self.inputs[label].delete(0, tk.END)
            self.inputs[label].insert(0, path)

    def run_threaded(self):
        threading.Thread(target=self.run).start()

    def run(self):
        try:
            self.set_progress(0)

            landuse = self.inputs["Landuse Raster"].get()
            dem = self.inputs["DEM Raster"].get()
            solar = self.inputs["Solar Raster"].get()
            wind = self.inputs["Wind Raster"].get()
            road = self.inputs["Roads Shapefile"].get()
            water = self.inputs["Water Shapefile"].get()
            reserve = self.inputs["Reserves Shapefile"].get()
            boundary = self.inputs["Boundary Shapefile"].get()

            out_dir = os.path.dirname(landuse)
            ref_raster = landuse

            # 1. 裁剪矢量
            self.log("裁剪道路矢量...")
            road_clip = f"{out_dir}/road_clip.shp"
            if not os.path.exists(road_clip):
                road_clip = rp.clip_vector_to_boundary(road, boundary, road_clip)
            self.set_progress(5)

            self.log("裁剪水体矢量...")
            water_clip = f"{out_dir}/water_clip.shp"
            if not os.path.exists(water_clip):
                water_clip = rp.clip_vector_to_boundary(water, boundary, water_clip)
            self.set_progress(7)

            self.log("裁剪保护区矢量...")
            reserve_clip = f"{out_dir}/reserve_clip.shp"
            if not os.path.exists(reserve_clip):
                reserve_clip = rp.clip_vector_to_boundary(reserve, boundary, reserve_clip)
            self.set_progress(10)

            # 2. 裁剪栅格并处理
            self.log("裁剪土地利用栅格...")
            landuse_crop = f"{out_dir}/landuse_crop.tif"
            if not os.path.exists(landuse_crop):
                landuse_crop = rp.crop_raster_to_boundary(landuse, boundary, landuse_crop)
            self.set_progress(15)

            self.log("重分类土地利用...")
            landuse_reclass = f"{out_dir}/landuse_reclass.tif"
            if not os.path.exists(landuse_reclass):
                landuse_reclass = rp.reclassify_landuse(landuse_crop, landuse_reclass)
            self.set_progress(25)

            self.log("裁剪DEM...")
            dem_crop = f"{out_dir}/dem_crop.tif"
            if not os.path.exists(dem_crop):
                dem_crop = rp.crop_raster_to_boundary(dem, boundary, dem_crop)

            self.log("计算坡度...")
            slope = f"{out_dir}/slope_score.tif"
            if not os.path.exists(slope):
                slope = rp.compute_slope(dem_crop, slope, grid_size=50)
            self.set_progress(40)

            self.log("裁剪太阳能栅格...")
            solar_crop = f"{out_dir}/solar_crop.tif"
            if not os.path.exists(solar_crop):
                solar_crop = rp.crop_raster_to_boundary(solar, boundary, solar_crop)

            self.log("分类太阳能潜力...")
            solar_class = f"{out_dir}/solar_score.tif"
            if not os.path.exists(solar_class):
                solar_class = rp.classify_natural_breaks(solar_crop, solar_class)
            self.set_progress(55)

            self.log("裁剪风能栅格...")
            wind_crop = f"{out_dir}/wind_crop.tif"
            if not os.path.exists(wind_crop):
                wind_crop = rp.crop_raster_to_boundary(wind, boundary, wind_crop)

            self.log("分类风能潜力...")
            wind_class = f"{out_dir}/wind_score.tif"
            if not os.path.exists(wind_class):
                wind_class = rp.classify_natural_breaks(wind_crop, wind_class)
            self.set_progress(70)

            # 3. 矢量缓冲并栅格化
            self.log("道路缓冲并栅格化...")
            road_score = f"{out_dir}/road_score.tif"
            if not os.path.exists(road_score):
                road_score = rp.buffer_and_rasterize(road_clip, ref_raster, [1000, 3000, 5000], out_path=road_score)
            self.set_progress(75)

            self.log("水体缓冲并栅格化...")
            water_score = f"{out_dir}/water_score.tif"
            if not os.path.exists(water_score):
                water_score = rp.buffer_and_rasterize(water_clip, ref_raster, [1000, 3000, 5000], out_path=water_score)
            self.set_progress(80)

            self.log("保护区缓冲并栅格化（负向影响）...")
            reserve_score = f"{out_dir}/reserve_score.tif"
            if not os.path.exists(reserve_score):
                reserve_score = rp.buffer_and_rasterize(reserve_clip, ref_raster, [1000, 3000, 5000], reverse=True, out_path=reserve_score)
            self.set_progress(90)

            # 4. 对齐所有参与叠加的栅格，保证大小和投影一致
            raster_paths = [
                landuse_reclass,
                slope,
                solar_class,
                wind_class,
                road_score,
                water_score,
                reserve_score
            ]
            aligned_rasters = []
            self.log("对齐栅格数据，准备加权叠加...")
            for i, path in enumerate(raster_paths):
                aligned_path = f"{out_dir}/aligned_{i}.tif"
                if not os.path.exists(aligned_path):
                    aligned_path = rp.align_raster_to_template(path, landuse_reclass, aligned_path)
                aligned_rasters.append(aligned_path)
            self.set_progress(95)

            weights = [0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.10]
            self.log("执行加权叠加...")
            result = f"{out_dir}/suitability_score.tif"
            if not os.path.exists(result):
                result = rp.weighted_overlay(aligned_rasters, weights, result)
            self.set_progress(100)

            self.log(f"\n✔️ 适宜性地图已生成：{result}")
            messagebox.showinfo("成功", f"适宜性地图已生成：{result}")

        except Exception as e:
            self.log(f"❌ 错误: {str(e)}")
            messagebox.showerror("错误", str(e))
            self.set_progress(0)


if __name__ == '__main__':
    root = tk.Tk()
    app = GreenAmmoniaApp(root)
    root.mainloop()
