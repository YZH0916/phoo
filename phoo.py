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

        note = (f"保留键：W=跳过  Del=删除  I=元数据  Ctrl+Z=撤销  Tab=切换模式\n"
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
            reserved = {'w', '\t', 'i'}  # tab=切换模式, i=元数据
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


class Phoo:
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

        self.config_file = "phoo_config.json"

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

        # ── 待应用操作队列 ──
        # 每条: {'action': 'move'|'copy'|'delete', 'src': 原路径, 'dst': 目标路径, 'idx': 原索引}
        self.pending_actions = []

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

        # ── 预览区右上角：文件类型 + 拍摄日期 + 扩展元数据 ──
        self._info_expanded = False  # 是否展开完整元数据
        self._info_label = Label(
            self.img_frame, text="", anchor='ne',
            bg='#f5f5f5', fg='#333333',
            font=FONT_SMALL, padx=8, pady=4,
            justify=RIGHT, relief=FLAT, bd=0,
            cursor='hand2')
        self._info_label.place(relx=1.0, rely=0.0, anchor='ne')
        self._info_label.bind('<Button-1>', lambda e: self._toggle_info_expand())

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

        # 应用按钮（状态栏右侧，进度条左侧）
        self._apply_btn = Button(
            status_bar, text="应用 (0)",
            command=self.apply_pending,
            bg='#4CAF50', fg='white',
            activebackground='#45a049',
            bd=0, padx=10, pady=2,
            font=FONT_SMALL, cursor='hand2',
            state=DISABLED
        )
        self._apply_btn.pack(side=RIGHT, padx=(0, 6), pady=3)

        # ── 绑定快捷键 ──
        self._bind_hotkeys()

        self.update_display()

    def _open_folder_by_idx(self, idx):
        """通过索引打开对应的输出文件夹"""
        path = self.output_folders[idx]["path"].get()
        if path and os.path.isdir(path):
            try:
                os.startfile(path)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件夹：{e}")
        else:
            messagebox.showinfo("提示", f"文件夹{idx + 1} 未设置有效路径")

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

            # 文件夹已有照片数标签（点击可打开文件夹）
            cnt_lbl = Label(cell, text="", bg=COLOR_BG,
                            font=FONT_SMALL, fg='#52b788', width=6,
                            cursor='hand2')
            cnt_lbl.pack(side=LEFT, padx=(2, 0))
            cnt_lbl.bind('<Button-1>', lambda e, idx=i: self._open_folder_by_idx(idx))
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
        self.root.bind('<KeyPress-i>', lambda e: self._toggle_info_expand())
        self.root.bind('<KeyPress-I>', lambda e: self._toggle_info_expand())

    def _on_folder_count_change(self):
        """文件夹数量改变时重建 UI"""
        self._build_output_rows()
        self._bind_hotkeys()
        self._refresh_key_preview()
        self.save_config()
        self.update_display()

    def _refresh_key_preview(self):
        """刷新底部快捷键提示文字（精简版）"""
        self._key_preview_var.set("  [W]=跳过  [Del]=删除  [Ctrl+Z]=撤销  [Tab]=切换模式")

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
            "  5. W=跳过  Del=删除  I=查看元数据  Ctrl+Z=撤销\n"
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
        获取文件拍摄日期，按优先级：
        1. EXIF DateTimeOriginal / DateTimeDigitized / DateTime
        2. 文件名中的日期模式（覆盖主流手机/APP命名格式）
        3. 文件创建时间
        4. 文件修改时间（兜底）
        返回格式化字符串，如 '2026-05-16 10:40'
        """
        ext = os.path.splitext(filepath)[1].lower()
        basename = os.path.splitext(os.path.basename(filepath))[0]

        # ── 1. 图片 EXIF ──
        if ext in ('.jpg', '.jpeg', '.png', '.tiff', '.bmp'):
            try:
                img = Image.open(filepath)
                exif = img._getexif()
                if exif:
                    for tag_id in (36867, 36868, 306):
                        val = exif.get(tag_id)
                        if val:
                            try:
                                dt = datetime.datetime.strptime(val, "%Y:%m:%d %H:%M:%S")
                                return dt.strftime("%Y-%m-%d %H:%M")
                            except ValueError:
                                pass
            except Exception:
                pass

        # ── 2. 从文件名解析日期 ──
        #    覆盖常见命名格式：
        #    IMG_20260516_104028 / VID_20260516-104028
        #    IMG_2026-05-16_104028 / Screenshot 2026-05-16
        #    微信图片_20260516104028 / mmexport1652683228354
        #    照片_2026-05-16-10-40-28 / Screenshot 2026-05-16 at 10.40.28
        #    AU20260516-104028 / 20260516104028 / 2026_05_16_10_40
        #    1677721600000 (纯毫秒时间戳) / 1677721600 (纯秒时间戳)

        # 2a. 纯数字时间戳（微信 mmexport 前缀等，13位毫秒或10位秒）
        ts_match = re.search(r'(?<!\d)(\d{13})(?!\d)', basename)
        if not ts_match:
            ts_match = re.search(r'(?<!\d)(\d{10})(?!\d)', basename)
        if ts_match:
            ts = int(ts_match.group(1))
            # 13位=毫秒，10位=秒
            if ts > 1e12:
                ts = ts // 1000
            # 合理年份范围 2000-2099
            try:
                dt = datetime.datetime.fromtimestamp(ts)
                if 2000 <= dt.year <= 2099:
                    return dt.strftime("%Y-%m-%d %H:%M")
            except (OSError, ValueError, OverflowError):
                pass

        # 2b. 带分隔符的日期时间（精确匹配年月日时分秒）
        dt_patterns = [
            # 20260516_104028 / 2026-05-16_10-40-28 / 2026_05_16 10_40_28
            r'(\d{4})[-_](\d{2})[-_](\d{2})[-_\s](\d{1,2})[-_:](\d{1,2})[-_:](\d{1,2})',
            # 20260516104028 (8+6 连续数字，年月日时分秒)
            r'(\d{4})(\d{2})(\d{2})[-_]?(?=\d)(\d{2})(\d{2})(\d{2})(?!\d)',
            # 2026-05-16 at 10.40.28 (iOS 截图)
            r'(\d{4})[-_](\d{2})[-_](\d{2})\s+at\s+(\d{1,2})\.(\d{1,2})\.(\d{1,2})',
            # 2026-05-16 10:40:28 / 2026-05-16 10-40-28
            r'(\d{4})[-_](\d{2})[-_](\d{2})\s+(\d{1,2})[-_:](\d{1,2})[-_:](\d{1,2})',
            # 2026-05-16 1040 (8位日期+4位时分)
            r'(\d{4})[-_](\d{2})[-_](\d{2})[-_\s](\d{2})(\d{2})',
            # 2026-05-16_1040 / 2026_05_16 1040
            r'(\d{4})[-_](\d{2})[-_](\d{2})[-_\s](\d{2})[-_:]?(\d{2})',
        ]
        for pat in dt_patterns:
            m = re.search(pat, basename)
            if m:
                groups = [int(g) for g in m.groups()]
                try:
                    dt = datetime.datetime(*groups[:6])
                    if self._is_valid_date(dt):
                        return dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    continue

        # 2c. 仅日期（年月日）
        date_patterns = [
            # 2026-05-16 / 2026_05_16
            r'(\d{4})[-_](\d{2})[-_](\d{2})',
            # 20260516 (8位连续日期)
            r'(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)',
        ]
        for pat in date_patterns:
            m = re.search(pat, basename)
            if m:
                groups = [int(g) for g in m.groups()]
                try:
                    dt = datetime.datetime(*groups[:3])
                    if self._is_valid_date(dt):
                        return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        # ── 3. 文件创建时间 ──
        try:
            ctime = os.path.getctime(filepath)
            dt = datetime.datetime.fromtimestamp(ctime)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

        # ── 4. 文件修改时间（兜底）──
        try:
            mtime = os.path.getmtime(filepath)
            dt = datetime.datetime.fromtimestamp(mtime)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return ""

    def _get_exif_data(self, filepath):
        """
        读取图片的完整 EXIF 元数据，返回结构化字典。
        仅对图片格式有效（JPG/JPEG/PNG/TIFF/BMP）。
        """
        result = {}
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'):
            return result

        try:
            img = Image.open(filepath)
            exif = img._getexif()
            if not exif:
                return result
        except Exception:
            return result

        # ── 拍摄设备 ──
        make = exif.get(271, '')   # Make
        model = exif.get(272, '')  # Model
        if make and model:
            # 去重：有些相机 Make 和 Model 前缀重复
            if model.startswith(make):
                result['设备'] = model
            else:
                result['设备'] = f"{make} {model}"
        elif model:
            result['设备'] = model
        elif make:
            result['设备'] = make

        # ── 镜头信息 ──
        lens_make = exif.get(42035, '')  # LensMake
        lens_model = exif.get(42036, '') # LensModel
        if lens_model:
            result['镜头'] = lens_model
        elif lens_make:
            result['镜头'] = lens_make

        # ── 拍摄参数 ──
        # 光圈
        fnum = exif.get(33437)  # FNumber
        if fnum:
            try:
                f_val = fnum[0] / fnum[1]
                result['光圈'] = f"f/{f_val:.1f}"
            except (TypeError, ZeroDivisionError):
                pass

        # 快门速度
        exp_time = exif.get(33434)  # ExposureTime
        if exp_time:
            try:
                num, den = exp_time
                if den == 1:
                    result['快门'] = f"{num}s"
                elif num == 1:
                    result['快门'] = f"1/{den}s"
                else:
                    result['快门'] = f"{num}/{den}s"
            except (TypeError, ZeroDivisionError):
                pass

        # ISO
        iso = exif.get(34855)  # ISOSpeedRatings
        if iso:
            result['ISO'] = str(iso)

        # 焦距
        focal = exif.get(37386)  # FocalLength
        if focal:
            try:
                fl = focal[0] / focal[1]
                result['焦距'] = f"{fl:.0f}mm"
            except (TypeError, ZeroDivisionError):
                pass

        # 35mm等效焦距
        focal_35 = exif.get(41989)  # FocalLengthIn35mmFilm
        if focal_35:
            result['等效焦距'] = f"{focal_35}mm"

        # 闪光灯
        flash = exif.get(37385)  # Flash
        if flash is not None:
            result['闪光灯'] = "已使用" if flash & 1 else "未使用"

        # ── GPS 信息 ──
        gps_lat = exif.get(34853, {})  # GPSInfo
        if isinstance(gps_lat, dict):
            lat_dms = gps_lat.get(2)  # GPSLatitude
            lat_ref = gps_lat.get(1)  # GPSLatitudeRef
            lon_dms = gps_lat.get(4)  # GPSLongitude
            lon_ref = gps_lat.get(3)  # GPSLongitudeRef
            alt = gps_lat.get(6)      # GPSAltitude

            if lat_dms and lat_ref and lon_dms and lon_ref:
                try:
                    lat = self._dms_to_decimal(lat_dms, lat_ref)
                    lon = self._dms_to_decimal(lon_dms, lon_ref)
                    result['GPS纬度'] = f"{lat:.4f}° {lat_ref}"
                    result['GPS经度'] = f"{lon:.4f}° {lon_ref}"
                except (TypeError, ZeroDivisionError, IndexError):
                    pass

            if alt:
                try:
                    alt_val = alt[0] / alt[1]
                    result['GPS海拔'] = f"{alt_val:.1f}m"
                except (TypeError, ZeroDivisionError):
                    pass

        # ── 图像信息 ──
        width = exif.get(40962)  # ExifImageWidth (PixelXDimension)
        height = exif.get(40963) # ExifImageHeight (PixelYDimension)
        if width and height:
            result['分辨率'] = f"{width} × {height}"

        orientation = exif.get(274)  # Orientation
        if orientation:
            orient_map = {1: "正常", 2: "水平翻转", 3: "旋转180°",
                         4: "垂直翻转", 5: "顺时针90°+水平翻转",
                         6: "顺时针90°", 7: "逆时针90°+水平翻转",
                         8: "逆时针90°"}
            result['方向'] = orient_map.get(orientation, str(orientation))

        # 色彩空间
        cs = exif.get(40961)  # ColorSpace
        if cs is not None:
            result['色彩空间'] = "sRGB" if cs == 1 else f"Uncalibrated ({cs})"

        # 软件
        software = exif.get(305)  # Software
        if software:
            result['软件'] = software

        return result

    def _dms_to_decimal(self, dms, ref):
        """将 EXIF GPS 的度分秒格式转为十进制坐标"""
        d = dms[0][0] / dms[0][1]
        m = dms[1][0] / dms[1][1]
        s = dms[2][0] / dms[2][1]
        decimal = d + m / 60 + s / 3600
        if ref in ('S', 'W'):
            decimal = -decimal
        return decimal

    def _is_valid_date(self, dt):
        """校验日期是否在合理范围内（2000年~明年）"""
        now = datetime.datetime.now()
        return (datetime.datetime(2000, 1, 1) <= dt
                <= datetime.datetime(now.year + 1, 12, 31))

    def _parse_filename_date(self, filepath):
        """
        从文件名中解析日期，返回 datetime 对象。
        如果无法解析则返回 None。
        优先级与 _get_file_datetime 中的文件名解析部分一致。
        """
        basename = os.path.splitext(os.path.basename(filepath))[0]

        # 1. 纯数字时间戳（13位毫秒或10位秒）
        ts_match = re.search(r'(?<!\d)(\d{13})(?!\d)', basename)
        if not ts_match:
            ts_match = re.search(r'(?<!\d)(\d{10})(?!\d)', basename)
        if ts_match:
            ts = int(ts_match.group(1))
            if ts > 1e12:
                ts = ts // 1000
            try:
                dt = datetime.datetime.fromtimestamp(ts)
                if self._is_valid_date(dt):
                    return dt
            except (OSError, ValueError, OverflowError):
                pass

        # 2. 带分隔符的日期时间（年月日时分秒）
        dt_patterns = [
            r'(\d{4})[-_](\d{2})[-_](\d{2})[-_\s](\d{1,2})[-_:](\d{1,2})[-_:](\d{1,2})',
            r'(\d{4})(\d{2})(\d{2})[-_]?(?=\d)(\d{2})(\d{2})(\d{2})(?!\d)',
            r'(\d{4})[-_](\d{2})[-_](\d{2})\s+at\s+(\d{1,2})\.(\d{1,2})\.(\d{1,2})',
            r'(\d{4})[-_](\d{2})[-_](\d{2})\s+(\d{1,2})[-_:](\d{1,2})[-_:](\d{1,2})',
            r'(\d{4})[-_](\d{2})[-_](\d{2})[-_\s](\d{2})(\d{2})',
            r'(\d{4})[-_](\d{2})[-_](\d{2})[-_\s](\d{2})[-_:]?(\d{2})',
        ]
        for pat in dt_patterns:
            m = re.search(pat, basename)
            if m:
                groups = [int(g) for g in m.groups()]
                try:
                    dt = datetime.datetime(*groups[:6])
                    if self._is_valid_date(dt):
                        return dt
                except ValueError:
                    continue

        # 3. 仅日期（年月日）
        date_patterns = [
            r'(\d{4})[-_](\d{2})[-_](\d{2})',
            r'(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)',
        ]
        for pat in date_patterns:
            m = re.search(pat, basename)
            if m:
                groups = [int(g) for g in m.groups()]
                try:
                    dt = datetime.datetime(*groups[:3])
                    if self._is_valid_date(dt):
                        return dt
                except ValueError:
                    continue

        return None

    def _fix_file_date(self, filepath):
        """
        校正文件创建/修改时间：
        如果文件名中包含的日期与文件系统时间偏差超过 1 天，
        则将创建时间和修改时间都修正为文件名记录的日期。
        返回 True 表示已修正，False 表示无需修正。
        """
        filename_date = self._parse_filename_date(filepath)
        if not filename_date:
            return False

        try:
            ctime_ts = os.path.getctime(filepath)
            ctime = datetime.datetime.fromtimestamp(ctime_ts)
        except Exception:
            return False

        # 计算偏差天数
        delta = abs((filename_date - ctime).total_seconds())
        # 偏差超过 1 天才修正（避免同一天内的小时差异触发）
        if delta < 86400:  # 86400 秒 = 1 天
            return False

        # 修正文件的创建时间和修改时间
        target_ts = filename_date.timestamp()
        try:
            os.utime(filepath, (target_ts, target_ts))
            # Windows 下 os.utime 只改 mtime/atime，ctime 需要额外处理
            # Windows 的 ctime 是"创建时间"，需要通过 pywin32 或 ctypes 修改
            if sys.platform == 'win32':
                try:
                    import ctypes
                    from ctypes import wintypes
                    # 使用 SetFileTime 修改 Windows 创建时间
                    kernel32 = ctypes.windll.kernel32
                    handle = kernel32.CreateFileW(
                        filepath, 0x100000,  # GENERIC_WRITE
                        0, None, 3,  # OPEN_EXISTING
                        0x80, None)  # FILE_ATTRIBUTE_NORMAL
                    if handle != -1:
                        # Windows FILETIME: 100纳秒单位，从1601-01-01 UTC
                        epoch = datetime.datetime(1601, 1, 1)
                        delta_w = filename_date - epoch
                        ft_value = int(delta_w.total_seconds() * 10_000_000)
                        ft = wintypes.FILETIME(ft_value & 0xFFFFFFFF,
                                               ft_value >> 32)
                        # SetFileTime(hFile, lpCreationTime, lpLastAccessTime, lpLastWriteTime)
                        kernel32.SetFileTime(handle, ctypes.byref(ft),
                                            ctypes.byref(ft), ctypes.byref(ft))
                        kernel32.CloseHandle(handle)
                except Exception:
                    pass  # 创建时间修改失败不影响 mtime 已被 os.utime 修正
            return True
        except Exception:
            return False

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

        # ── 自动校正文件日期（文件名日期 vs 创建时间偏差 > 1天则修正）──
        if self._fix_file_date(f):
            self._flash_status("📅 已校正文件日期为文件名记录的时间", duration=2500)

        # ── 更新右上角信息标签 ──
        self._update_info_label(f)

    def _get_video_info(self, filepath):
        """读取视频元数据，返回结构化字典（分辨率/帧率/时长/总帧数）"""
        result = {}
        if not HAS_CV2:
            return result
        try:
            cap = cv2.VideoCapture(filepath)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if w > 0 and h > 0:
                    result['分辨率'] = f"{w} × {h}"
                if fps > 0:
                    result['帧率'] = f"{fps:.1f} fps"
                if frames > 0 and fps > 0:
                    duration = frames / fps
                    mins = int(duration // 60)
                    secs = duration % 60
                    result['时长'] = f"{mins}:{secs:05.2f}"
                    result['总帧数'] = str(frames)
                cap.release()
        except Exception:
            pass
        return result

    def _toggle_info_expand(self):
        """按 I 键或点击切换预览区右上角信息展开/收起"""
        self._info_expanded = not self._info_expanded
        if self.all_images:
            self._update_info_label(self.all_images[self.ptr])

    def _shorten_date(self, date_str):
        """将 '2024-08-02 15:55' 转为 '2024/8/2 15:55' 短格式"""
        if not date_str:
            return date_str
        # 尝试解析并转为短格式
        for fmt_in, fmt_out in [
            ("%Y-%m-%d %H:%M", None),  # 带时间
            ("%Y-%m-%d", None),         # 仅日期
        ]:
            try:
                dt = datetime.datetime.strptime(date_str, fmt_in)
                if fmt_in == "%Y-%m-%d %H:%M":
                    return f"{dt.year}/{dt.month}/{dt.day} {dt.hour}:{dt.minute:02d}"
                else:
                    return f"{dt.year}/{dt.month}/{dt.day}"
            except ValueError:
                continue
        # 解析失败原样返回
        return date_str

    def _resolution_label(self, w, h):
        """将像素分辨率转为简洁标签，如 1080P/4K/720P"""
        short_side = min(w, h)
        if short_side >= 2160:
            return "4K"
        elif short_side >= 1080:
            return "1080P"
        elif short_side >= 720:
            return "720P"
        elif short_side >= 480:
            return "480P"
        else:
            return f"{w}×{h}"

    def _build_info_lines(self, filepath):
        """构建预览区右上角的信息行，根据 _info_expanded 返回简洁或完整内容"""
        type_str = self._get_file_type_label(filepath)
        date_str = self._get_file_datetime(filepath)
        ext = os.path.splitext(filepath)[1].lower()

        # ── 日期来源标注 ──
        date_note = ""
        if date_str:
            basename = os.path.splitext(os.path.basename(filepath))[0]
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
            elif re.search(r'(?<!\d)(\d{13}|1\d{9})(?!\d)', basename):
                date_note = "(时间戳)"
            elif re.search(r'\d{4}[-_]?\d{2}[-_]?\d{2}', basename):
                date_note = "(文件名)"
            else:
                try:
                    ctime = datetime.datetime.fromtimestamp(os.path.getctime(filepath))
                    ctime_str = ctime.strftime("%Y-%m-%d %H:%M")
                    if date_str == ctime_str:
                        date_note = "(创建时间)"
                    else:
                        date_note = "(修改时间)"
                except Exception:
                    date_note = ""

        # ── 读取元数据 ──
        exif_info = self._get_exif_data(filepath)
        video_info = self._get_video_info(filepath) if ext in self.vid_ext else {}

        # ── 位置信息判断 ──
        has_gps = ('GPS纬度' in exif_info and 'GPS经度' in exif_info)
        location_str = "位置信息：有" if has_gps else "位置信息：无"

        lines = [type_str]
        if date_str:
            lines.append(f"{self._shorten_date(date_str)} {date_note}".strip())

        if not self._info_expanded:
            # ── 简洁模式 ──
            if ext in self.vid_ext and video_info:
                # 视频：1080P|60fps|0:12:02
                vid_parts = []
                # 分辨率简写
                try:
                    cap = cv2.VideoCapture(filepath)
                    if cap.isOpened():
                        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        vid_parts.append(self._resolution_label(w, h))
                        cap.release()
                except Exception:
                    if '分辨率' in video_info:
                        vid_parts.append(video_info['分辨率'])
                if '帧率' in video_info:
                    vid_parts.append(video_info['帧率'])
                if '时长' in video_info:
                    vid_parts.append(video_info['时长'])
                if vid_parts:
                    lines.append("|".join(vid_parts))
            else:
                # 图片：设备|f/1.8|1/120s|ISO80
                img_parts = []
                if '设备' in exif_info:
                    img_parts.append(exif_info['设备'])
                for k in ('光圈', '快门', 'ISO'):
                    if k in exif_info:
                        img_parts.append(exif_info[k])
                if img_parts:
                    lines.append("|".join(img_parts))

            lines.append(location_str)
            lines.append("[I] 展开 ▼")
        else:
            # ── 展开模式：全部元数据 ──
            try:
                size = os.path.getsize(filepath)
                if size >= 1024 * 1024:
                    lines.append(f"💾 大小: {size / 1024 / 1024:.1f} MB")
                else:
                    lines.append(f"💾 大小: {size / 1024:.1f} KB")
            except Exception:
                pass

            if ext in self.img_ext:
                try:
                    img = Image.open(filepath)
                    lines.append(f"📐 分辨率: {img.width} × {img.height}")
                except Exception:
                    pass

            try:
                ctime = datetime.datetime.fromtimestamp(os.path.getctime(filepath))
                lines.append(f"📁 创建: {ctime.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception:
                pass
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
                lines.append(f"✏️ 修改: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception:
                pass

            # 图片 EXIF 详情
            if exif_info:
                lines.append("── 拍摄设备 ──")
                for k in ('设备', '镜头', '软件'):
                    if k in exif_info:
                        lines.append(f"  {k}: {exif_info[k]}")
                lines.append("── 拍摄参数 ──")
                for k in ('光圈', '快门', 'ISO', '焦距', '等效焦距', '闪光灯'):
                    if k in exif_info:
                        lines.append(f"  {k}: {exif_info[k]}")
                if has_gps:
                    lines.append("── 位置信息 ──")
                    for k in ('GPS纬度', 'GPS经度', 'GPS海拔'):
                        if k in exif_info:
                            lines.append(f"  {k}: {exif_info[k]}")
                lines.append("── 图像属性 ──")
                for k in ('方向', '色彩空间'):
                    if k in exif_info:
                        lines.append(f"  {k}: {exif_info[k]}")

            # 视频详情
            if video_info:
                lines.append("── 视频信息 ──")
                for k, v in video_info.items():
                    lines.append(f"  {k}: {v}")

            lines.append(location_str)
            lines.append("[I] 收起 ▲")

        return lines

    def _update_info_label(self, filepath):
        """更新预览区右上角的信息标签"""
        lines = self._build_info_lines(filepath)
        self._info_label.config(text="\n".join(lines))

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
        """更新状态栏：统计待应用操作数，并刷新应用按钮"""
        if self.all_images:
            cur = os.path.basename(self.all_images[self.ptr])
            mode = "复制" if self.copy_mode.get() else "移动"
            # 已规划操作数
            done = len(self.pending_actions)
            remaining = len(self.all_images)
            total_session = done + remaining
            pct = (done / total_session * 100) if total_session > 0 else 0

            self.status.config(
                text=(f"  {self.ptr + 1}/{remaining} 待分类  ·  "
                      f"本次已规划 {done} 项  ·  {cur}    [{mode}模式]"),
                fg='black')
            self._progress_var.set(pct)
            self._progress_label.config(
                text=f"{pct:.0f}%  ({done}/{total_session})")
        else:
            self.status.config(text="", fg='black')
            self._progress_var.set(0)
            self._progress_label.config(text="")

        # 刷新应用按钮状态
        n = len(self.pending_actions)
        if n > 0:
            self._apply_btn.config(
                text=f"应用 ({n})",
                state=NORMAL,
                bg='#4CAF50', fg='white'
            )
        else:
            self._apply_btn.config(
                text="已应用",
                state=DISABLED,
                bg='SystemButtonFace', fg='gray'
            )

        # 刷新每个输出文件夹的照片计数
        self._refresh_folder_counts()

    def _refresh_folder_counts(self):
        """刷新输出文件夹旁的照片计数标签（含 pending 预估）"""
        if not hasattr(self, '_folder_count_labels'):
            return
        n = self.folder_count_var.get()

        # 统计 pending 中目标为各文件夹的操作数
        pending_counts = {}
        for act in self.pending_actions:
            if act['dst']:
                folder = os.path.dirname(act['dst'])
                pending_counts[folder] = pending_counts.get(folder, 0) + 1

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
                    # 加上 pending 预估数
                    cnt += pending_counts.get(path, 0)
                    lbl.config(text=f"📁{cnt}张" if cnt > 0 else "📂空")
                except Exception:
                    lbl.config(text="")
            else:
                lbl.config(text="")

    def _on_close(self):
        """窗口关闭时检查待应用操作，提供应用或放弃选项"""
        if self.pending_actions:
            count = len(self.pending_actions)
            classify_n = sum(1 for a in self.pending_actions if a['action'] != 'delete')
            delete_n = sum(1 for a in self.pending_actions if a['action'] == 'delete')

            # 自定义弹窗：应用 / 放弃 / 取消
            result = {'choice': None}

            dlg = Toplevel(self.root)
            dlg.title("未应用的操作")
            dlg.resizable(False, False)
            dlg.grab_set()
            dlg.transient(self.root)

            # 居中显示
            dlg.update_idletasks()
            dw, dh = 380, 160
            x = self.root.winfo_x() + (self.root.winfo_width() - dw) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - dh) // 2
            dlg.geometry(f"{dw}x{dh}+{x}+{y}")

            Label(dlg, text=f"还有 {count} 项未应用的操作",
                  font=('', 11, 'bold')).pack(pady=(18, 4))
            Label(dlg, text=f"{classify_n} 项分类  ·  {delete_n} 项删除",
                  fg='#555').pack()

            btn_frame = Frame(dlg)
            btn_frame.pack(pady=(14, 0))

            def on_apply():
                result['choice'] = 'apply'
                dlg.destroy()

            def on_discard():
                result['choice'] = 'discard'
                dlg.destroy()

            def on_cancel():
                result['choice'] = 'cancel'
                dlg.destroy()

            Button(btn_frame, text="应用我的分类", command=on_apply,
                   bg='#4CAF50', fg='white', font=('', 10, 'bold'),
                   padx=12, pady=4, bd=0, cursor='hand2').pack(side=LEFT, padx=6)
            Button(btn_frame, text="放弃分类", command=on_discard,
                   bg='#e53935', fg='white', font=('', 10),
                   padx=12, pady=4, bd=0, cursor='hand2').pack(side=LEFT, padx=6)
            Button(btn_frame, text="取消", command=on_cancel,
                   font=('', 10), padx=12, pady=4, bd=1,
                   cursor='hand2').pack(side=LEFT, padx=6)

            dlg.protocol("WM_DELETE_WINDOW", on_cancel)
            self.root.wait_window(dlg)

            choice = result['choice']
            if choice == 'cancel' or choice is None:
                return
            elif choice == 'apply':
                # 执行所有待应用操作，全部成功则关闭
                success, failed, errors = self._do_apply()
                if failed > 0:
                    messagebox.showwarning(
                        "部分失败",
                        f"成功：{success}，失败：{failed}\n\n" + "\n".join(errors[:10]),
                        parent=self.root
                    )
                    return  # 有失败则不关闭
                # 全部成功，继续关闭
            elif choice == 'discard':
                self.pending_actions.clear()

        self.save_config()
        self.root.destroy()

    def skip(self):
        if not self.all_images: return
        self.skip_stack.append(self.all_images[self.ptr])
        self.ptr = (self.ptr + 1) % len(self.all_images)
        self.update_display()

    def delete_current(self):
        """将当前文件记录到待删除队列（不立即删除）"""
        if not self.all_images: return
        src = self.all_images[self.ptr]
        self.pending_actions.append({
            'action': 'delete', 'src': src, 'dst': None, 'idx': self.ptr
        })
        self.all_images.pop(self.ptr)
        if self.all_images:
            self.ptr = self.ptr % len(self.all_images)
        self.update_display()

    def go_back(self):
        if not self.all_images: return
        self.ptr = (self.ptr - 1) % len(self.all_images)
        self.update_display()

    def move_to(self, idx):
        """将当前文件记录到待应用队列（不立即执行）"""
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

        # 记录到待应用队列，不立即执行
        action = 'copy' if self.copy_mode.get() else 'move'
        self.pending_actions.append({
            'action': action, 'src': src, 'dst': dst, 'idx': self.ptr
        })
        self.all_images.pop(self.ptr)
        if self.all_images:
            self.ptr = self.ptr % len(self.all_images)
        self.update_display()

    def undo(self):
        """从待应用队列撤回最近一条操作，文件回到列表"""
        if not self.pending_actions: return
        act = self.pending_actions.pop()
        # 文件本身未被移动/删除，src 就是原始路径
        self.all_images.insert(act['idx'], act['src'])
        self.ptr = act['idx']
        self.update_display()

    def _do_apply(self):
        """执行所有待应用操作，返回 (success, failed, errors)"""
        success = 0
        failed = 0
        errors = []
        for act in list(self.pending_actions):
            try:
                if act['action'] == 'copy':
                    shutil.copy2(act['src'], act['dst'])
                elif act['action'] == 'move':
                    shutil.move(act['src'], act['dst'])
                elif act['action'] == 'delete':
                    os.remove(act['src'])
                success += 1
            except Exception as e:
                failed += 1
                errors.append(f"{os.path.basename(act['src'])}：{e}")

        self.pending_actions.clear()
        self.update_display()
        return success, failed, errors

    def apply_pending(self):
        """批量执行所有待应用操作（由"应用"按钮触发）"""
        if not self.pending_actions:
            messagebox.showinfo("提示", "没有待应用的操作")
            return

        success, failed, errors = self._do_apply()

        if failed == 0:
            self._flash_status(f"✅ 已成功应用 {success} 项操作")
        else:
            messagebox.showwarning(
                "部分失败",
                f"成功：{success}，失败：{failed}\n\n" + "\n".join(errors[:10])
            )

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
    app = Phoo(root)
    root.mainloop()
