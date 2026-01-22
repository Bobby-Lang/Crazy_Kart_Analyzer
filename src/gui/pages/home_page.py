import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import threading
import queue
import webbrowser
import os
from tkinter import messagebox
from src.utils.config_manager import ConfigManager
from src.utils.constants import OFFICIAL_MAP_ORDER, GAME_MODES
from src.core.scraper import CrazyCarScraper
from src.core.report_gen import ReportGenerator
from src.utils.paths import get_data_dir

class HomePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.config_manager = ConfigManager()
        self.log_queue = queue.Queue()
        self.is_running = False
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 1. Control Panel (Top)
        self.ctrl_frame = ctk.CTkFrame(self)
        self.ctrl_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        # Row 1: Status & Mode
        r1 = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=5)
        
        self.acc_label = ctk.CTkLabel(r1, text="当前账号: 未登录", font=("Microsoft YaHei UI", 14))
        self.acc_label.pack(side="left")
        
        self.mode_var = ctk.StringVar(value="组队竞速")
        self.mode_menu = ctk.CTkOptionMenu(r1, values=GAME_MODES, variable=self.mode_var)
        self.mode_menu.pack(side="right")
        ctk.CTkLabel(r1, text="模式:").pack(side="right", padx=5)

        # Row 2: Maps Selection (使用 ttk.Combobox 支持滚轮)
        r2 = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=5)
        
        # 配置 ttk 样式以匹配暗色主题
        style = ttk.Style()
        style.configure("TCombobox", padding=5)
        
        # End Map
        ctk.CTkLabel(r2, text="结束地图:").pack(side="left")
        self.end_map_var = tk.StringVar(value="(不限制/直接开始)")
        map_opts = ["(不限制/直接开始)"] + OFFICIAL_MAP_ORDER
        self.end_map_menu = ttk.Combobox(r2, textvariable=self.end_map_var, values=map_opts, width=20, state="readonly")
        self.end_map_menu.pack(side="left", padx=10)
        
        # Start Map
        ctk.CTkLabel(r2, text="起始地图:").pack(side="left", padx=(20, 0))
        self.start_map_var = tk.StringVar(value=OFFICIAL_MAP_ORDER[0])
        self.start_map_menu = ttk.Combobox(r2, textvariable=self.start_map_var, values=OFFICIAL_MAP_ORDER, width=20, state="readonly")
        self.start_map_menu.pack(side="left", padx=10)
        
        # Row 3: Action
        r3 = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        r3.pack(fill="x", padx=10, pady=10)
        
        self.auto_open_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r3, text="完成后自动打开报表", variable=self.auto_open_var).pack(side="left")
        
        self.run_btn = ctk.CTkButton(r3, text="🏁 开始生成报表", font=("Microsoft YaHei UI", 16, "bold"), height=50, fg_color="#28A745", hover_color="#218838", command=self.start_process)
        self.run_btn.pack(side="right", fill="x", expand=True, padx=(20, 0))

        # 2. Progress Area (Replaces Log Box)
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        self.progress_frame.grid_columnconfigure(0, weight=1)
        self.progress_frame.grid_rowconfigure(0, weight=1) # Center vertically

        # Container for progress info
        self.status_container = ctk.CTkFrame(self.progress_frame)
        self.status_container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8)

        self.status_label = ctk.CTkLabel(self.status_container, text="准备就绪", font=("Microsoft YaHei UI", 18))
        self.status_label.pack(pady=(20, 10))

        self.progress_bar = ctk.CTkProgressBar(self.status_container, height=15)
        self.progress_bar.pack(fill="x", padx=40, pady=(0, 20))
        self.progress_bar.set(0)

        # 3. Result Card (Initially Hidden)
        self.result_frame = ctk.CTkFrame(self.progress_frame, border_width=2, border_color="#28A745")
        # Don't pack/place initially
        
        self.success_icon = ctk.CTkLabel(self.result_frame, text="✅", font=("Segoe UI Emoji", 48))
        self.success_icon.pack(pady=(20, 0))
        
        self.result_title = ctk.CTkLabel(self.result_frame, text="报表生成成功", font=("Microsoft YaHei UI", 20, "bold"))
        self.result_title.pack(pady=5)
        
        self.result_path_label = ctk.CTkLabel(self.result_frame, text="report.html", text_color="gray70")
        self.result_path_label.pack(pady=5)
        
        self.open_report_btn = ctk.CTkButton(self.result_frame, text="📂 打开报表", command=self.open_current_report, width=200, height=40)
        self.open_report_btn.pack(pady=20)
        
        self.current_report_path = None

        # Queue for updates (msg, progress_float)
        self.check_log_queue()

    def on_show(self):
        acc = self.config_manager.get_current_account()
        if acc:
            self.acc_label.configure(text=f"当前账号: {acc['phone']}")
        else:
            self.acc_label.configure(text="当前账号: 未登录 (请前往账号页设置)")

    def update_status(self, msg, progress=None):
        """Put status update into queue"""
        self.log_queue.put((msg, progress))

    def log(self, msg):
        """Adapter for existing scraper calls - estimate progress based on msg"""
        # Simple heuristic to map log messages to progress bar
        p = None
        if "初始化" in msg: p = 0.05
        elif "登录成功" in msg: p = 0.1
        elif "开始抓取" in msg: p = 0.2
        elif "抓取中" in msg: p = 0.5 # This might need finer grain from scraper
        elif "生成报表" in msg: p = 0.8
        elif "生成成功" in msg: p = 1.0
        elif "失败" in msg: p = 0.0
        
        self.update_status(msg, p)

    def check_log_queue(self):
        while not self.log_queue.empty():
            msg, progress = self.log_queue.get()
            
            # Update Text
            if "成功" in msg or "失败" in msg:
                 self.status_label.configure(text=msg)
            else:
                 self.status_label.configure(text=msg + "...")

            # Update Progress Bar
            if progress is not None:
                self.progress_bar.set(progress)
            
            # Show Result Card on Success
            if "报表生成成功" in msg and ":" in msg:
                 # Extract filename roughly
                 fname = msg.split(":")[-1].strip()
                 self.show_success_card(fname)

        self.after(100, self.check_log_queue)

    def show_success_card(self, filename):
        self.status_container.place_forget() # Hide progress
        self.result_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.6, relheight=0.6)
        self.result_path_label.configure(text=filename)
        self.current_report_path = filename # Store for button

    def open_current_report(self):
        if self.current_report_path:
             path = os.path.abspath(os.path.join(get_data_dir(), self.current_report_path))
             webbrowser.open(f"file://{path}")

    def start_process(self):
        if self.is_running:
            return

        acc = self.config_manager.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先配置账号！")
            self.controller.show_frame("account")
            return

        self.is_running = True
        self.run_btn.configure(state="disabled", text="⏳ 处理中...")
        
        # Reset UI
        self.result_frame.place_forget()
        self.status_container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8)
        self.status_label.configure(text="正在初始化...", text_color=("black", "white"))
        self.progress_bar.set(0)
        
        thread = threading.Thread(target=self.worker, args=(acc,))
        thread.start()

    def worker(self, acc):
        try:
            self.log("🚀 初始化爬虫...")
            scraper = CrazyCarScraper(acc['phone'], acc['password'], self.log)
            
            if not scraper.login():
                self.log("❌ 登录失败，终止任务")
                return

            self.update_status("🔍 正在抓取比赛数据...", 0.3)
            end_map = self.end_map_var.get()
            if "不限制" in end_map: end_map = ""
            
            mode = self.mode_var.get()
            start_map_val = self.start_map_var.get()
            start_maps = [start_map_val]
            
            # Scrape
            header, data = scraper.start_crawl(mode, start_maps, end_map, self.config_manager.get("substitution_map"))
            self.update_status("💾 数据抓取完成，正在保存...", 0.7)
            
            # Save CSV
            csv_path = scraper.save_to_csv(header, data, str(get_data_dir()))
            
            if csv_path:
                self.log("📊 正在生成可视化报表...")
                gen = ReportGenerator()
                
                custom_pages = self.config_manager.get("custom_pages", [])
                sub_map = self.config_manager.get("substitution_map", {})
                
                report_path = gen.generate_report(csv_path, sub_map, custom_pages, get_data_dir())
                
                if report_path:
                    # Pass full path object, UI will handle extraction
                    self.current_report_path = report_path.name
                    self.log(f"✅ 报表生成成功: {report_path.name}")
                    if self.auto_open_var.get():
                        webbrowser.open(f"file://{os.path.abspath(report_path)}")
                else:
                    self.log("❌ 报表生成失败")
            else:
                self.log("❌ 未抓取到数据或保存失败")

        except Exception as e:
            self.log(f"❌ 发生异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            self.after(0, lambda: self.run_btn.configure(state="normal", text="🏁 开始生成报表"))
