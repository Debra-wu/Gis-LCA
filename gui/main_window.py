import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from geoprocessing import raster_processing as rp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
import rasterio
from matplotlib.colors import LinearSegmentedColormap
import geopandas as gpd
from matplotlib.patches import Patch
import json
import os

# 增强中文字体兼容性
plt.rcParams["font.family"] = ["Microsoft YaHei", "SimHei", "WenQuanYi Micro Hei", "Heiti TC"]


class GreenAmmoniaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Green Ammonia Siting Analysis Tool")
        self.inputs = {}
        self.result_path = None
        self.preserved_inputs = {}

        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 输入文件选择区域
        input_frame = ttk.LabelFrame(main_frame, text="Input Data", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        labels = [
            "Land Use Raster", "DEM Raster", "Solar Raster", "Wind Raster",
            "Road Vector", "Water Vector", "Protected Area Vector", "Boundary Vector"
        ]

        for i, label in enumerate(labels):
            ttk.Label(input_frame, text=label).grid(row=i, column=0, sticky='e', pady=2)
            entry = ttk.Entry(input_frame, width=60)
            entry.grid(row=i, column=1, pady=2)
            self.inputs[label] = entry
            ttk.Button(input_frame, text="Browse", command=lambda l=label: self.browse_file(l)).grid(row=i, column=2,
                                                                                                   padx=5)

        # 权重输入区域
        weight_frame = ttk.LabelFrame(main_frame, text="Factor Weights", padding="10")
        weight_frame.pack(fill=tk.X, pady=5)

        weight_labels = [
            "Land Use Weight", "Slope Weight", "Solar Weight", "Wind Weight",
            "Road Weight", "Water Weight", "Protected Area Weight"
        ]
        self.weight_entries = {}
        for i, label in enumerate(weight_labels):
            ttk.Label(weight_frame, text=label).grid(row=i, column=0, sticky='e', pady=2)
            entry = ttk.Entry(weight_frame, width=10)
            entry.insert(0, "0.15" if i < 6 else "0.10")
            entry.grid(row=i, column=1, pady=2)
            self.weight_entries[label] = entry

        self.try_load_saved_weights()

        # 按钮区域
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="Run Suitability Analysis", command=self.run_threaded).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Show Result Map", command=self.show_result_map).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Recalculate All", command=self.recalculate_all_threaded).pack(side=tk.LEFT, padx=5)

        # 进度条
        self.progress = ttk.Progressbar(main_frame, orient='horizontal', mode='determinate', length=400)
        self.progress.pack(fill=tk.X, pady=5)

        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="Processing Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=5, width=80)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 存储当前地图数据
        self.current_data = None
        self.current_transform = None
        self.current_cmap = LinearSegmentedColormap.from_list(
            "suitability", ["red", "yellow", "green"]
        )

        # 地图窗口相关变量
        self.map_window = None
        self.map_canvas = None
        self.map_figure = None
        self.map_ax = None
        self.map_colorbar = None
        self.map_im = None
        self.threshold_var = tk.DoubleVar(value=50)
        self.map_extent = None
        self.boundary_data = None

    def try_load_saved_weights(self):
        try:
            weights_path = os.path.join(os.path.dirname(__file__), "..", "ahp", "weights.json")
            weights_path = os.path.abspath(weights_path)

            if os.path.exists(weights_path):
                with open(weights_path, "r", encoding="utf-8") as f:
                    weights = json.load(f)
                self.receive_ahp_weights(weights)
                self.log("✅ Successfully loaded previous AHP weights")
            else:
                self.log("ℹ️ No AHP weight file found, using manual input")
        except Exception as e:
            self.log(f"⚠️ Failed to load AHP weights: {str(e)}")

    def receive_ahp_weights(self, weights_dict):
        self.log("✅ Already received AHP weights：")
        self.log(str(weights_dict))

        mapping = {
            "Land Use": "Land Use Weight",
            "Slope": "Slope Weight",
            "Solar Energy": "Solar Weight",
            "Wind Energy": "Wind Weight",
            "Road Access": "Road Weight",
            "Water System": "Water Weight",
            "Protected Area": "Protected Area Weight"
        }

        for key, label in mapping.items():
            if label in self.weight_entries and key in weights_dict:
                self.weight_entries[label].delete(0, tk.END)
                self.weight_entries[label].insert(0, str(weights_dict[key]))
                self.weight_entries[label].config(state='readonly')

    def log(self, message):
        self.root.after(0, lambda: self._update_log(message))

    def _update_log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def set_progress(self, value):
        self.root.after(0, lambda: self._update_progress(value))

    def _update_progress(self, value):
        self.progress["value"] = value

    def browse_file(self, label):
        path = filedialog.askopenfilename()
        if path:
            self.inputs[label].delete(0, tk.END)
            self.inputs[label].insert(0, path)

    def save_input_values(self):
        for label, entry in self.inputs.items():
            self.preserved_inputs[label] = entry.get()
        for label, entry in self.weight_entries.items():
            self.preserved_inputs[f"weight_{label}"] = entry.get()

    def restore_input_values(self):
        for label, entry in self.inputs.items():
            if label in self.preserved_inputs:
                entry.delete(0, tk.END)
                entry.insert(0, self.preserved_inputs[label])
        for label, entry in self.weight_entries.items():
            key = f"weight_{label}"
            if key in self.preserved_inputs:
                entry.delete(0, tk.END)
                entry.insert(0, self.preserved_inputs[key])

    def run_threaded(self):
        self.save_input_values()
        self._set_inputs_state("disabled")
        threading.Thread(target=self.run).start()

    def recalculate_all_threaded(self):
        """全部重新计算按钮的线程处理函数"""
        if messagebox.askyesno("Confirm", "Are you sure you want to delete all intermediate results and recalculate? This action cannot be undone."):
            self.save_input_values()
            self._set_inputs_state("disabled")
            threading.Thread(target=self.run, kwargs={"recalculate_all": True}).start()

    def _set_inputs_state(self, state):
        for entry in self.inputs.values():
            entry.config(state=state)
        for entry in self.weight_entries.values():
            entry.config(state=state)

    def run(self, recalculate_all=False):
        try:
            self.set_progress(0)
            self.log("Starting suitability analysis...")

            # 获取输入文件路径
            landuse = self.inputs["Land Use Raster"].get()
            dem = self.inputs["DEM Raster"].get()
            solar = self.inputs["Solar Raster"].get()
            wind = self.inputs["Wind Raster"].get()
            road = self.inputs["Road Vector"].get()
            water = self.inputs["Water Vector"].get()
            reserve = self.inputs["Protected Area Vector"].get()
            boundary = self.inputs["Boundary Vector"].get()

            # 验证输入文件是否存在
            input_files = [landuse, dem, solar, wind, road, water, reserve, boundary]
            for file in input_files:
                if not file or not os.path.exists(file):
                    raise ValueError(f"Input file does not exist: {file}")

            # 获取用户输入的权重并验证
            try:
                weights = [float(self.weight_entries[label].get()) for label in self.weight_entries]
                if not all(0 <= w <= 1 for w in weights):
                    raise ValueError("Value of weights must be between 0 and 1")
                if not np.isclose(sum(weights), 1.0, atol=0.01):
                    self.log(f"⚠️ Warning: sum of weights{sum(weights):.2f}，should be adjusted to 1.0")
            except ValueError as e:
                raise ValueError(f"Wrong weight input: {str(e)}")

            # 输出目录设置
            out_dir = os.path.dirname(landuse)
            ref_raster = landuse
            self.log(f"Output directory: {out_dir}")

            # 如果选择全部重新计算，删除所有中间结果文件
            if recalculate_all:
                self.log("\n===== Delete All Intermediate Results =====")
                self.delete_intermediate_results(out_dir)
                self.set_progress(5)

            # 1. 裁剪矢量
            self.log("\n===== Start clipping vectors =====")
            road_clip = f"{out_dir}/road_clip.shp"
            if os.path.exists(road_clip) and os.path.getsize(road_clip) > 0 and not recalculate_all:
                self.log(f"✅ Road clipping result already exists, skipping: {road_clip}")
            else:
                self.log("Clipping road vector...")
                road_clip = rp.clip_vector_to_boundary(road, boundary, road_clip)
            self.set_progress(10)

            water_clip = f"{out_dir}/water_clip.shp"
            if os.path.exists(water_clip) and os.path.getsize(water_clip) > 0 and not recalculate_all:
                self.log(f"✅ Water clipping result already exists, skipping: {water_clip}")
            else:
                self.log("Clipping water vector...")
                water_clip = rp.clip_vector_to_boundary(water, boundary, water_clip)
            self.set_progress(15)

            reserve_clip = f"{out_dir}/reserve_clip.shp"
            if os.path.exists(reserve_clip) and os.path.getsize(reserve_clip) > 0 and not recalculate_all:
                self.log(f"✅ Protected area clipping result already exists, skipping: {reserve_clip}")
            else:
                self.log("Clipping protected area vector...")
                reserve_clip = rp.clip_vector_to_boundary(reserve, boundary, reserve_clip)
            self.set_progress(20)

            # 2. 裁剪栅格并处理
            self.log("\n===== Start raster processing  =====")
            landuse_crop = f"{out_dir}/landuse_crop.tif"
            if os.path.exists(landuse_crop) and os.path.getsize(landuse_crop) > 0 and not recalculate_all:
                self.log(f"✅ Land use crop already exists, skipping: {landuse_crop}")
            else:
                self.log("Cropping land use raster...")
                landuse_crop = rp.crop_raster_to_boundary(landuse, boundary, landuse_crop)
            self.set_progress(25)

            landuse_reclass = f"{out_dir}/landuse_reclass.tif"
            if os.path.exists(landuse_reclass) and os.path.getsize(landuse_reclass) > 0 and not recalculate_all:
                self.log(f"✅ Land use reclassification already exists, skipping: {landuse_reclass}")
            else:
                self.log("Reclassifying land use...")
                landuse_reclass = rp.reclassify_landuse(landuse_crop, landuse_reclass)
            self.set_progress(35)

            dem_crop = f"{out_dir}/dem_crop.tif"
            if os.path.exists(dem_crop) and os.path.getsize(dem_crop) > 0 and not recalculate_all:
                self.log(f"✅ DEM crop already exists, skipping: {dem_crop}")
            else:
                self.log("Cropping DEM...")
                dem_crop = rp.crop_raster_to_boundary(dem, boundary, dem_crop)

            slope = f"{out_dir}/slope_score.tif"
            if os.path.exists(slope) and os.path.getsize(slope) > 0 and not recalculate_all:
                self.log(f"✅ Slope computation already exists, skipping: {slope}")
            else:
                self.log("Computing slope...")
                slope = rp.compute_slope(dem_crop, slope, grid_size=50)
            self.set_progress(50)

            solar_crop = f"{out_dir}/solar_crop.tif"
            if os.path.exists(solar_crop) and os.path.getsize(solar_crop) > 0 and not recalculate_all:
                self.log(f"✅ Solar crop already exists, skipping: {solar_crop}")
            else:
                self.log("Cropping solar raster...")
                solar_crop = rp.crop_raster_to_boundary(solar, boundary, solar_crop)

            solar_class = f"{out_dir}/solar_score.tif"
            if os.path.exists(solar_class) and os.path.getsize(solar_class) > 0 and not recalculate_all:
                self.log(f"✅ Solar classification already exists, skipping: {solar_class}")
            else:
                self.log("Classifying solar potential...")
                solar_class = rp.classify_natural_breaks(solar_crop, solar_class)
            self.set_progress(65)

            wind_crop = f"{out_dir}/wind_crop.tif"
            if os.path.exists(wind_crop) and os.path.getsize(wind_crop) > 0 and not recalculate_all:
                self.log(f"✅ Wind crop already exists, skipping: {wind_crop}")
            else:
                self.log("Cropping wind raster...")
                wind_crop = rp.crop_raster_to_boundary(wind, boundary, wind_crop)

            wind_class = f"{out_dir}/wind_score.tif"
            if os.path.exists(wind_class) and os.path.getsize(wind_class) > 0 and not recalculate_all:
                self.log(f"✅ Wind classification already exists, skipping: {wind_class}")
            else:
                self.log("Classifying wind potential...")
                wind_class = rp.classify_natural_breaks(wind_crop, wind_class)
            self.set_progress(80)

            # 3. 矢量缓冲并栅格化
            self.log("\n===== Start buffer analysis =====")
            road_score = f"{out_dir}/road_score.tif"
            road_breaks = [1000, 3000, 5000]
            road_scores = [1, 0.8, 0.5, 0.2]
            if os.path.exists(road_score) and os.path.getsize(road_score) > 0 and not recalculate_all:
                self.log(f"✅ Road buffer result already exists, skipping: {road_score}")
            else:
                self.log("Buffering and rasterizing road...")
                road_score = rp.buffer_and_rasterize(road_clip, ref_raster, road_breaks, road_scores,
                                                     out_path=road_score)
            self.set_progress(85)

            water_score = f"{out_dir}/water_score.tif"
            water_breaks = [500, 1000, 2000]
            water_scores = [1, 0.8, 0.6, 0.3]
            if os.path.exists(water_score) and os.path.getsize(water_score) > 0 and not recalculate_all:
                self.log(f"✅ Water buffer result already exists, skipping: {water_score}")
            else:
                self.log("Buffering and rasterizing water...")
                water_score = rp.buffer_and_rasterize(water_clip, ref_raster, water_breaks, water_scores,
                                                      out_path=water_score)
            self.set_progress(90)

            reserve_score = f"{out_dir}/reserve_score.tif"
            reserve_breaks = [1000, 2000, 5000]
            reserve_scores = [0, 0.2, 0.6, 1]
            if os.path.exists(reserve_score) and os.path.getsize(reserve_score) > 0 and not recalculate_all:
                self.log(f"✅ Protected area buffer result already exists, skipping: {reserve_score}")
            else:
                self.log("Buffering and rasterizing protected area (negative impact)...")
                reserve_score = rp.buffer_and_rasterize(reserve_clip, ref_raster, reserve_breaks, reserve_scores,
                                                        reverse=True, out_path=reserve_score)
            self.set_progress(95)

            # 4. 栅格对齐
            self.log("\n===== Start raster alignment =====")
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
            for i, path in enumerate(raster_paths):
                aligned_path = f"{out_dir}/aligned_{i}.tif"
                if os.path.exists(aligned_path) and os.path.getsize(aligned_path) > 0 and not recalculate_all:
                    self.log(f"✅ Aligned raster {i} already exists, skipping: {aligned_path}")
                    aligned_rasters.append(aligned_path)
                    continue
                self.log(f"Aligning raster {i}...")
                aligned_path = rp.align_raster_to_template(path, landuse_reclass, aligned_path)
                aligned_rasters.append(aligned_path)
            self.set_progress(98)

            # 5. 加权叠加
            self.log("\n===== Start weighted overlay =====")
            result = f"{out_dir}/suitability_score.tif"
            if os.path.exists(result) and os.path.getsize(result) > 0 and not recalculate_all:
                self.log(f"✅ Suitability result already exists, skipping: {result}")
            else:
                self.log("Performing weighted overlay...")
                result = rp.weighted_overlay(aligned_rasters, weights, result)
            self.set_progress(100)

            # 保存结果路径
            self.result_path = result

            self.log(f"\n✔️ Suitability analysis completed! Result file: {result}")
            # 修复成功提示的闭包变量引用
            self.root.after(0, lambda res=result: messagebox.showinfo("成功", f"Suitability map generated：{res}"))

        except Exception as e:
            # 修复异常处理的闭包变量引用（核心修复点）
            self.root.after(0, lambda error=str(e): self._handle_error(error))
        finally:
            self.root.after(0, self._restore_ui_state)

    def delete_intermediate_results(self, out_dir):
        """删除所有中间结果文件"""
        try:
            if not os.path.exists(out_dir):
                return

            files_to_delete = [
                "road_clip.shp", "road_clip.shx", "road_clip.dbf", "road_clip.prj",
                "water_clip.shp", "water_clip.shx", "water_clip.dbf", "water_clip.prj",
                "reserve_clip.shp", "reserve_clip.shx", "reserve_clip.dbf", "reserve_clip.prj",
                "landuse_crop.tif", "landuse_reclass.tif",
                "dem_crop.tif", "slope_score.tif",
                "solar_crop.tif", "solar_score.tif",
                "wind_crop.tif", "wind_score.tif",
                "road_score.tif", "water_score.tif", "reserve_score.tif"
            ]

            # 添加对齐栅格文件
            for i in range(7):
                files_to_delete.append(f"aligned_{i}.tif")

            deleted_count = 0
            for file in files_to_delete:
                file_path = os.path.join(out_dir, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.log(f"Deleted: {file_path}")
                    deleted_count += 1

            self.log(f"Total {deleted_count} intermediate files deleted")

        except Exception as e:
            self.log(f"Error occurred while deleting intermediate files: {str(e)}")
            messagebox.showerror("Error", f"Error occurred while deleting intermediate files: {str(e)}")

    def _handle_error(self, error_msg):
        self.log(f"❌ Error: {error_msg}")
        messagebox.showerror("Error", error_msg)

    def _restore_ui_state(self):
        self.restore_input_values()
        self._set_inputs_state("normal")
        self.set_progress(0)

    def show_result_map(self):
        if not self.result_path or not os.path.exists(self.result_path):
            messagebox.showwarning("Warning", "Please run the suitability analysis to generate the result map first")
            return

        try:
            # 获取边界数据路径
            boundary_path = self.inputs["Boundary vector"].get()
            if not boundary_path or not os.path.exists(boundary_path):
                messagebox.showwarning("Warning", "Boundary vector file does not exist, please check your input")
                return

            # 读取边界数据
            self.log("Loading boundary data...")
            self.boundary_data = gpd.read_file(boundary_path)

            with rasterio.open(self.result_path) as src:
                data = src.read(1)
                transform = src.transform
                self.current_data = data
                self.current_transform = transform

                # 计算地理边界范围
                left = transform.c
                right = transform.c + transform.a * src.width
                bottom = transform.f + transform.e * src.height
                top = transform.f
                self.map_extent = (left, right, bottom, top)

                # 创建弹出窗口
                self.create_map_window()

                # 显示栅格数据和边界
                self.update_map_display()

                self.log("Suitability map and boundary displayed in a new window")

        except Exception as e:
            # 修复异常处理的闭包变量引用
            self.log(f"❌ Error occurs while map visualization: {str(e)}")
            messagebox.showerror("Error", f"Error occurs while map visualization: {str(e)}")

    def create_map_window(self):
        if self.map_window and self.map_window.winfo_exists():
            self.map_window.destroy()

        self.map_window = tk.Toplevel(self.root)
        self.map_window.title("Suitability Analysis Map of Green Ammonia Plant")
        self.map_window.geometry("1000x800")

        main_frame = ttk.Frame(self.map_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        map_frame = ttk.LabelFrame(main_frame, text="Suitability Map", padding="10")
        map_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.map_figure, self.map_ax = plt.subplots(figsize=(8, 6))
        self.map_figure.subplots_adjust(left=0.1, right=0.9, bottom=0.1, top=0.9)
        self.map_canvas = FigureCanvasTkAgg(self.map_figure, master=map_frame)
        self.map_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar_frame = ttk.Frame(map_frame)
        toolbar_frame.pack(fill=tk.X, pady=5)
        toolbar = NavigationToolbar2Tk(self.map_canvas, toolbar_frame)
        toolbar.update()

        filter_frame = ttk.LabelFrame(main_frame, text="Score Filter", padding="10")
        filter_frame.pack(fill=tk.X, pady=5)

        ttk.Label(filter_frame, text="Score Threshold:").pack(side=tk.LEFT, padx=5)
        threshold_entry = ttk.Entry(filter_frame, width=10, textvariable=self.threshold_var)
        threshold_entry.pack(side=tk.LEFT, padx=5)
        threshold_scale = ttk.Scale(
            filter_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=300,
            variable=self.threshold_var,
            command=lambda s: self.threshold_var.set(round(float(s), 1))
        )
        threshold_scale.pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Apply Threshold", command=self.apply_threshold).pack(side=tk.LEFT, padx=5)
        # 拆分导出按钮为栅格和矢量
        ttk.Button(filter_frame, text="Export Raster", command=self.export_filtered_raster).pack(side=tk.LEFT, padx=5)
        # ttk.Button(filter_frame, text="导出矢量", command=self.export_filtered_vector).pack(side=tk.LEFT, padx=5)

        self.map_window.protocol("WM_DELETE_WINDOW", self.on_map_window_close)

    def update_map_display(self, threshold=None):
        self.map_ax.clear()

        if self.map_colorbar is not None:
            try:
                self.map_colorbar.remove()
            except Exception:
                pass
            self.map_colorbar = None

        if threshold is not None and self.current_data is not None:
            masked_data = np.ma.masked_where(self.current_data < threshold, self.current_data)
            data_to_display = masked_data
            self.map_ax.set_title(f"Suitability Map of Green Ammonia Plant (Threshold ≥ {threshold})")
        else:
            data_to_display = self.current_data
            self.map_ax.set_title("Suitability Map of Green Ammonia Plant")

        # 显示栅格数据
        self.map_im = self.map_ax.imshow(
            data_to_display,
            cmap=self.current_cmap,
            vmin=0,
            vmax=100,
            extent=self.map_extent,
            origin='upper'
        )

        # 显示边界数据
        if self.boundary_data is not None:
            self.boundary_data.plot(
                ax=self.map_ax,
                facecolor='none',
                edgecolor='black',
                linewidth=1.5,
                alpha=0.8
            )

        # 添加颜色条
        cbar_ax = self.map_figure.add_axes([0.92, 0.15, 0.03, 0.7])
        self.map_colorbar = self.map_figure.colorbar(self.map_im, cax=cbar_ax)
        self.map_colorbar.set_label('Suitability Score')

        # 图例位置在右下角（避免遮挡）
        legend_items = [Patch(facecolor='none', edgecolor='black', label='Study Area Boundary')]
        self.map_ax.legend(handles=legend_items, loc='lower right')

        # 锁定轴范围
        self.map_ax.set_xlim(self.map_extent[0], self.map_extent[1])
        self.map_ax.set_ylim(self.map_extent[2], self.map_extent[3])

        # 关闭坐标轴显示
        self.map_ax.set_axis_off()

        # 更新画布
        self.map_canvas.draw()

        # 计算并显示统计信息
        if threshold is not None and self.current_data is not None:
            valid_data = self.current_data[self.current_data >= threshold]
            if valid_data.size > 0:
                percent_above_threshold = (valid_data.size / self.current_data.size) * 100
                self.log(f"Area ratio with score ≥ {threshold} : {percent_above_threshold:.2f}%")
                self.log(f"Average score for area ≥ {threshold}: {np.mean(valid_data):.2f}")
            else:
                self.log(f"No area meets the threshold ≥ {threshold} ")

    def apply_threshold(self):
        try:
            threshold = float(self.threshold_var.get())
            if 0 <= threshold <= 100:
                self.update_map_display(threshold)
            else:
                messagebox.showerror("Error", "Threshold must be between 0 and 100")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid threshold")

    def export_filtered_raster(self):
        """单独导出过滤后的栅格"""
        try:
            threshold = float(self.threshold_var.get())
            if not (0 <= threshold <= 100):
                messagebox.showerror("Error", "Threshold must be between 0 and 100")
                return

            if self.current_data is None:
                messagebox.showerror("Error", "No valid data to export")
                return

            # 应用阈值过滤
            masked_data = np.where(self.current_data < threshold, 0, self.current_data)

            # 选择保存路径
            raster_out_path = filedialog.asksaveasfilename(
                defaultextension=".tif",
                filetypes=[("TIFF Files", "*.tif"), ("All Files", "*.*")]
            )
            if not raster_out_path:
                return  # 用户取消选择

            # 保存栅格
            with rasterio.open(self.result_path) as src:
                profile = src.profile
                profile.update(
                    dtype=rasterio.float32,
                    nodata=0,
                    count=1  # 确保单波段输出
                )
                with rasterio.open(raster_out_path, 'w', **profile) as dst:
                    dst.write(masked_data.astype(np.float32), 1)

            self.log(f"✅ Filtered raster exported to: {raster_out_path}")
            messagebox.showinfo("Success", f"Raster exported successfully: {raster_out_path}")

        except Exception as e:
            self.log(f"❌ Failed to export raster: {str(e)}")
            messagebox.showerror("Error", f"Failed to export raster: {str(e)}")

    def export_filtered_vector(self):
        """单独导出过滤后的矢量（修复版）"""
        try:
            threshold = float(self.threshold_var.get())
            if not (0 <= threshold <= 100):
                messagebox.showerror("Error", "Threshold must be between 0 and 100")
                return

            if self.current_data is None:
                messagebox.showerror("Error", "No valid data to export")
                return

            # 应用阈值过滤（仅保留符合条件的区域）
            masked_data = np.where(self.current_data >= threshold, self.current_data, 0)

            # 选择保存路径
            vector_out_path = filedialog.asksaveasfilename(
                defaultextension=".shp",
                filetypes=[("Shapefile", "*.shp"), ("All Files", "*.*")]
            )
            if not vector_out_path:
                return  # 用户取消选择

            # 栅格转矢量（使用rasterio.features.shapes）
            with rasterio.open(self.result_path) as src:
                # 生成矢量形状（仅保留值>0的区域）
                shapes = rasterio.features.shapes(
                    masked_data.astype(np.float32),
                    mask=masked_data > 0,  # 仅转换有值的区域
                    transform=src.transform
                )

                # 提取几何和属性
                geometries = []
                values = []
                for geom, value in shapes:
                    geometries.append(geom)
                    values.append(round(value, 2))  # 保留2位小数

                # 创建GeoDataFrame并保存
                gdf = gpd.GeoDataFrame(
                    {'suitability': values},  # 适宜性分数作为属性
                    geometry=geometries,
                    crs=src.crs  # 继承原栅格的坐标系统
                )
                gdf.to_file(vector_out_path)

            self.log(f"✅ Filtered vector exported to: {vector_out_path}")
            messagebox.showinfo("Success", f"Vector exported successfully: {vector_out_path}")

        except Exception as e:
            self.log(f"❌ Failed to export vector: {str(e)}")
            messagebox.showerror("Error", f"Failed to export vector: {str(e)}")

    def on_map_window_close(self):
        if self.map_window:
            plt.close(self.map_figure)
            self.map_window.destroy()
            self.map_window = None
            self.map_figure = None
            self.map_ax = None
            self.map_colorbar = None
            self.map_im = None
            self.map_extent = None
            self.boundary_data = None

