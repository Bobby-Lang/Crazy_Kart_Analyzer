import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from src.utils.config_manager import ConfigManager
from src.core.scraper import CrazyCarScraper

class AccountPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.config_manager = ConfigManager()
        
        # Header
        self.header = ctk.CTkLabel(self, text="账号管理", font=("Microsoft YaHei UI", 24, "bold"))
        self.header.pack(pady=20, padx=20, anchor="w")
        
        # Form Area
        self.form_frame = ctk.CTkFrame(self)
        self.form_frame.pack(padx=20, fill="x")
        
        # 账号输入行
        phone_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        phone_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(phone_frame, text="账号:", width=50, font=("Microsoft YaHei UI", 14)).pack(side="left")
        self.phone_entry = ctk.CTkEntry(phone_frame, placeholder_text="请输入手机号", height=40, font=("Microsoft YaHei UI", 14))
        self.phone_entry.pack(side="left", fill="x", expand=True)
        
        # 密码输入行
        pwd_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        pwd_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(pwd_frame, text="密码:", width=50, font=("Microsoft YaHei UI", 14)).pack(side="left")
        
        # 使用原生 Entry 以支持 show="*" (CustomTkinter的Entry有时会有bug)
        # 这里为了样式统一，我们把 Entry 放在一个 CTkFrame 容器里模拟边框，或者直接调整 Entry 样式
        # 简单起见，我们调整 Entry 的背景色以适配 Dark 主题
        self.pwd_entry = tk.Entry(pwd_frame, show="*", font=("Consolas", 14), bg="#343638", fg="white", insertbackground="white", relief="flat")
        self.pwd_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(5,0)) # padx to align with CTkEntry padding roughly
        
        # 尝试禁用 IME (Windows) - 强制切换到英文布局
        self.pwd_entry.bind("<FocusIn>", lambda e: self._force_english_layout())
        
        self.btn_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.btn_frame.pack(pady=15, fill="x")
        
        self.test_btn = ctk.CTkButton(self.btn_frame, text="🚀 登录", height=40, font=("Microsoft YaHei UI", 14, "bold"), fg_color="#007BFF", hover_color="#0056b3", command=self.perform_login)
        self.test_btn.pack(side="right", padx=20)
        
        self.save_btn = ctk.CTkButton(self.btn_frame, text="保存账号", height=40, font=("Microsoft YaHei UI", 14), command=self.save_account)
        self.save_btn.pack(side="right", padx=20)

        # List Area
        ctk.CTkLabel(self, text="已保存账号", font=("Microsoft YaHei UI", 16)).pack(pady=(20, 10), padx=20, anchor="w")
        
        self.list_frame = ctk.CTkScrollableFrame(self, height=300)
        self.list_frame.pack(padx=20, fill="both", expand=True)
        
        self.refresh_list()

    def refresh_list(self):
        # Clear existing
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        accounts = self.config_manager.get("accounts", [])
        curr_idx = self.config_manager.get("current_account_idx", -1)
        
        for i, acc in enumerate(accounts):
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=5)
            
            lbl_text = f"{acc['phone']} {'(默认)' if i == curr_idx else ''}"
            lbl = ctk.CTkLabel(row, text=lbl_text, anchor="w")
            lbl.pack(side="left", padx=10)
            
            del_btn = ctk.CTkButton(row, text="删除", width=60, fg_color="#DC3545", hover_color="#C82333", command=lambda idx=i: self.delete_account(idx))
            del_btn.pack(side="right", padx=5, pady=5)
            
            use_btn = ctk.CTkButton(row, text="设为默认", width=80, command=lambda idx=i: self.set_default(idx))
            if i != curr_idx:
                use_btn.pack(side="right", padx=5, pady=5)

    def save_account(self):
        phone = self.phone_entry.get().strip()
        pwd = self.pwd_entry.get().strip()
        if not phone or not pwd:
            return
        
        self.config_manager.add_or_update_account(phone, pwd)
        self.phone_entry.delete(0, "end")
        self.pwd_entry.delete(0, "end")
        self.refresh_list()

    def delete_account(self, idx):
        accounts = self.config_manager.get("accounts", [])
        if 0 <= idx < len(accounts):
            del accounts[idx]
            self.config_manager.set("accounts", accounts)
            
            # Update index
            curr = self.config_manager.get("current_account_idx", -1)
            if curr == idx:
                self.config_manager.set("current_account_idx", -1)
            elif curr > idx:
                self.config_manager.set("current_account_idx", curr - 1)
                
            self.refresh_list()

    def set_default(self, idx):
        self.config_manager.set("current_account_idx", idx)
        self.refresh_list()

    def _force_english_layout(self):
        """强制切换到美式英语键盘布局 (Windows Only)"""
        try:
            import ctypes
            # 0x04090409 是美式英语键盘布局的 ID
            # LoadKeyboardLayoutW(LPCWSTR pwszKLID, UINT Flags); KLF_ACTIVATE = 1
            user32 = ctypes.windll.user32
            user32.LoadKeyboardLayoutW("00000409", 1)
        except Exception as e:
            print(f"Failed to switch keyboard layout: {e}")

    def perform_login(self):
        phone = self.phone_entry.get().strip()
        pwd = self.pwd_entry.get().strip()
        if not phone:
            acc = self.config_manager.get_current_account()
            if acc:
                phone = acc["phone"]
                pwd = acc["password"]
            else:
                messagebox.showwarning("提示", "请输入或选择一个账号")
                return

        def log_cb(msg):
            print(msg) # Simple print for test

        # Show loading state
        self.test_btn.configure(state="disabled", text="登录中...")
        self.update() # force UI update

        def _do_login():
            try:
                scraper = CrazyCarScraper(phone, pwd, log_cb)
                if scraper.login():
                    self.after(0, lambda: self._on_login_success(phone, pwd))
                else:
                    self.after(0, lambda: self._on_login_fail("账号或密码错误"))
            except Exception as e:
                self.after(0, lambda: self._on_login_fail(str(e)))

        import threading
        threading.Thread(target=_do_login).start()

    def _on_login_success(self, phone, pwd):
        self.test_btn.configure(state="normal", text="🚀 登录")
        # Ensure it's saved/updated as current
        self.config_manager.add_or_update_account(phone, pwd)
        # Find index and set default
        accounts = self.config_manager.get("accounts", [])
        for i, acc in enumerate(accounts):
            if acc["phone"] == phone:
                self.config_manager.set("current_account_idx", i)
                break
        
        self.refresh_list()
        messagebox.showinfo("成功", "登录成功！即将跳转主页...")
        self.controller.show_frame("home")

    def _on_login_fail(self, error):
        self.test_btn.configure(state="normal", text="🚀 登录")
        messagebox.showerror("登录失败", f"登录失败: {error}\n请检查网络或账号密码")
