#!/usr/bin/env python3

import sys
import subprocess
import shutil
import os

def check_and_install_dependencies():
    """检测依赖，Linux下不自动安装Pillow，仅提示"""
    
    print("\n" + "="*60)
    print("正在检测系统依赖...")
    print("="*60)
    
    try:
        import tkinter
        print("[✓] tkinter 已安装")
    except ImportError:
        if sys.platform == "linux":
            if os.path.exists("/etc/debian_version"):
                cmd = "sudo apt update && sudo apt install -y python3-tk"
                pkg = "python3-tk"
            elif os.path.exists("/etc/redhat-release"):
                cmd = "sudo dnf install -y python3-tkinter"
                pkg = "python3-tkinter"
            elif shutil.which("pacman"):
                cmd = "sudo pacman -S --noconfirm tk"
                pkg = "tk"
            else:
                cmd = "请手动安装系统对应的python3-tk包"
                pkg = "python3-tk"
            
            print(f"\n[✗] tkinter 未安装 (系统库)")
            print(f"\n检测到您的Linux系统需要手动安装tkinter:")
            print(f"  包名: {pkg}")
            print(f"  建议命令: {cmd}")
            print("\n注意：此步骤需要管理员权限，脚本无法自动完成。")
            print("请在另一个终端中运行上述命令后，重新启动本脚本。")
            print("="*60)
            sys.exit(1)
        else:
            print("[✗] tkinter 未安装")
            print("\n您的系统缺少tkinter，这通常意味着Python安装不完整。")
            print("请重新安装Python并确保包含 tcl/tk 支持。")
            print("="*60)
            input("\n按回车键退出...")
            sys.exit(1)
    
    try:
        from PIL import Image, ImageTk
        print("[✓] Pillow 已安装")
    except ImportError:
        print("[✗] Pillow 未安装")

        if sys.platform == "linux":
            if os.path.exists("/etc/debian_version"):
                cmd = "sudo apt install python3-pil"
                pkg = "python3-pil"
            elif os.path.exists("/etc/redhat-release"):
                cmd = "sudo dnf install python3-pillow"
                pkg = "python3-pillow"
            elif shutil.which("pacman"):
                cmd = "sudo pacman -S python-pillow"
                pkg = "python-pillow"
            else:
                cmd = "pip install Pillow"
                pkg = "Pillow"

            print(f"\n检测到您的系统需要手动安装Pillow:")
            print(f"  包名: {pkg}")
            print(f"  建议命令: {cmd}")
            print("\n对于Debian/Ubuntu等系统，建议使用系统包管理器安装。")
            print("安装完成后，请重新运行本脚本。")
            print("="*60)
            sys.exit(1)
        else:
            print("\nPillow可以通过pip安装:")
            print(f"  pip install Pillow")
            print("\n请安装完成后重新运行本脚本。")
            print("="*60)
            input("\n按回车键退出...")
            sys.exit(1)

    # ── opencv-python（可选，用于视频首帧缩略图）──
    try:
        import cv2
        print("[✓] opencv-python 已安装（支持视频缩略图预览）")
    except ImportError:
        cv2 = None
        print("[!] opencv-python 未安装，视频文件将以文字提示代替预览")
        print("    安装命令：pip install opencv-python")

    print("\n所有依赖检测通过！正在启动程序...\n")
    return True


if __name__ == "__main__":
    check_and_install_dependencies()

import json
import re
import datetime
from tkinter import *
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import subprocess

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False

# ── 默认快捷键配置（最多支持 MAX_FOLDERS 个文件夹）──
MAX_FOLDERS = 9
DEFAULT_KEYS = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l']
DEFAULT_FOLDER_COUNT = 3
TOGGLE_MODE_KEY = 'Tab'

# ── 全局样式常量 ──
FONT_NORMAL    = ('Microsoft YaHei', 11)
FONT_BOLD      = ('Microsoft YaHei', 11, 'bold')
FONT_SMALL     = ('Microsoft YaHei', 10)
FONT_TITLE     = ('Microsoft YaHei', 13, 'bold')
FONT_WELCOME  = ('Microsoft YaHei', 12)
COLOR_BG       = '#f0f2f5'
COLOR_BTN      = '#4a90d9'
COLOR_BTN_FG   = 'white'
COLOR_BTN_ALT  = '#6c757d'
COLOR_ACCENT   = '#e8edf3'
COLOR_BORDER   = '#c0c4cc'
COLOR_STATUS_BG = '#e8e8e8'


class HintEntry(Entry):
    def __init__(self, master, hint='', **kw):
        super().__init__(master, **kw)
        self.hint = hint
        self.hint_color = 'grey'
        self.normal_color = self['fg']
        self.bind('<FocusIn>',  self._clear_hint)
        self.bind('<FocusOut>', self._show_hint)
        self._show_hint()

    def _clear_hint(self, *_):
        if self['fg'] == self.hint_color:
            self.delete(0, END)
            self.config(fg=self.normal_color)

    def _show_hint(self, *_):
        if not self.get():
            self.insert(0, self.hint)
            self.config(fg=self.hint_color)

    def set(self, text):
        self._clear_hint()
        self.insert(0, text)
        self.config(fg=self.normal_color)


class CreateFolderDialog(Toplevel):
    """新建分类文件夹对话框"""
    def __init__(self, parent, base_dir, default_name):
        super().__init__(parent)
        self.title("新建分类文件夹")
        self.resizable(False, False)
        self.configure(bg=COLOR_BG)
        self.result_path = None
        self._base_dir = base_dir

        Label(self, text="在以下位置创建新文件夹：",
              font=FONT_BOLD, bg=COLOR_BG).pack(padx=20, pady=(14, 2), anchor='w')
        Label(self, text=base_dir,
              font=FONT_SMALL, fg=COLOR_BTN_ALT, bg=COLOR_BG).pack(padx=20, anchor='w')

        name_frm = Frame(self, bg=COLOR_BG)
        name_frm.pack(padx=20, pady=(10, 2), fill='x')
        Label(name_frm, text="文件夹名称：", font=FONT_BOLD, bg=COLOR_BG).pack(side=LEFT)
        self._entry = Entry(name_frm, font=FONT_BOLD, width=20,
                            bd=1, relief=SUNKEN)
        self._entry.pack(side=LEFT, padx=4)
        self._entry.insert(0, default_name)
        self._entry.select_range(0, END)

        self._hint_label = Label(self, text="", font=FONT_SMALL,
                                 fg='#52b788', bg=COLOR_BG)
        self._hint_label.pack(padx=20, pady=(2, 0), anchor='w')

        btn_frm = Frame(self, bg=COLOR_BG)
        btn_frm.pack(padx=20, pady=12)
        Button(btn_frm, text=" 创建 ", command=self._ok,
               bg='#52b788', fg='white', font=FONT_BOLD,
               padx=14, pady=4, bd=0, cursor='hand2').pack(side=LEFT, padx=6)
        Button(btn_frm, text=" 取消 ", command=self.destroy,
               bg=COLOR_BTN_ALT, fg='white', font=FONT_BOLD,
               padx=14, pady=4, bd=0, cursor='hand2').pack(side=LEFT, padx=6)

        # 绑定回车 → 创建
        self._entry.bind('<Return>', lambda e: self._ok())

        # 延迟 grab_set 和 focus，避免 IME 初始化冲突
        self.after(100, self._delayed_init)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window()

    def _delayed_init(self):
        """对话框完全渲染后再聚焦，确保中文输入法正常"""
        self.grab_set()
        self._entry.focus_set()
        self._update_hint()

    def _update_hint(self):
        name = self._entry.get().strip()
        if not name:
            self._hint_label.config(text="请输入文件夹名称", fg='#aaa')
            return
        full = os.path.join(self._base_dir, name)
        if os.path.exists(full):
            self._hint_label.config(text="该文件夹已存在，创建后将合并内容", fg='#e67e22')
        else:
            self._hint_label.config(text=f"将创建：{full}", fg='#52b788')

    def _ok(self):
        name = self._entry.get().strip()
        if not name:
            self._hint_label.config(text="文件夹名称不能为空！", fg='#e74c3c')
            self._entry.focus_set()
            return
        full = os.path.join(self._base_dir, name)
        try:
            os.makedirs(full, exist_ok=True)
            self.result_path = full
            self.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"创建失败：{e}", parent=self)


class KeybindDialog(Toplevel):
    """自定义快捷键对话框"""
    def __init__(self, parent, folder_count, keys):
        super().__init__(parent)
        self.title("自定义快捷键")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=COLOR_BG)
        self.result_keys = list(keys)
        self.folder_count = folder_count
        self.entries = []

        Label(self, text="设置各文件夹快捷键（单个字母/数字）",
              font=FONT_BOLD, bg=COLOR_BG).grid(
                  row=0, column=0, columnspan=3, padx=20, pady=(14, 8))

        Label(self, text="文件夹", font=FONT_BOLD, bg=COLOR_BG).grid(row=1, column=0, padx=10)
        Label(self, text="快捷键", font=FONT_BOLD, bg=COLOR_BG).grid(row=1, column=1, padx=10)
        Label(self, text="说明",   font=FONT_BOLD, bg=COLOR_BG).grid(row=1, column=2, padx=10)

        for i in range(folder_count):
            Label(self, text=f"文件夹 {i+1}", font=FONT_NORMAL, bg=COLOR_BG).grid(
                row=i+2, column=0, padx=10, pady=4)
            var = StringVar(value=keys[i])
            e = Entry(self, textvariable=var, width=4,
                      font=FONT_BOLD, justify='center',
                      bd=1, relief=SUNKEN)
            e.grid(row=i+2, column=1, padx=10, pady=4)
            self.entries.append(var)
            Label(self, text="（单字符）", font=FONT_SMALL,
                  fg=COLOR_BTN_ALT, bg=COLOR_BG).grid(
                      row=i+2, column=2, padx=10)

        note = (f"保留键：W=跳过  Del=删除  Ctrl+Z=撤销  Tab=切换模式\n"
                "请勿将上述键设为分类快捷键")
        Label(self, text=note, font=FONT_SMALL,
              fg=COLOR_BTN_ALT, bg=COLOR_BG).grid(
                  row=folder_count+2, column=0, columnspan=3,
                  padx=16, pady=(8, 4))

        btn_frm = Frame(self, bg=COLOR_BG)
        btn_frm.grid(row=folder_count+3, column=0, columnspan=3, pady=12)
        Button(btn_frm, text=" 确定 ", command=self._ok,
               bg=COLOR_BTN, fg=COLOR_BTN_FG,
               font=FONT_BOLD, padx=12, pady=4,
               bd=0, cursor='hand2').pack(side=LEFT, padx=6)
        Button(btn_frm, text=" 取消 ", command=self.destroy,
               bg=COLOR_BTN_ALT, fg=COLOR_BTN_FG,
               font=FONT_BOLD, padx=12, pady=4,
               bd=0, cursor='hand2').pack(side=LEFT, padx=6)
        Button(btn_frm, text=" 重置默认 ", command=self._reset,
               bg='#e0e0e0', fg='black',
               font=FONT_NORMAL, padx=12, pady=4,
               bd=0, cursor='hand2').pack(side=LEFT, padx=6)

        self.wait_window()

    def _ok(self):
        new_keys = []
        seen = set()
        for i, var in enumerate(self.entries):
            k = var.get().strip().lower()
            if not k:
                messagebox.showwarning("提示", f"文件夹 {i+1} 的快捷键不能为空", parent=self)
                return
            if len(k) != 1:
                messagebox.showwarning("提示", f"文件夹 {i+1} 的快捷键请输入单个字符", parent=self)
                return
            reserved = {'w', '\t'}  # tab 用于切换模式
            if k in reserved:
                messagebox.showwarning("提示",
                    f"字符 '{k}' 是系统保留快捷键，请换一个", parent=self)
                return
            if k in seen:
                messagebox.showwarning("提示",
                    f"快捷键 '{k}' 重复，请为每个文件夹设置不同的快捷键", parent=self)
                return
            seen.add(k)
            new_keys.append(k)
        self.result_keys[:len(new_keys)] = new_keys
        self.destroy()

    def _reset(self):
        for i, var in enumerate(self.entries):
            if i < len(DEFAULT_KEYS):
                var.set(DEFAULT_KEYS[i])


class ImageClassifier:
    def __init__(self, root):
        self.root = root
        self.root.title("图片分类工具")
        
        self.windowed_height_ratio = 0.75
        self.windowed_geometry_set = False
        
        if sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except:
                pass
            self.root.state('zoomed')
        
        elif sys.platform == 'darwin':
            root.geometry('%dx%d+%d+%d' % (root.winfo_screenwidth(), root.winfo_screenheight(), 0, 0))
        
        else:
            if root.winfo_screenwidth() > 1920:
                root.tk.call('tk', 'scaling', 1.5)
            root.attributes('-zoomed', True)
        
        import tkinter.font as tkfont
        self.default_font = tkfont.nametofont("TkDefaultFont")
        self.default_font.configure(size=11)
        self.root.option_add("*Font", self.default_font)
        self.root.configure(bg=COLOR_BG)
        # ttk 样式（Combobox 等控件不受 option_add 影响）
        self._ttk_style = ttk.Style()
        self._ttk_style.configure('TCombobox', font=FONT_NORMAL)
        self._ttk_style.map('TCombobox',
            fieldbackground=[('readonly', 'white')],
            selectbackground=[('readonly', '#cce5ff')])

        self.config_file = "classifier_config.json"

        self.input_folder   = StringVar()
        self.inc_subfolders = BooleanVar(value=False)
        self.sort_method    = StringVar(value="name")
        self.reverse_sort   = BooleanVar(value=False)
        self.copy_mode      = BooleanVar(value=True)
        
        self.scale_mode     = StringVar(value="完整")
        self.dont_enlarge   = BooleanVar(value=True)

        # ── 动态文件夹数量 ──
        self.folder_count_var = IntVar(value=DEFAULT_FOLDER_COUNT)
        self.output_folders = [
            {"name": f"文件夹{i+1}", "path": StringVar()}
            for i in range(MAX_FOLDERS)
        ]
        # 自定义快捷键列表
        self.hotkeys = list(DEFAULT_KEYS)

        self.all_images = []
        self.ptr = 0
        self.history = []
        self.skip_stack = []

        # ── 进度恢复 ──
        self._saved_ptr = 0          # 从配置读取的上次 ptr
        self._saved_anchor = None    # 上次退出时的锚定文件名（用于精确恢复）

        self.img_ext = ('.jpg','.jpeg','.png','.gif','.bmp','.tiff','.ico')
        self.vid_ext = ('.mp4','.avi','.mov','.wmv','.flv','.mkv')
        self.swf_ext = ('.swf',)
        self.supported_formats = self.img_ext + self.vid_ext + self.swf_ext

        self.load_config()
        self.build_ui()
        self.root.after(100, lambda: self.root.focus_force())
        if self.input_folder.get() and os.path.exists(self.input_folder.get()):
            self.root.after(200, self.load_images)
        # 退出时自动保存（含进度）
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ──────────────────────────────────────────────
    #  UI 构建
    # ──────────────────────────────────────────────
    def build_ui(self):
        # ── 第一行：输入路径 ──
        line1 = Frame(self.root, bg=COLOR_BG)
        line1.pack(fill=X, padx=10, pady=(8,3))
        Label(line1, text="输入路径：", bg=COLOR_BG, font=FONT_BOLD).pack(side=LEFT)
        self.input_entry = HintEntry(line1, textvariable=self.input_folder,
                                     hint='这里是需要处理的文件夹路径', state='readonly')
        self.input_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        Button(line1, text="浏览…", command=self.browse_input,
               bg=COLOR_BTN, fg=COLOR_BTN_FG, font=FONT_BOLD,
               padx=10, pady=3, bd=0, cursor='hand2').pack(side=LEFT, padx=5)
        Checkbutton(line1, text="包含子文件夹", variable=self.inc_subfolders,
                    command=self.load_images, bg=COLOR_BG,
                    activebackground=COLOR_BG).pack(side=LEFT, padx=5)

        # ── 第二行：排序 + 缩放 + 复制/移动 + 撤销 ──
        line2 = Frame(self.root, bg=COLOR_BG)
        line2.pack(fill=X, padx=10, pady=(2,4))

        Label(line2, text="排序：", bg=COLOR_BG, font=FONT_BOLD).pack(side=LEFT, padx=(6,0))
        sort_frm = Frame(line2, bg=COLOR_BG)
        sort_frm.pack(side=LEFT)
        for txt, val in [("时间↑","time"), ("大小↑","size"), ("名称↑","name")]:
            Radiobutton(sort_frm, text=txt, variable=self.sort_method,
                       value=val, command=self.load_images,
                       bg=COLOR_BG, activebackground=COLOR_BG,
                       font=FONT_SMALL).pack(side=LEFT, padx=3)
        Checkbutton(sort_frm, text="倒序", variable=self.reverse_sort,
                   command=self.load_images,
                   bg=COLOR_BG, activebackground=COLOR_BG,
                   font=FONT_SMALL).pack(side=LEFT, padx=8)

        sep2 = Frame(line2, width=1, bg=COLOR_BORDER)
        sep2.pack(side=LEFT, fill=Y, padx=8, pady=4)
        
        Frame(line2, bg=COLOR_BG).pack(side=LEFT, fill=X, expand=True)
        
        Label(line2, text="缩放：", bg=COLOR_BG, font=FONT_BOLD).pack(side=LEFT)
        scale_frame = Frame(line2, bg=COLOR_BG)
        scale_frame.pack(side=LEFT, padx=2)
        ttk.Combobox(scale_frame, textvariable=self.scale_mode,
                    values=["完整", "填充", "原始"],
                    state="readonly", width=5).pack(side=LEFT)
        self.scale_mode.trace_add('write', self.on_display_option_change)
        
        Checkbutton(line2, text="小图不放大", variable=self.dont_enlarge,
                   command=self.on_display_option_change,
                   bg=COLOR_BG, activebackground=COLOR_BG,
                   font=FONT_SMALL).pack(side=LEFT, padx=6)
        
        sep = Frame(line2, width=1, bg=COLOR_BORDER)
        sep.pack(side=LEFT, fill=Y, padx=8, pady=4)
        
        mode_frm = Frame(line2, bg=COLOR_BG)
        mode_frm.pack(side=LEFT)
        Radiobutton(mode_frm, text="复制", variable=self.copy_mode, value=True,
                    bg=COLOR_BG, activebackground=COLOR_BG,
                    font=FONT_SMALL, selectcolor=COLOR_ACCENT).pack(side=LEFT)
        Radiobutton(mode_frm, text="移动", variable=self.copy_mode, value=False,
                    bg=COLOR_BG, activebackground=COLOR_BG,
                    font=FONT_SMALL, selectcolor=COLOR_ACCENT).pack(side=LEFT)
        Label(mode_frm, text="(Tab切换)", font=FONT_SMALL, fg=COLOR_BTN_ALT,
              bg=COLOR_BG).pack(side=LEFT, padx=(4,0))

        sep_undo = Frame(line2, width=1, bg=COLOR_BORDER)
        sep_undo.pack(side=LEFT, fill=Y, padx=8, pady=4)
        
        Button(line2, text="↩ 撤销", command=self.undo,
               bg=COLOR_BTN_ALT, fg=COLOR_BTN_FG, font=FONT_BOLD,
               padx=10, pady=3, bd=0, cursor='hand2').pack(side=LEFT, padx=5)

        # ── 第三行：文件夹数量 + 自定义快捷键 ──
        line3 = Frame(self.root, bg=COLOR_BG)
        line3.pack(fill=X, padx=10, pady=(2,4))

        Label(line3, text="分类文件夹：", bg=COLOR_BG, font=FONT_BOLD).pack(side=LEFT)
        self._count_spinbox = Spinbox(
            line3, from_=2, to=MAX_FOLDERS,
            textvariable=self.folder_count_var,
            width=4, state='readonly',
            font=FONT_BOLD,
            command=self._on_folder_count_change)
        self._count_spinbox.pack(side=LEFT, padx=(0, 12))

        Button(line3, text="⌨ 自定义快捷键",
               command=self._open_keybind_dialog,
               bg=COLOR_BTN_ALT, fg=COLOR_BTN_FG, font=FONT_BOLD,
               padx=10, pady=3, bd=0, cursor='hand2').pack(side=LEFT, padx=5)

        # 快捷键预览标签（动态更新）
        self._key_preview_var = StringVar()
        Label(line3, textvariable=self._key_preview_var,
              font=FONT_SMALL, fg=COLOR_BTN_ALT,
              bg=COLOR_BG).pack(side=LEFT, padx=(12, 0))
        self._refresh_key_preview()

        # ── 图片预览区 ──
        self.img_frame = Frame(self.root, bg='white',
                              highlightbackground=COLOR_BORDER,
                              highlightthickness=1)
        self.img_frame.pack(fill=BOTH, expand=True, padx=14, pady=(4,6))
        self.img_frame.pack_propagate(False)

        self.img_label = Label(self.img_frame, bg='white', anchor=CENTER)
        self.img_label.pack(fill=BOTH, expand=True)
        self.img_label.bind("<Double-Button-1>", self.open_current_file)

        # ── 预览区右上角：文件类型 + 拍摄日期 ──
        self._info_label = Label(
            self.img_frame, text="", anchor='ne',
            bg='white', fg='#333333',
            font=FONT_SMALL, padx=8, pady=4,
            justify=RIGHT, relief=FLAT, bd=0)
        self._info_label.place(relx=1.0, rely=0.0, anchor='ne')

        # ── 输出文件夹行（动态生成）──
        self.out_line = Frame(self.root, bg=COLOR_BG)
        self.out_line.pack(fill=X, padx=10, pady=(2,4))
        self.out_entries = []
        self._build_output_rows()

        # ── 状态栏 ──
        status_bar = Frame(self.root, bg=COLOR_STATUS_BG)
        status_bar.pack(side=BOTTOM, fill=X)

        self.status = Label(status_bar, text="", bd=0, relief=FLAT, anchor=W,
                           bg=COLOR_STATUS_BG, font=FONT_SMALL,
                           padx=8, pady=4)
        self.status.pack(side=LEFT, fill=X, expand=True)

        # 进度条（紧贴状态栏右侧）
        self._progress_var = DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(
            status_bar, variable=self._progress_var,
            maximum=100, length=160, mode='determinate')
        self._progress_bar.pack(side=RIGHT, padx=(0, 10), pady=3)
        self._progress_label = Label(
            status_bar, text="", bg=COLOR_STATUS_BG,
            font=FONT_SMALL, fg='#555')
        self._progress_label.pack(side=RIGHT, padx=(0, 4), pady=3)

        # ── 绑定快捷键 ──
        self._bind_hotkeys()

        self.update_display()

    def _build_output_rows(self):
        """根据 folder_count_var 动态重建输出文件夹区域（网格布局，每行3个）"""
        for w in self.out_line.winfo_children():
            w.destroy()
        self.out_entries.clear()
        self._folder_count_labels = []   # 每个文件夹的计数标签

        n = self.folder_count_var.get()
        COLS = 3  # 每行显示的文件夹数量
        self.out_line.columnconfigure(0, weight=1)
        self.out_line.columnconfigure(1, weight=1)
        self.out_line.columnconfigure(2, weight=1)

        for i in range(n):
            fo = self.output_folders[i]
            key = self.hotkeys[i].upper()
            row = i // COLS
            col = i % COLS

            cell = Frame(self.out_line, bg=COLOR_BG)
            cell.grid(row=row, column=col, sticky='ew', padx=(0, 8) if col < COLS - 1 else 0,
                      pady=(0, 4) if row < (n - 1) // COLS else 0)

            btn_text = f"[{key}] 文件夹{i+1}"
            Button(cell, text=btn_text,
                   command=lambda f=fo: self.browse_output(f),
                   bg=COLOR_BTN, fg=COLOR_BTN_FG, font=FONT_BOLD,
                   padx=6, pady=3, bd=0,
                   cursor='hand2').pack(side=LEFT)
            hint = f'输出文件夹 {i+1} 的路径'
            e = HintEntry(cell, textvariable=fo["path"],
                          hint=hint, state='readonly')
            e.pack(side=LEFT, fill=X, expand=True, padx=(4, 0))
            self.out_entries.append(e)

            # 文件夹已有照片数标签
            cnt_lbl = Label(cell, text="", bg=COLOR_BG,
                            font=FONT_SMALL, fg='#52b788', width=6)
            cnt_lbl.pack(side=LEFT, padx=(2, 0))
            self._folder_count_labels.append(cnt_lbl)

            Button(cell, text="✚",
                   command=lambda idx=i: self.quick_create_folder(idx),
                   bg='#52b788', fg='white', font=('', 11, 'bold'),
                   padx=4, pady=1, bd=0,
                   cursor='hand2').pack(side=LEFT, padx=(2, 0))

    def _bind_hotkeys(self):
        """解绑旧快捷键，绑定新快捷键"""
        # 解绑之前绑定的分类快捷键
        if hasattr(self, '_bound_classify_keys'):
            for k in self._bound_classify_keys:
                try:
                    self.root.unbind(k)
                except:
                    pass

        self._bound_classify_keys = []
        n = self.folder_count_var.get()
        for i in range(n):
            k = self.hotkeys[i]
            self.root.bind(k, lambda e, idx=i: self.move_to(idx))
            self._bound_classify_keys.append(k)

        # 系统固定快捷键（同时绑大小写，确保 Windows 下不丢失事件）
        self.root.bind('<KeyPress-w>', lambda e: self.skip())
        self.root.bind('<KeyPress-W>', lambda e: self.skip())
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Tab>', lambda e: self.toggle_copy_mode())
        self.root.bind('<Delete>', lambda e: self.delete_current())

    def _on_folder_count_change(self):
        """文件夹数量改变时重建 UI"""
        self._build_output_rows()
        self._bind_hotkeys()
        self._refresh_key_preview()
        self.save_config()
        self.update_display()

    def _refresh_key_preview(self):
        """刷新快捷键预览文字"""
        n = self.folder_count_var.get()
        parts = [f"[{self.hotkeys[i].upper()}]=文件夹{i+1}" for i in range(n)]
        self._key_preview_var.set("  " + "  ".join(parts) +
                                   "  [W]=跳过  [Del]=删除  [Ctrl+Z]=撤销  [Tab]=切换模式")

    def _open_keybind_dialog(self):
        n = self.folder_count_var.get()
        dlg = KeybindDialog(self.root, n, self.hotkeys[:n])
        new_keys = dlg.result_keys
        # 更新实际 hotkeys（只更新前 n 个）
        for i in range(n):
            self.hotkeys[i] = new_keys[i]
        self._build_output_rows()
        self._bind_hotkeys()
        self._refresh_key_preview()
        self.save_config()

    # ──────────────────────────────────────────────
    #  复制/移动模式快速切换
    # ──────────────────────────────────────────────
    def toggle_copy_mode(self):
        """Tab 键快速切换复制/移动模式，并在状态栏闪提示"""
        new_val = not self.copy_mode.get()
        self.copy_mode.set(new_val)
        mode_text = "复制模式" if new_val else "移动模式"
        # 在状态栏显示临时提示
        self._flash_status(f"已切换为：{mode_text}")

    def _flash_status(self, msg, duration=2000):
        """在状态栏短暂显示一条高亮消息"""
        self.status.config(text=msg, fg='blue')
        self.root.after(duration, self._restore_status)

    def _restore_status(self):
        self.status.config(fg='black')
        self.update_status_bar()

    # ──────────────────────────────────────────────
    #  原有逻辑（基本不变）
    # ──────────────────────────────────────────────
    def on_display_option_change(self, *args):
        if self.all_images:
            self.show_current()

    def load_images(self):
        self.all_images = []
        if not self.input_folder.get(): return
        root_path = self.input_folder.get()
        if not os.path.exists(root_path): return

        if self.inc_subfolders.get():
            for r, _, fs in os.walk(root_path):
                for f in fs:
                    if f.lower().endswith(self.supported_formats):
                        self.all_images.append(os.path.join(r, f))
        else:
            for f in os.listdir(root_path):
                if f.lower().endswith(self.supported_formats):
                    full = os.path.join(root_path, f)
                    if os.path.isfile(full):
                        self.all_images.append(full)

        rev = self.reverse_sort.get()
        if self.sort_method.get() == "time":
            self.all_images.sort(key=lambda x: os.path.getmtime(x), reverse=not rev)
        elif self.sort_method.get() == "size":
            self.all_images.sort(key=lambda x: os.path.getsize(x), reverse=not rev)
        else:
            self.all_images.sort(reverse=rev)

        # ── 断点续传：尝试恢复上次的位置 ──
        self.ptr = 0
        if self._saved_anchor and self.all_images:
            # 优先按锚文件名精确定位
            for i, p in enumerate(self.all_images):
                if os.path.basename(p) == self._saved_anchor:
                    self.ptr = i
                    break
            else:
                # 文件名未找到时按保存的 ptr 数值恢复（可能已处理部分）
                self.ptr = min(self._saved_ptr, max(0, len(self.all_images) - 1))
        self._saved_anchor = None   # 用完即清，避免反复影响手动浏览

        self.update_display()

    def update_display(self):
        self.update_status_bar()
        if not self.input_folder.get():
            self.show_welcome(); return
        if not os.path.exists(self.input_folder.get()):
            self.show_error(f"目录：{self.input_folder.get()} 不存在"); return
        if not self.all_images:
            self.show_error(f"目录：{self.input_folder.get()} 没有图片"); return
        n = self.folder_count_var.get()
        valid = sum(1 for i in range(n) if self.output_folders[i]["path"].get())
        if valid < 2:
            self.show_error("请选择至少 2 个输出文件夹。\n请注意检查右上角的分类模式是否正确。\n此时，您仍可以双击打开当前选定的文件，即使程序没有显示该文件。")
            return
        self.show_current()

    def show_welcome(self):
        n = self.folder_count_var.get()
        key_list = "、".join(k.upper() for k in self.hotkeys[:n])
        txt = (
            "图片分类工具 优化版\n"
            "操作指南：\n"
            "  1. 选择输入文件夹（浏览按钮）\n"
            "  2. 选择 2~9 个输出文件夹\n"
            f"  3. 按 {key_list} 分类到对应文件夹（可自定义快捷键）\n"
            "  4. Tab 键快速切换复制/移动模式\n"
            "  5. W=跳过  Del=删除  Ctrl+Z=撤销\n"
            "  6. 双击预览图用系统程序打开"
        )
        self.img_label.config(text=txt, fg='#444',
                            font=FONT_WELCOME,
                            bg='white', justify=LEFT)

    def show_error(self, msg):
        self.img_label.config(text=msg, fg='#c0392b',
                             font=FONT_NORMAL, bg='white')

    def _get_file_datetime(self, filepath):
        """
        获取文件拍摄/创建日期，按优先级：
        1. EXIF DateTimeOriginal
        2. EXIF DateTimeDigitized
        3. 文件名中的日期模式
        4. 文件修改时间（兜底）
        返回格式化字符串，如 '2026-05-16 10:40'
        """
        ext = os.path.splitext(filepath)[1].lower()

        # ── 1. 图片 EXIF ──
        if ext in ('.jpg', '.jpeg', '.png', '.tiff', '.bmp'):
            try:
                from PIL.ExifTags import Base as ExifBase
                img = Image.open(filepath)
                exif = img._getexif()
                if exif:
                    # 优先 DateTimeOriginal (36867)
                    for tag_id in (36867, 36868, 306):
                        val = exif.get(tag_id)
                        if val:
                            # EXIF 格式: "2026:05:16 10:40:28"
                            try:
                                dt = datetime.datetime.strptime(val, "%Y:%m:%d %H:%M:%S")
                                return dt.strftime("%Y-%m-%d %H:%M")
                            except ValueError:
                                pass
            except Exception:
                pass

        # ── 2. 视频元数据（opencv，仅取创建/修改时间） ──
        # 视频文件通常没有可靠的拍摄时间，跳到文件名解析

        # ── 3. 从文件名解析日期 ──
        basename = os.path.splitext(os.path.basename(filepath))[0]
        # 常见模式（按精确度排序）
        patterns = [
            # IMG_20260516_104028, VID_2026-05-16, Screenshot 2026-05-16 等
            r'(\d{4})[-_](\d{1,2})[-_](\d{1,2})[_\s](\d{1,2})[-_:](\d{1,2})[-_:](\d{1,2})',
            r'(\d{4})[-_](\d{1,2})[-_](\d{1,2})[_\s](\d{1,2})[-_:](\d{1,2})',
            r'(\d{4})[-_](\d{1,2})[-_](\d{1,2})[_\s](\d{1,2})',
            r'(\d{4})[-_](\d{1,2})[-_](\d{1,2})',
        ]
        for pat in patterns:
            m = re.search(pat, basename)
            if m:
                groups = [int(g) for g in m.groups()]
                try:
                    if len(groups) >= 6:
                        dt = datetime.datetime(*groups[:6])
                    elif len(groups) >= 5:
                        dt = datetime.datetime(*groups[:5])
                    elif len(groups) >= 4:
                        dt = datetime.datetime(*groups[:4])
                    else:
                        dt = datetime.datetime(*groups[:3])
                    return dt.strftime("%Y-%m-%d" + (" %H:%M" if len(groups) >= 4 else ""))
                except ValueError:
                    continue

        # ── 4. 文件修改时间兜底 ──
        try:
            mtime = os.path.getmtime(filepath)
            dt = datetime.datetime.fromtimestamp(mtime)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return ""

    def _get_file_type_label(self, filepath):
        """返回文件类型的中文标签"""
        ext = os.path.splitext(filepath)[1].lower()
        if ext in self.vid_ext:
            return "视频"
        elif ext in self.swf_ext:
            return "Flash"
        elif ext in ('.jpg', '.jpeg'):
            return "图片 JPEG"
        elif ext == '.png':
            return "图片 PNG"
        elif ext == '.gif':
            return "图片 GIF"
        elif ext == '.bmp':
            return "图片 BMP"
        elif ext in ('.tiff', '.tif'):
            return "图片 TIFF"
        elif ext == '.ico':
            return "图标 ICO"
        else:
            return f"文件 {ext}"

    def show_current(self):
        if not self.all_images: return
        f = self.all_images[self.ptr]
        ext = os.path.splitext(f)[1].lower()

        if ext in self.swf_ext:
            # Flash 文件无法预览，仅提示
            self.img_label.config(
                image="",
                text=f"Flash 文件：{os.path.basename(f)}\n双击此处用默认程序打开",
                fg='#1a5fb4', font=FONT_NORMAL, bg='white')
        elif ext in self.vid_ext:
            # 视频文件：提取首帧缩略图
            if HAS_CV2:
                try:
                    self._show_video_thumbnail(f)
                except Exception as e:
                    self.img_label.config(
                        image="",
                        text=f"视频文件（无法预览缩略图）：{os.path.basename(f)}\n{e}\n双击此处用默认程序打开",
                        fg='#c0392b', font=FONT_NORMAL, bg='white')
            else:
                self.img_label.config(
                    image="",
                    text=f"视频文件：{os.path.basename(f)}\n（安装 opencv-python 可预览缩略图）\n双击此处用默认程序打开",
                    fg='#1a5fb4', font=FONT_NORMAL, bg='white')
        else:
            try:
                img = Image.open(f)
                frame_w = self.img_frame.winfo_width() - 10
                frame_h = self.img_frame.winfo_height() - 10
                
                if frame_w < 50 or frame_h < 50:
                    return
                
                scale_mode = self.scale_mode.get()
                dont_enlarge = self.dont_enlarge.get()
                
                if scale_mode == "原始":
                    ph = ImageTk.PhotoImage(img)
                elif scale_mode == "填充":
                    scale_w = frame_w / img.width
                    scale_h = frame_h / img.height
                    scale = max(scale_w, scale_h)
                    if dont_enlarge and scale > 1:
                        ph = ImageTk.PhotoImage(img)
                    else:
                        new_w = int(img.width * scale)
                        new_h = int(img.height * scale)
                        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        ph = ImageTk.PhotoImage(resized)
                else:
                    img_ratio = img.width / img.height
                    frame_ratio = frame_w / frame_h
                    
                    if img.width <= frame_w and img.height <= frame_h and dont_enlarge:
                        ph = ImageTk.PhotoImage(img)
                    else:
                        if img_ratio > frame_ratio:
                            new_w = frame_w
                            new_h = int(frame_w / img_ratio)
                        else:
                            new_h = frame_h
                            new_w = int(frame_h * img_ratio)
                        
                        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        ph = ImageTk.PhotoImage(resized)
                
                self.img_label.config(image=ph, text="")
                self.img_label.image = ph
            except Exception as e:
                self.img_label.config(text=f"无法加载图片：{e}", fg='red')

        # ── 更新右上角信息标签 ──
        self._update_info_label(f)

    def _update_info_label(self, filepath):
        """更新预览区右上角的文件类型 + 拍摄日期标签"""
        type_str = self._get_file_type_label(filepath)
        date_str = self._get_file_datetime(filepath)

        # 判断日期来源，加注释
        ext = os.path.splitext(filepath)[1].lower()
        date_note = ""
        if date_str:
            basename = os.path.splitext(os.path.basename(filepath))[0]
            # 检查是否从 EXIF 获取
            from_exif = False
            if ext in ('.jpg', '.jpeg', '.png', '.tiff', '.bmp'):
                try:
                    img = Image.open(filepath)
                    exif = img._getexif()
                    if exif and (36867 in exif or 36868 in exif or 306 in exif):
                        from_exif = True
                except Exception:
                    pass
            if from_exif:
                date_note = "(EXIF)"
            elif re.search(r'\d{4}[-_]\d{1,2}[-_]\d{1,2}', basename):
                date_note = "(文件名)"

        if date_str:
            self._info_label.config(
                text=f"{type_str}  |  📅 {date_str} {date_note}")
        else:
            self._info_label.config(text=f"{type_str}")

    def _show_video_thumbnail(self, filepath):
        """用 OpenCV 提取视频首帧，缩放后显示在预览区"""
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            raise RuntimeError("无法打开视频文件")
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError("无法读取视频帧")

        # BGR → RGB → PIL Image
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        frame_w = self.img_frame.winfo_width() - 10
        frame_h = self.img_frame.winfo_height() - 10
        if frame_w < 50 or frame_h < 50:
            return

        # 使用"完整"缩放模式（保持比例适应窗口）
        img_ratio = img.width / img.height
        frame_ratio = frame_w / frame_h
        dont_enlarge = self.dont_enlarge.get()

        if img.width <= frame_w and img.height <= frame_h and dont_enlarge:
            ph = ImageTk.PhotoImage(img)
        else:
            if img_ratio > frame_ratio:
                new_w = frame_w
                new_h = int(frame_w / img_ratio)
            else:
                new_h = frame_h
                new_w = int(frame_h * img_ratio)
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            ph = ImageTk.PhotoImage(resized)

        # 在缩略图右下角叠加"视频"标签
        self.img_label.config(image=ph, text="")
        self.img_label.image = ph

    def update_status_bar(self):
        if self.all_images:
            cur = os.path.basename(self.all_images[self.ptr])
            mode = "复制" if self.copy_mode.get() else "移动"
            total_orig = self.ptr + len(self.all_images) - self.ptr  # 当前队列
            # 已处理数 = 历史操作数（不含撤销）
            done = len(self.history)
            remaining = len(self.all_images)
            total_session = done + remaining
            pct = (done / total_session * 100) if total_session > 0 else 0

            self.status.config(
                text=(f"  {self.ptr + 1}/{remaining} 待分类  ·  "
                      f"本次已分类 {done} 张  ·  {cur}    [{mode}模式]"),
                fg='black')
            self._progress_var.set(pct)
            self._progress_label.config(
                text=f"{pct:.0f}%  ({done}/{total_session})")
        else:
            self.status.config(text="", fg='black')
            self._progress_var.set(0)
            self._progress_label.config(text="")

        # 刷新每个输出文件夹的照片计数
        self._refresh_folder_counts()

    def _refresh_folder_counts(self):
        """刷新输出文件夹旁的照片计数标签"""
        if not hasattr(self, '_folder_count_labels'):
            return
        n = self.folder_count_var.get()
        for i, lbl in enumerate(self._folder_count_labels):
            if i >= n:
                lbl.config(text="")
                continue
            path = self.output_folders[i]["path"].get()
            if path and os.path.isdir(path):
                try:
                    cnt = sum(
                        1 for f in os.listdir(path)
                        if f.lower().endswith(self.supported_formats)
                        and os.path.isfile(os.path.join(path, f))
                    )
                    lbl.config(text=f"📁{cnt}张" if cnt > 0 else "📂空")
                except Exception:
                    lbl.config(text="")
            else:
                lbl.config(text="")

    def _on_close(self):
        """窗口关闭时保存配置（含进度）并退出"""
        self.save_config()
        self.root.destroy()

    def skip(self):
        if not self.all_images: return
        self.skip_stack.append(self.all_images[self.ptr])
        self.ptr = (self.ptr + 1) % len(self.all_images)
        self.update_display()

    def delete_current(self):
        """删除当前图片（直接删除，二次确认）"""
        if not self.all_images: return
        src = self.all_images[self.ptr]
        ok = messagebox.askyesno(
            "确认删除",
            f"确定要删除这张图片吗？\n\n{os.path.basename(src)}\n\n此操作不可撤销！",
            parent=self.root
        )
        if not ok: return
        try:
            os.remove(src)
            self.all_images.pop(self.ptr)
            if self.all_images:
                self.ptr = self.ptr % len(self.all_images)
            self.update_display()
        except Exception as e:
            messagebox.showerror("错误", f"删除失败：{e}")

    def go_back(self):
        if not self.all_images: return
        self.ptr = (self.ptr - 1) % len(self.all_images)
        self.update_display()

    def move_to(self, idx):
        n = self.folder_count_var.get()
        if not self.all_images or idx >= n: return
        fo = self.output_folders[idx]["path"].get()
        if not fo:
            messagebox.showwarning("提示", f"请先选择 文件夹{idx+1} 的路径")
            return
        os.makedirs(fo, exist_ok=True)

        src = self.all_images[self.ptr]
        name = os.path.basename(src)
        dst = os.path.join(fo, name)
        base, ext = os.path.splitext(name)
        c = 1
        while os.path.exists(dst):
            dst = os.path.join(fo, f"{base}_{c}{ext}")
            c += 1

        try:
            if self.copy_mode.get():
                shutil.copy2(src, dst)
            else:
                shutil.move(src, dst)
            self.history.append({
                'src': dst,
                'dst': src,
                'idx': self.ptr,
                'copy': self.copy_mode.get()
            })
            self.all_images.pop(self.ptr)
            if self.all_images:
                self.ptr = self.ptr % len(self.all_images)
            self.update_display()
        except Exception as e:
            messagebox.showerror("错误", f"操作失败：{e}")

    def undo(self):
        if not self.history: return
        act = self.history.pop()
        try:
            if act['copy']:
                os.remove(act['src'])
            else:
                shutil.move(act['src'], act['dst'])
            self.all_images.insert(act['idx'], act['dst'])
            self.ptr = act['idx']
            self.update_display()
        except Exception as e:
            messagebox.showerror("错误", f"撤销失败：{e}")

    # ──────────────────────────────────────────────
    #  配置 保存/读取
    # ──────────────────────────────────────────────
    def save_config(self):
        # 当前正在查看的文件名（锚点，用于断点续传）
        anchor = ""
        if self.all_images and 0 <= self.ptr < len(self.all_images):
            anchor = os.path.basename(self.all_images[self.ptr])

        cfg = {
            'input_folder':   self.input_folder.get(),
            'inc_subfolders': self.inc_subfolders.get(),
            'sort_method':    self.sort_method.get(),
            'reverse_sort':   self.reverse_sort.get(),
            'copy_mode':      self.copy_mode.get(),
            'scale_mode':     self.scale_mode.get(),
            'dont_enlarge':   self.dont_enlarge.get(),
            'folder_count':   self.folder_count_var.get(),
            'hotkeys':        self.hotkeys,
            'output_folders': [fo["path"].get() for fo in self.output_folders],
            # ── 进度断点 ──
            'last_ptr':       self.ptr,
            'last_anchor':    anchor,
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                self.input_folder.set(cfg.get('input_folder', ''))
                self.inc_subfolders.set(cfg.get('inc_subfolders', False))
                self.sort_method.set(cfg.get('sort_method', 'name'))
                self.reverse_sort.set(cfg.get('reverse_sort', False))
                self.copy_mode.set(cfg.get('copy_mode', True))
                self.scale_mode.set(cfg.get('scale_mode', '完整'))
                self.dont_enlarge.set(cfg.get('dont_enlarge', True))
                self.folder_count_var.set(cfg.get('folder_count', DEFAULT_FOLDER_COUNT))
                saved_keys = cfg.get('hotkeys', DEFAULT_KEYS)
                for i, k in enumerate(saved_keys):
                    if i < MAX_FOLDERS:
                        self.hotkeys[i] = k
                for i, p in enumerate(cfg.get('output_folders', [])):
                    if i < MAX_FOLDERS:
                        self.output_folders[i]["path"].set(p)
                # ── 恢复进度断点 ──
                self._saved_ptr    = cfg.get('last_ptr', 0)
                self._saved_anchor = cfg.get('last_anchor', None)
        except:
            print("配置文件丢失或损坏，已恢复默认设置。")

    # ──────────────────────────────────────────────
    #  文件浏览
    # ──────────────────────────────────────────────
    def browse_input(self):
        d = filedialog.askdirectory()
        if d:
            self.input_folder.set(d)
            self.input_entry.set(d)
            self.load_images()
            self.save_config()

    def browse_output(self, fo):
        d = filedialog.askdirectory()
        if d:
            fo["path"].set(d)
            idx = next(i for i, x in enumerate(self.output_folders) if x is fo)
            if idx < len(self.out_entries):
                self.out_entries[idx].set(d)
            self.save_config()
            self.update_display()

    def quick_create_folder(self, idx):
        """在输入文件夹同级目录下快速创建新的分类文件夹"""
        base_dir = self.input_folder.get()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning("提示", "请先选择输入文件夹，再创建分类文件夹")
            return

        default_name = f"分类{idx + 1}"

        # 弹出自定义对话框让用户输入/确认文件夹名
        dlg = CreateFolderDialog(self.root, base_dir, default_name)
        if dlg.result_path:
            self.output_folders[idx]["path"].set(dlg.result_path)
            if idx < len(self.out_entries):
                self.out_entries[idx].set(dlg.result_path)
            self.save_config()
            self.update_display()

    def open_current_file(self, _):
        if not self.all_images: return
        f = self.all_images[self.ptr]
        try:
            if sys.platform == 'win32':
                os.startfile(f)
            elif sys.platform == 'darwin':
                subprocess.run(['open', f], check=True)
            else:
                subprocess.run(['xdg-open', f], check=True)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件：{e}")

    def on_window_configure(self, event):
        if event.widget != self.root:
            return
        
        if not hasattr(self.root, 'wm_state'):
            return
        
        current_state = self.root.wm_state()
        
        if not hasattr(self, '_prev_window_state'):
            self._prev_window_state = 'zoomed' if sys.platform == 'win32' else 'normal'
        
        state_changed = (current_state != self._prev_window_state)
        
        if (current_state == 'normal' and 
            not self.windowed_geometry_set and 
            self.windowed_height_ratio > 0):
            
            screen_height = self.root.winfo_screenheight()
            target_height = int(screen_height * self.windowed_height_ratio)
            
            current_width = self.root.winfo_width()
            new_geometry = f"{current_width}x{target_height}"
            self.root.geometry(new_geometry)
            
            self.windowed_geometry_set = True
            state_changed = True
        
        if state_changed and self.all_images:
            current_file = self.all_images[self.ptr]
            ext = os.path.splitext(current_file)[1].lower()
            if ext in self.img_ext:
                self.root.after(100, self.show_current)
        
        self._prev_window_state = current_state


if __name__ == "__main__":
    root = Tk()
    app = ImageClassifier(root)
    root.mainloop()
