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
import webbrowser
import re
import datetime
import tempfile
import xml.etree.ElementTree as ET
import hashlib
from tkinter import *
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import subprocess

# ── LIVP（iPhone 实况照片）支持 ──
try:
    from livp import LivpFile
    HAS_LIVP = True
except ImportError:
    HAS_LIVP = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False

__version__ = "2.3.1"

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

# 配色体系
COLOR_BG       = '#f7f8fa'       # 主背景
COLOR_CARD     = '#ffffff'       # 卡片/面板背景
COLOR_BORDER   = '#e5e7eb'       # 柔和边框
COLOR_BTN      = '#3b82f6'       # 主色按钮
COLOR_BTN_FG   = '#ffffff'       # 按钮文字
COLOR_BTN_ALT  = '#6b7280'       # 次要按钮
COLOR_ACCENT   = '#e8edf3'       # 选中底色
COLOR_SUCCESS  = '#10b981'       # 成功色
COLOR_DANGER   = '#ef4444'       # 危险色
COLOR_WARNING  = '#f59e0b'       # 警告色
COLOR_STATUS_BG = '#ffffff'      # 状态栏底色
COLOR_TEXT     = '#1f2937'       # 文字主色
COLOR_TEXT_SEC = '#6b7280'       # 文字次色
COLOR_TEXT_WEAK = '#9ca3af'      # 文字弱色/提示

# 间距系统（4px 基准）
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16


def _bind_hover(widget, bg, hover_bg):
    """通用按钮 hover 效果"""
    widget.bind('<Enter>', lambda e: widget.config(bg=hover_bg))
    widget.bind('<Leave>', lambda e: widget.config(bg=bg))


class HintEntry(Entry):
    def __init__(self, master, hint='', shorten_path=False, textvariable_ref=None, **kw):
        # shorten_path 模式：不传 textvariable 给 Entry，避免双向绑定冲突
        if shorten_path and textvariable_ref:
            self._var = textvariable_ref
            self._shorten_path = True
            kw.pop('textvariable', None)
            super().__init__(master, **kw)
            # 先初始化颜色和 hint，再注册 trace 回调
            self.hint = hint
            self.hint_color = '#9ca3af'
            self.normal_color = self['fg']
            self._var.trace_add("write", self._on_var_change)
            self._on_var_change()
            # 鼠标悬停时显示完整路径
            self.bind('<Enter>', self._show_full_path)
            self.bind('<Leave>', self._show_short_path)
        else:
            self._shorten_path = False
            super().__init__(master, **kw)
            self.hint = hint
            self.hint_color = '#9ca3af'
            self.normal_color = self['fg']
            self._show_hint()
        self.bind('<FocusIn>',  self._clear_hint)
        self.bind('<FocusOut>', self._show_hint)

    def _on_var_change(self, *_):
        """StringVar 变化时更新缩略显示"""
        if not self._shorten_path: return
        val = self._var.get()
        self.config(state='normal')
        self.delete(0, END)
        if val:
            short = os.path.basename(val.rstrip(os.sep))
            self.insert(0, short)
            self.config(fg=self.normal_color)
        else:
            self.insert(0, self.hint)
            self.config(fg=self.hint_color)
        self.config(state='readonly')

    def _show_full_path(self, *_):
        """鼠标进入时显示完整路径"""
        if not self._shorten_path: return
        val = self._var.get()
        if val:
            self.config(state='normal')
            self.delete(0, END)
            self.insert(0, val)
            self.config(fg=self.normal_color)
            self.config(state='readonly')

    def _show_short_path(self, *_):
        """鼠标离开时恢复缩略显示"""
        if not self._shorten_path: return
        self._on_var_change()

    def _clear_hint(self, *_):
        if self._shorten_path: return
        if self['fg'] == self.hint_color:
            self.delete(0, END)
            self.config(fg=self.normal_color)

    def _show_hint(self, *_):
        if self._shorten_path: return
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
        self.configure(bg=COLOR_CARD)
        self.result_path = None
        self._base_dir = base_dir

        Label(self, text="在以下位置创建新文件夹：",
              font=FONT_BOLD, bg=COLOR_CARD, fg=COLOR_TEXT).pack(padx=20, pady=(14, 2), anchor='w')
        Label(self, text=base_dir,
              font=FONT_SMALL, fg=COLOR_TEXT_SEC, bg=COLOR_CARD).pack(padx=20, anchor='w')

        name_frm = Frame(self, bg=COLOR_CARD)
        name_frm.pack(padx=20, pady=(10, 2), fill='x')
        Label(name_frm, text="文件夹名称：", font=FONT_BOLD, bg=COLOR_CARD,
              fg=COLOR_TEXT).pack(side=LEFT)
        self._entry = Entry(name_frm, font=FONT_BOLD, width=20,
                            bd=1, relief=SUNKEN)
        self._entry.pack(side=LEFT, padx=4)
        self._entry.insert(0, default_name)
        self._entry.select_range(0, END)

        self._hint_label = Label(self, text="", font=FONT_SMALL,
                                 fg=COLOR_SUCCESS, bg=COLOR_CARD)
        self._hint_label.pack(padx=20, pady=(2, 0), anchor='w')

        btn_frm = Frame(self, bg=COLOR_CARD)
        btn_frm.pack(padx=20, pady=12)
        btn_ok = Button(btn_frm, text=" 创建 ", command=self._ok,
               bg=COLOR_SUCCESS, fg='white', font=FONT_BOLD,
               padx=14, pady=4, bd=0, cursor='hand2')
        btn_ok.pack(side=LEFT, padx=6)
        _bind_hover(btn_ok, COLOR_SUCCESS, '#059669')
        btn_cancel = Button(btn_frm, text=" 取消 ", command=self.destroy,
               bg=COLOR_BTN_ALT, fg='white', font=FONT_BOLD,
               padx=14, pady=4, bd=0, cursor='hand2')
        btn_cancel.pack(side=LEFT, padx=6)
        _bind_hover(btn_cancel, COLOR_BTN_ALT, '#4b5563')

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
            self._hint_label.config(text="请输入文件夹名称", fg=COLOR_TEXT_WEAK)
            return
        full = os.path.join(self._base_dir, name)
        if os.path.exists(full):
            self._hint_label.config(text="该文件夹已存在，创建后将合并内容", fg=COLOR_WARNING)
        else:
            self._hint_label.config(text=f"将创建：{full}", fg=COLOR_SUCCESS)

    def _ok(self):
        name = self._entry.get().strip()
        if not name:
            self._hint_label.config(text="文件夹名称不能为空！", fg=COLOR_DANGER)
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
    def __init__(self, parent, folder_count, keys, folder_names=None):
        super().__init__(parent)
        self.title("自定义快捷键")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=COLOR_CARD)
        self.result_keys = list(keys)
        self.folder_count = folder_count
        self._folder_names = folder_names or []
        self.entries = []

        Label(self, text="设置各文件夹快捷键（单个字母/数字）",
              font=FONT_BOLD, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
                  row=0, column=0, columnspan=3, padx=20, pady=(14, 8))

        Label(self, text="文件夹", font=FONT_BOLD, bg=COLOR_CARD,
              fg=COLOR_TEXT).grid(row=1, column=0, padx=10)
        Label(self, text="快捷键", font=FONT_BOLD, bg=COLOR_CARD,
              fg=COLOR_TEXT).grid(row=1, column=1, padx=10)
        Label(self, text="说明",   font=FONT_BOLD, bg=COLOR_CARD,
              fg=COLOR_TEXT).grid(row=1, column=2, padx=10)

        for i in range(folder_count):
            name = self._folder_names[i] if i < len(self._folder_names) else f"文件夹 {i+1}"
            Label(self, text=name, font=FONT_NORMAL, bg=COLOR_CARD,
                  fg=COLOR_TEXT).grid(
                row=i+2, column=0, padx=10, pady=4)
            var = StringVar(value=keys[i])
            e = Entry(self, textvariable=var, width=4,
                      font=FONT_BOLD, justify='center',
                      bd=1, relief=SUNKEN)
            e.grid(row=i+2, column=1, padx=10, pady=4)
            self.entries.append(var)
            Label(self, text="（单字符）", font=FONT_SMALL,
                  fg=COLOR_TEXT_WEAK, bg=COLOR_CARD).grid(
                      row=i+2, column=2, padx=10)

        note = (f"保留键：W=跳过  Del=删除  I=元数据  Ctrl+Z=撤销  Tab=切换模式\n"
                "请勿将上述键设为分类快捷键")
        Label(self, text=note, font=FONT_SMALL,
              fg=COLOR_TEXT_WEAK, bg=COLOR_CARD).grid(
                  row=folder_count+2, column=0, columnspan=3,
                  padx=16, pady=(8, 4))

        btn_frm = Frame(self, bg=COLOR_CARD)
        btn_frm.grid(row=folder_count+3, column=0, columnspan=3, pady=12)
        btn_ok = Button(btn_frm, text=" 确定 ", command=self._ok,
               bg=COLOR_BTN, fg=COLOR_BTN_FG,
               font=FONT_BOLD, padx=12, pady=4,
               bd=0, cursor='hand2')
        btn_ok.pack(side=LEFT, padx=6)
        _bind_hover(btn_ok, COLOR_BTN, '#2563eb')
        btn_cancel = Button(btn_frm, text=" 取消 ", command=self.destroy,
               bg=COLOR_BTN_ALT, fg=COLOR_BTN_FG,
               font=FONT_BOLD, padx=12, pady=4,
               bd=0, cursor='hand2')
        btn_cancel.pack(side=LEFT, padx=6)
        _bind_hover(btn_cancel, COLOR_BTN_ALT, '#4b5563')
        btn_reset = Button(btn_frm, text=" 重置默认 ", command=self._reset,
               bg='#e5e7eb', fg=COLOR_TEXT,
               font=FONT_NORMAL, padx=12, pady=4,
               bd=0, cursor='hand2')
        btn_reset.pack(side=LEFT, padx=6)
        _bind_hover(btn_reset, '#e5e7eb', '#d1d5db')

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
        self.root.title(f"图片分类工具 v{__version__}")
        
        self.config_file = "phoo_config.json"

        # ── 所有变量必须在 load_config 之前定义 ──
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

        # ── 加载配置（在所有变量创建之后）──
        self.load_config()

        # ── 窗口几何信息（需在 load_config 之后）──
        saved_geometry = getattr(self, '_saved_geometry', '')
        if saved_geometry:
            try:
                self.root.geometry(saved_geometry)
            except:
                self.root.geometry('1200x800')
        else:
            self.root.geometry('1200x800')
        self.root.resizable(True, True)

        import tkinter.font as tkfont
        self.default_font = tkfont.nametofont("TkDefaultFont")
        self.default_font.configure(size=11)
        self.root.option_add("*Font", self.default_font)
        self.root.configure(bg=COLOR_BG)
        # ttk 样式
        self._ttk_style = ttk.Style()
        self._ttk_style.configure('TCombobox', font=FONT_NORMAL)
        self._ttk_style.map('TCombobox',
            fieldbackground=[('readonly', 'white')],
            selectbackground=[('readonly', '#dbeafe')])

        self.all_images = []
        self.ptr = 0
        self.history = []
        self.skip_stack = []

        # ── 待应用操作队列 ──
        # 每条: {'action': 'move'|'copy'|'delete', 'src': 原路径, 'dst': 目标路径, 'idx': 原索引}
        self.pending_actions = []

        # ── 动图播放状态 ──
        self._motion_playing = False   # 是否正在播放动图
        self._motion_after_id = None   # after() 定时器 ID
        self._motion_cap = None        # OpenCV VideoCapture 对象
        self._motion_temp_file = None  # 嵌入视频提取后的临时文件路径

        # ── .livp 悬停播放状态 ──
        self._livp_hover_after = None   # 悬停定时器 ID（0.2s 延迟）
        self._livp_static_img = None    # 当前 .livp 的静态 PIL Image（用于恢复）
        self._livp_video_path = None    # 当前 .livp 解压出的 MOV 临时路径

        # ── 旋转状态 ──
        self._current_rotation = 0     # 当前旋转角度（90 的倍数）

        # ── Live Photo 配对 MOV 集合（被 load_images 排除的 .mov） ──
        self._live_mov_set = set()

        # ── 进度恢复 ──
        self._saved_ptr = 0          # 从配置读取的上次 ptr
        self._saved_anchor = None    # 上次退出时的锚定文件名（用于精确恢复）

        self.img_ext = ('.jpg','.jpeg','.png','.gif','.bmp','.tiff','.ico','.heic')
        self.vid_ext = ('.mp4','.avi','.mov','.wmv','.flv','.mkv')
        self.swf_ext = ('.swf',)
        self.livp_ext = ('.livp',)   # iPhone 实况照片（ZIP 内含 HEIC + MOV）
        self.supported_formats = self.img_ext + self.vid_ext + self.swf_ext + self.livp_ext

        # ── 查重设置 ──
        self.dedup_enabled = BooleanVar(value=False)   # 是否启用查重
        self.dedup_mode    = StringVar(value="skip")     # 处理方式：skip=跳过, delete=删除, ask=每次询问
        # 查重缓存：(文件名, 大小) → [输出文件夹中的路径列表]
        self._dedup_hash_cache = {}          # {(fname, fsize): [path1, path2, ...]}
        self._dedup_hash_valid = False     # 缓存是否有效
        self._dedup_scanning = False       # 是否正在后台扫描
        self._dedup_scan_thread = None       # 扫描线程引用
        self._dedup_progress_dlg = None    # 扫描进度对话框

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
        # ── 工具栏卡片 ──
        toolbar_card = Frame(self.root, bg=COLOR_CARD,
                             highlightbackground=COLOR_BORDER,
                             highlightthickness=1)
        toolbar_card.pack(fill=X, padx=SPACE_LG, pady=(SPACE_MD, SPACE_XS))

        # ── 第一行：输入路径 ──
        line1 = Frame(toolbar_card, bg=COLOR_CARD)
        line1.pack(fill=X, padx=SPACE_SM, pady=(SPACE_SM, SPACE_XS))
        Label(line1, text="输入路径：", bg=COLOR_CARD, font=FONT_BOLD,
              fg=COLOR_TEXT).pack(side=LEFT)
        self.input_entry = HintEntry(line1, textvariable=self.input_folder,
                                     hint='这里是需要处理的文件夹路径',
                                     state='readonly')
        self.input_entry.pack(side=LEFT, fill=X, expand=True, padx=SPACE_XS)
        btn_browse = Button(line1, text="浏览…", command=self.browse_input,
               bg=COLOR_BTN, fg=COLOR_BTN_FG, font=FONT_BOLD,
               padx=10, pady=3, bd=0, cursor='hand2')
        btn_browse.pack(side=LEFT, padx=SPACE_XS)
        _bind_hover(btn_browse, COLOR_BTN, '#2563eb')
        Checkbutton(line1, text="包含子文件夹", variable=self.inc_subfolders,
                    command=self.load_images, bg=COLOR_CARD,
                    activebackground=COLOR_CARD,
                    fg=COLOR_TEXT, selectcolor=COLOR_ACCENT,
                    font=FONT_SMALL).pack(side=LEFT, padx=SPACE_XS)

        # 分隔线
        Frame(toolbar_card, height=1, bg=COLOR_BORDER).pack(fill=X, padx=SPACE_SM)

        # ── 第二行：排序 + 缩放 + 复制/移动 + 撤销 ──
        line2 = Frame(toolbar_card, bg=COLOR_CARD)
        line2.pack(fill=X, padx=SPACE_SM, pady=SPACE_XS)

        Label(line2, text="排序：", bg=COLOR_CARD, font=FONT_BOLD,
              fg=COLOR_TEXT).pack(side=LEFT)
        sort_frm = Frame(line2, bg=COLOR_CARD)
        sort_frm.pack(side=LEFT)
        for txt, val in [("时间↑","time"), ("大小↑","size"), ("名称↑","name")]:
            Radiobutton(sort_frm, text=txt, variable=self.sort_method,
                       value=val, command=self.load_images,
                       bg=COLOR_CARD, activebackground=COLOR_CARD,
                       fg=COLOR_TEXT, selectcolor=COLOR_ACCENT,
                       font=FONT_SMALL).pack(side=LEFT, padx=3)
        Checkbutton(sort_frm, text="倒序", variable=self.reverse_sort,
                   command=self.load_images,
                   bg=COLOR_CARD, activebackground=COLOR_CARD,
                   fg=COLOR_TEXT, selectcolor=COLOR_ACCENT,
                   font=FONT_SMALL).pack(side=LEFT, padx=SPACE_SM)

        Frame(line2, bg=COLOR_CARD).pack(side=LEFT, fill=X, expand=True)

        Label(line2, text="缩放：", bg=COLOR_CARD, font=FONT_BOLD,
              fg=COLOR_TEXT).pack(side=LEFT)
        scale_frame = Frame(line2, bg=COLOR_CARD)
        scale_frame.pack(side=LEFT, padx=SPACE_XS)
        ttk.Combobox(scale_frame, textvariable=self.scale_mode,
                    values=["完整", "填充", "原始"],
                    state="readonly", width=5).pack(side=LEFT)
        self.scale_mode.trace_add('write', self.on_display_option_change)

        Checkbutton(line2, text="小图不放大", variable=self.dont_enlarge,
                   command=self.on_display_option_change,
                   bg=COLOR_CARD, activebackground=COLOR_CARD,
                   fg=COLOR_TEXT, selectcolor=COLOR_ACCENT,
                   font=FONT_SMALL).pack(side=LEFT, padx=SPACE_XS)

        # 复制/移动 + 撤销（右侧）
        mode_frm = Frame(line2, bg=COLOR_CARD)
        mode_frm.pack(side=RIGHT)
        Radiobutton(mode_frm, text="复制", variable=self.copy_mode, value=True,
                    bg=COLOR_CARD, activebackground=COLOR_CARD,
                    fg=COLOR_TEXT, selectcolor=COLOR_ACCENT,
                    font=FONT_SMALL).pack(side=LEFT)
        Radiobutton(mode_frm, text="移动", variable=self.copy_mode, value=False,
                    bg=COLOR_CARD, activebackground=COLOR_CARD,
                    fg=COLOR_TEXT, selectcolor=COLOR_ACCENT,
                    font=FONT_SMALL).pack(side=LEFT)
        Label(mode_frm, text="(Tab)", font=FONT_SMALL, fg=COLOR_TEXT_WEAK,
              bg=COLOR_CARD).pack(side=LEFT, padx=(SPACE_XS, 0))
        btn_undo = Button(mode_frm, text="↩ 撤销", command=self.undo,
               bg=COLOR_BTN_ALT, fg=COLOR_BTN_FG, font=FONT_BOLD,
               padx=10, pady=3, bd=0, cursor='hand2')
        btn_undo.pack(side=LEFT, padx=(SPACE_MD, 0))
        _bind_hover(btn_undo, COLOR_BTN_ALT, '#4b5563')

        # 分隔线
        Frame(toolbar_card, height=1, bg=COLOR_BORDER).pack(fill=X, padx=SPACE_SM)

        # ── 第三行：文件夹数量 + 自定义快捷键 ──
        line3 = Frame(toolbar_card, bg=COLOR_CARD)
        line3.pack(fill=X, padx=SPACE_SM, pady=(SPACE_XS, SPACE_SM))

        Label(line3, text="分类文件夹：", bg=COLOR_CARD, font=FONT_BOLD,
              fg=COLOR_TEXT).pack(side=LEFT)
        self._count_spinbox = Spinbox(
            line3, from_=2, to=MAX_FOLDERS,
            textvariable=self.folder_count_var,
            width=4, state='readonly',
            font=FONT_BOLD,
            command=self._on_folder_count_change)
        self._count_spinbox.pack(side=LEFT, padx=(0, SPACE_MD))

        btn_new_sub = Button(line3, text="✚ 新建分类",
               command=self._global_create_subfolder,
               bg=COLOR_SUCCESS, fg='white', font=FONT_BOLD,
               padx=8, pady=3, bd=0, cursor='hand2')
        btn_new_sub.pack(side=LEFT, padx=(0, SPACE_XS))
        _bind_hover(btn_new_sub, COLOR_SUCCESS, '#059669')

        btn_keys = Button(line3, text="⌨ 自定义",
               command=self._open_keybind_dialog,
               bg=COLOR_BTN_ALT, fg=COLOR_BTN_FG, font=FONT_BOLD,
               padx=10, pady=3, bd=0, cursor='hand2')
        btn_keys.pack(side=LEFT, padx=SPACE_XS)
        _bind_hover(btn_keys, COLOR_BTN_ALT, '#4b5563')

        # 快捷键预览标签（动态更新）
        self._key_preview_var = StringVar()
        Label(line3, textvariable=self._key_preview_var,
              font=FONT_SMALL, fg=COLOR_TEXT_WEAK,
              bg=COLOR_CARD).pack(side=LEFT, padx=(SPACE_MD, 0))
        self._refresh_key_preview()

        # ── 查重按钮（右侧）──
        btn_dedup = Button(line3, text="🔍 查重",
               command=self._show_dedup_settings,
               bg='#e5e7eb', fg=COLOR_TEXT, font=FONT_NORMAL,
               padx=10, pady=3, bd=0, cursor='hand2')
        btn_dedup.pack(side=RIGHT, padx=(SPACE_SM, 0))
        _bind_hover(btn_dedup, '#e5e7eb', '#d1d5db')

        # ── 图片预览区 ──
        self.img_frame = Frame(self.root, bg=COLOR_CARD,
                              highlightbackground=COLOR_BORDER,
                              highlightthickness=1)
        self.img_frame.pack(fill=BOTH, expand=True, padx=SPACE_LG, pady=SPACE_XS)
        self.img_frame.pack_propagate(False)

        self.img_label = Label(self.img_frame, bg=COLOR_CARD, anchor=CENTER)
        self.img_label.pack(fill=BOTH, expand=True)
        self.img_label.bind("<Double-Button-1>", self.open_current_file)

        # ── 预览区内底部：文件名显示（覆盖在素材上）──
        self._filename_label = Label(
            self.img_frame, text="", anchor=S,
            bg=COLOR_CARD, fg=COLOR_TEXT_WEAK,
            font=FONT_SMALL, padx=SPACE_SM, pady=SPACE_XS)
        self._filename_label.place(relx=0.5, rely=1.0, anchor=S, y=-4)

        # ── 预览区右上角：文件类型 + 拍摄日期 + 扩展元数据 ──
        self._info_expanded = False  # 是否展开完整元数据
        self._info_label = Label(
            self.img_frame, text="", anchor='ne',
            bg='#fafafa', fg=COLOR_TEXT,
            font=FONT_SMALL, padx=SPACE_SM, pady=SPACE_XS,
            justify=RIGHT, relief=FLAT, bd=0,
            cursor='hand2')
        self._info_label.place(relx=1.0, rely=0.0, anchor='ne')
        self._info_label.bind('<Button-1>', lambda e: self._toggle_info_expand())

        # ── 预览区左下角：重复提醒 ──
        self._dup_label = Label(
            self.img_frame, text="", anchor='sw',
            bg='#fafafa', fg=COLOR_DANGER,
            font=FONT_SMALL, padx=SPACE_SM, pady=SPACE_XS,
            relief=FLAT, bd=0)
        self._dup_label.place(relx=0.0, rely=1.0, anchor='sw')

        # ── 预览区左上角：素材类型标签 ──
        self._type_label = Label(
            self.img_frame, text="", anchor='nw',
            bg='#fafafa', fg=COLOR_TEXT,
            font=FONT_SMALL, padx=SPACE_SM, pady=SPACE_XS,
            relief=FLAT, bd=0)
        self._type_label.place(relx=0.0, rely=0.0, anchor='nw')

        # ── 旋转按钮（预览区右下角）──
        rot_frame = Frame(self.img_frame, bg='#fafafa')
        rot_frame.place(relx=1.0, rely=1.0, anchor='se', x=-4, y=-4)

        self._rot_label = Label(rot_frame, text="", bg='#fafafa',
                                font=FONT_SMALL, fg=COLOR_TEXT_WEAK)
        self._rot_label.pack(side=LEFT, padx=(0, SPACE_SM))

        btn_rot_kw = dict(bg=COLOR_BTN_ALT, fg=COLOR_BTN_FG,
                          activebackground='#5b6270', activeforeground='white',
                          font=FONT_SMALL, bd=0, padx=8, pady=1, cursor='hand2')
        Button(rot_frame, text="↺", command=self._rotate_left,
               **btn_rot_kw).pack(side=LEFT, padx=1)
        Button(rot_frame, text="↻", command=self._rotate_right,
               **btn_rot_kw).pack(side=LEFT, padx=1)

        # ── 输出文件夹行（动态生成，卡片包裹）──
        self.out_card = Frame(self.root, bg=COLOR_CARD,
                              highlightbackground=COLOR_BORDER,
                              highlightthickness=1)
        self.out_card.pack(fill=X, padx=SPACE_LG, pady=(SPACE_XS, SPACE_SM))
        self.out_line = Frame(self.out_card, bg=COLOR_CARD)
        self.out_line.pack(fill=X, padx=SPACE_SM, pady=SPACE_SM)
        self.out_entries = []
        self._build_output_rows()

        # ── 状态栏 ──
        status_bar = Frame(self.root, bg=COLOR_STATUS_BG)
        status_bar.pack(side=BOTTOM, fill=X)
        # 顶部分隔线
        Frame(status_bar, height=1, bg=COLOR_BORDER).pack(fill=X)

        self.status = Label(status_bar, text="", bd=0, relief=FLAT, anchor=W,
                           bg=COLOR_STATUS_BG, font=FONT_SMALL,
                           fg=COLOR_TEXT_SEC,
                           padx=SPACE_SM, pady=SPACE_XS)
        self.status.pack(side=LEFT, fill=X, expand=True)

        # 进度条
        self._progress_var = DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(
            status_bar, variable=self._progress_var,
            maximum=100, length=140, mode='determinate')
        self._progress_bar.pack(side=RIGHT, padx=(0, SPACE_SM), pady=2)
        self._progress_label = Label(
            status_bar, text="", bg=COLOR_STATUS_BG,
            font=FONT_SMALL, fg=COLOR_TEXT_SEC)
        self._progress_label.pack(side=RIGHT, padx=(0, SPACE_XS), pady=2)

        # 应用按钮
        self._apply_btn = Button(
            status_bar, text="应用 (0)",
            command=self.apply_pending,
            bg=COLOR_SUCCESS, fg='white',
            bd=0, padx=10, pady=2,
            font=FONT_SMALL, cursor='hand2',
            state=DISABLED
        )
        self._apply_btn.pack(side=RIGHT, padx=(0, SPACE_XS), pady=2)
        _bind_hover(self._apply_btn, COLOR_SUCCESS, '#059669')

        # ── 绑定快捷键 ──
        self._bind_hotkeys()

        # ── 窗口大小变化时自动缩放图片 ──
        self._resize_job = None  # 节流定时器
        self.root.bind('<Configure>', self._on_window_resize)

        self.update_display()

    def _on_window_resize(self, event):
        """窗口大小变化时自动重新缩放图片"""
        # 忽略非窗口事件（如子控件）
        if event.widget != self.root:
            return
        # 取消之前的定时器
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        # 延迟执行（节流），避免频繁触发
        self._resize_job = self.root.after(150, self._reload_current_image)

    def _reload_current_image(self):
        """重新加载并显示当前图片（用于窗口大小变化后自适应）"""
        if self.all_images and self.ptr < len(self.all_images):
            self.show_current()

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

            cell = Frame(self.out_line, bg=COLOR_CARD)
            cell.grid(row=row, column=col, sticky='ew', padx=(0, SPACE_SM) if col < COLS - 1 else 0,
                      pady=(0, SPACE_XS) if row < (n - 1) // COLS else 0)

            btn_text = f"[{key}] 文件夹{i+1}"
            btn_folder = Button(cell, text=btn_text,
                   command=lambda f=fo: self.browse_output(f),
                   bg=COLOR_BTN, fg=COLOR_BTN_FG, font=FONT_BOLD,
                   padx=6, pady=3, bd=0,
                   cursor='hand2')
            btn_folder.pack(side=LEFT)
            _bind_hover(btn_folder, COLOR_BTN, '#2563eb')
            hint = f'输出文件夹 {i+1} 的路径'
            e = HintEntry(cell, textvariable_ref=fo["path"],
                          hint=hint, shorten_path=True, state='readonly')
            e.pack(side=LEFT, fill=X, expand=True, padx=(SPACE_XS, 0))
            # 点击路径文本可打开对应文件夹
            e.config(cursor='hand2')
            e.bind('<Button-1>', lambda evt, idx=i: self._open_folder_by_idx(idx))
            self.out_entries.append(e)

            # 文件夹已有照片数标签（点击可打开文件夹）
            cnt_lbl = Label(cell, text="", bg=COLOR_CARD,
                            font=FONT_SMALL, fg=COLOR_SUCCESS, width=6,
                            cursor='hand2')
            cnt_lbl.pack(side=LEFT, padx=(SPACE_XS, 0))
            cnt_lbl.bind('<Button-1>', lambda e, idx=i: self._open_folder_by_idx(idx))
            self._folder_count_labels.append(cnt_lbl)

            # 删除该分类按钮（仅当 > 2 个时可用）
            can_del = n > 2
            btn_del = Button(cell, text="✕",
                   command=lambda idx=i: self.remove_folder(idx),
                   bg='#fce7e7' if can_del else '#f3f4f6',
                   fg=COLOR_DANGER if can_del else COLOR_TEXT_WEAK,
                   font=('', 10, 'bold'),
                   padx=4, pady=1, bd=0,
                   cursor='hand2' if can_del else 'arrow',
                   state=NORMAL if can_del else DISABLED)
            btn_del.pack(side=LEFT, padx=(SPACE_XS, 0))
            if can_del:
                _bind_hover(btn_del, '#fce7e7', '#fecaca')

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
        folder_names = []
        for i in range(n):
            p = self.output_folders[i]["path"].get()
            folder_names.append(os.path.basename(p) if p else f"文件夹{i+1}")
        dlg = KeybindDialog(self.root, n, self.hotkeys[:n], folder_names)
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

    def _show_toast(self, title, message, duration=3500):
        """显示一个浮窗弱提醒，duration 毫秒后自动消失"""
        toast = Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes('-topmost', True)
        toast.configure(bg=COLOR_CARD, highlightbackground=COLOR_BORDER,
                        highlightthickness=1)
        toast.resizable(False, False)

        frm = Frame(toast, bg=COLOR_CARD, padx=18, pady=12)
        frm.pack()

        Label(frm, text=title, font=FONT_BOLD, bg=COLOR_CARD,
              fg=COLOR_SUCCESS).pack(anchor='w')
        Label(frm, text=message, font=FONT_SMALL, bg=COLOR_CARD,
              fg=COLOR_TEXT_SEC, justify=LEFT).pack(anchor='w', pady=(4, 0))

        # 定位到主窗口中下方
        toast.update_idletasks()
        tw, th = toast.winfo_width(), toast.winfo_height()
        rx = self.root.winfo_x() + (self.root.winfo_width() - tw) // 2
        ry = self.root.winfo_y() + self.root.winfo_height() - th - 60
        toast.geometry(f"+{rx}+{ry}")

        toast.after(duration, toast.destroy)

    def _on_classify_done(self):
        """所有文件分类完毕后的处理"""
        count = len(self.pending_actions)
        action = "复制" if self.copy_mode.get() else "移动"
        self.img_label.config(
            text=f"\n\n  ✅ 全部分类完成！\n\n"
                 f"  共 {count} 项待{action}操作\n\n"
                 f"  请点击「应用」执行\n",
            fg=COLOR_SUCCESS, font=FONT_WELCOME,
            bg=COLOR_CARD, justify=CENTER)
        self._type_label.config(text="")
        self._dup_label.config(text="")
        self._show_toast(
            "✅ 全部分类完成",
            f"共 {count} 项待{action}操作，请点击「应用」执行")

    # ──────────────────────────────────────────────
    #  原有逻辑（基本不变）
    # ──────────────────────────────────────────────
    def on_display_option_change(self, *args):
        if self.all_images:
            self.show_current()

    def load_images(self):
        self.all_images = []
        self._live_mov_set.clear()
        if not self.input_folder.get(): return
        root_path = self.input_folder.get()
        if not os.path.exists(root_path): return

        # 先收集所有符合条件的文件
        all_files = []
        if self.inc_subfolders.get():
            for r, _, fs in os.walk(root_path):
                for f in fs:
                    if f.lower().endswith(self.supported_formats):
                        all_files.append(os.path.join(r, f))
        else:
            for f in os.listdir(root_path):
                if f.lower().endswith(self.supported_formats):
                    full = os.path.join(root_path, f)
                    if os.path.isfile(full):
                        all_files.append(full)

        # ── 排除 Live Photo 配对的 .mov 文件（与 .heic/.jpg/.livp 等同名） ──
        img_basenames = set()
        for fp in all_files:
            ext = os.path.splitext(fp)[1].lower()
            if ext in ('.heic', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.livp'):
                img_basenames.add(os.path.splitext(fp)[0].lower())

        for fp in all_files:
            ext = os.path.splitext(fp)[1].lower()
            if ext == '.mov':
                base = os.path.splitext(fp)[0].lower()
                if base in img_basenames and os.path.getsize(fp) > 0:
                    self._live_mov_set.add(fp)
                    continue
            # ── 排除 vivo 配对的 .mp4 文件（与 .jpg/.jpeg 同名，作为图片的配对视频）──
            if ext == '.mp4':
                base = os.path.splitext(fp)[0].lower()
                if base in img_basenames and os.path.getsize(fp) > 0:
                    continue
            self.all_images.append(fp)

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
            # 分类完毕 vs 初始无文件
            if self.pending_actions:
                self._on_classify_done()
            else:
                self.show_error(f"目录：{self.input_folder.get()} 没有图片")
            return
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
            "\n\n"
            "📷  Phoo\n"
            "    图片 / 视频分类工具\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            f"  分类快捷键：{key_list}\n"
            "\n"
            "  W  跳过当前文件\n"
            "  Del  标记删除\n"
            "  I  查看文件元数据\n"
            "  Ctrl+Z  撤销上一步\n"
            "  Tab  切换复制/移动\n"
            "  双击  用系统程序打开\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "  选择输入文件夹，开始分类 →\n"
        )
        self.img_label.config(text=txt, fg=COLOR_TEXT_SEC,
                            font=FONT_WELCOME,
                            bg=COLOR_CARD, justify=CENTER)
        self._type_label.config(text="")

    def show_error(self, msg):
        self.img_label.config(text=msg, fg=COLOR_DANGER,
                             font=FONT_NORMAL, bg=COLOR_CARD)

    # ──────────────────────────────────────────────
    #  查重功能核心方法
    # ──────────────────────────────────────────────
    def _compute_file_hash(self, filepath, chunk_size=1048576):
        """计算文件 MD5 哈希，分块读取支持大文件，默认1MB分块"""
        h = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def _scan_output_hashes(self):
        """扫描所有输出文件夹，建立哈希缓存（后台线程+进度条）"""
        # 如果正在扫描，直接返回
        if self._dedup_scanning:
            return

        self._dedup_scanning = True
        self._dedup_hash_cache.clear()
        self._dedup_hash_valid = False
        n = self.folder_count_var.get()

        # 收集所有需要扫描的文件
        files_to_scan = []
        for i in range(n):
            path = self.output_folders[i]["path"].get()
            if not path or not os.path.isdir(path):
                continue
            for f in os.listdir(path):
                full = os.path.join(path, f)
                if os.path.isfile(full) and f.lower().endswith(self.supported_formats):
                    files_to_scan.append(full)

        total = len(files_to_scan)
        if total == 0:
            self._dedup_hash_valid = True
            self._dedup_scanning = False
            return

        # 创建进度条对话框
        self._show_scan_progress(total)

        # 启动后台扫描线程
        import threading
        self._dedup_scan_thread = threading.Thread(
            target=self._bg_scan_worker,
            args=(files_to_scan,),
            daemon=True
        )
        self._dedup_scan_thread.start()

    def _show_scan_progress(self, total):
        """显示扫描进度对话框"""
        if self._dedup_progress_dlg:
            try:
                self._dedup_progress_dlg.destroy()
            except Exception:
                pass

        dlg = Toplevel(self.root)
        dlg.title("查重扫描")
        dlg.resizable(False, False)
        dlg.configure(bg=COLOR_CARD)
        dlg.transient(self.root)
        dlg.grab_set()

        # 居中
        dlg.update_idletasks()
        dw, dh = 400, 120
        x = self.root.winfo_x() + (self.root.winfo_width() - dw) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dh) // 2
        dlg.geometry(f"{dw}x{dh}+{x}+{y}")

        Label(dlg, text="🔍 正在扫描输出文件夹...", font=FONT_BOLD,
              bg=COLOR_CARD, fg=COLOR_TEXT).pack(pady=(15, 10))

        # 进度条
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Custom.Horizontal.TProgressbar",
                     thickness=20, borderwidth=0)
        pbar = ttk.Progressbar(dlg, maximum=total, value=0,
                             mode='determinate', style="Custom.Horizontal.TProgressbar")
        pbar.pack(fill=X, padx=30, pady=5)

        self._scan_progress_var = StringVar(value=f"0 / {total}")
        Label(dlg, textvariable=self._scan_progress_var, font=FONT_SMALL,
              bg=COLOR_CARD, fg=COLOR_TEXT_SEC).pack()

        self._dedup_progress_dlg = dlg
        self._scan_pbar = pbar

    def _bg_scan_worker(self, files_to_scan):
        """后台扫描线程"""
        total = len(files_to_scan)
        scanned = 0
        for full in files_to_scan:
            try:
                fsize = os.path.getsize(full)
                fname = os.path.basename(full)
                # 记录（文件名, 大小）作为查重依据
                key = (fname, fsize)
                if key not in self._dedup_hash_cache:
                    self._dedup_hash_cache[key] = []
                self._dedup_hash_cache[key].append(full)
            except Exception:
                pass

            scanned += 1

            # 每10个文件更新一次UI
            if scanned % 10 == 0 or scanned == total:
                self.root.after(0, lambda s=scanned, t=total: self._update_scan_progress(s, t))

        # 扫描完成
        self.root.after(0, self._close_scan_progress)

    def _update_scan_progress(self, scanned, total):
        """更新进度条"""
        if self._scan_pbar:
            self._scan_pbar['value'] = scanned
        if self._scan_progress_var:
            self._scan_progress_var.set(f"{scanned} / {total}")
        if self._dedup_progress_dlg:
            self._dedup_progress_dlg.update_idletasks()

    def _close_scan_progress(self):
        """关闭进度条对话框"""
        self._dedup_hash_valid = True
        self._dedup_scanning = False

        if self._dedup_progress_dlg:
            try:
                self._dedup_progress_dlg.destroy()
            except Exception:
                pass
            self._dedup_progress_dlg = None
            self._scan_pbar = None

        total = len(self._dedup_hash_cache)
        self._flash_status(f"✅ 文件扫描完成，共 {total} 个唯一文件", duration=3000)

    def _start_bg_scan(self):
        """启动后台扫描"""
        if not self._dedup_scanning:
            self._scan_output_hashes()

    def _check_duplicate(self, filepath):
        """
        检查当前文件是否已在输出文件夹中存在（文件名+大小匹配）
        返回：None（不重复）或 {'dst_path': ...}
        """
        if not self.dedup_enabled.get():
            return None

        if not self._dedup_hash_valid:
            self._scan_output_hashes()

        try:
            fsize = os.path.getsize(filepath)
            fname = os.path.basename(filepath)
            key = (fname, fsize)
        except Exception:
            return None

        dup_paths = self._dedup_hash_cache.get(key, [])
        if dup_paths:
            return {'dst_path': dup_paths[0]}
        return None

    def _show_duplicate_dialog(self, filepath, dup_info):
        """
        弹出重复文件处理对话框
        返回：'skip' / 'delete' / 'proceed'
        """
        filename = os.path.basename(filepath)
        dst_name = os.path.basename(dup_info['dst_path'])

        result = {'action': None}

        dlg = Toplevel(self.root)
        dlg.title("发现重复文件")
        dlg.resizable(False, False)
        dlg.configure(bg=COLOR_CARD)
        dlg.grab_set()
        dlg.transient(self.root)

        # 居中显示
        dlg.update_idletasks()
        dw, dh = 420, 280
        x = self.root.winfo_x() + (self.root.winfo_width() - dw) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dh) // 2
        dlg.geometry(f"{dw}x{dh}+{x}+{y}")

        # 标题
        Label(dlg, text="⚠️ 发现重复文件",
              font=('Microsoft YaHei', 12, 'bold'),
              bg=COLOR_CARD, fg=COLOR_WARNING).pack(pady=(18, 6))

        # 文件信息
        info_text = f"当前文件：{filename}\n已在输出文件夹中存在相同内容的文件：\n{dst_name}"
        Label(dlg, text=info_text, font=FONT_SMALL,
              bg=COLOR_CARD, fg=COLOR_TEXT, justify=LEFT).pack(padx=20, pady=(0, 10))

        btn_frame = Frame(dlg, bg=COLOR_CARD)
        btn_frame.pack(pady=(10, 0))

        def on_skip():
            result['action'] = 'skip'
            dlg.destroy()

        def on_delete():
            result['action'] = 'delete'
            dlg.destroy()

        def on_proceed():
            result['action'] = 'proceed'
            dlg.destroy()

        def on_disable():
            result['action'] = 'disable'
            dlg.destroy()

        Button(btn_frame, text="跳过此文件", command=on_skip,
               bg=COLOR_BTN_ALT, fg='white', font=FONT_BOLD,
               padx=12, pady=5, bd=0, cursor='hand2').pack(side=LEFT, padx=4)
        _bind_hover(btn_frame.winfo_children()[-1], COLOR_BTN_ALT, '#4b5563')

        Button(btn_frame, text="删除此文件", command=on_delete,
               bg=COLOR_DANGER, fg='white', font=FONT_BOLD,
               padx=12, pady=5, bd=0, cursor='hand2').pack(side=LEFT, padx=4)
        _bind_hover(btn_frame.winfo_children()[-1], COLOR_DANGER, '#dc2626')

        Button(btn_frame, text="仍然分类", command=on_proceed,
               bg=COLOR_SUCCESS, fg='white', font=FONT_BOLD,
               padx=12, pady=5, bd=0, cursor='hand2').pack(side=LEFT, padx=4)
        _bind_hover(btn_frame.winfo_children()[-1], COLOR_SUCCESS, '#059669')

        # 禁用查重按钮
        disable_frame = Frame(dlg, bg=COLOR_CARD)
        disable_frame.pack(pady=(12, 0))
        Button(disable_frame, text="本次不再提醒", command=on_disable,
               font=FONT_SMALL, bg='#e5e7eb', fg=COLOR_TEXT,
               padx=10, pady=3, bd=0, cursor='hand2').pack()
        _bind_hover(disable_frame.winfo_children()[-1], '#e5e7eb', '#d1d5db')

        dlg.protocol("WM_DELETE_WINDOW", on_proceed)  # 关闭窗口默认继续分类
        self.root.wait_window(dlg)

        action = result['action']
        if action == 'disable':
            self.dedup_enabled.set(False)
            return 'proceed'
        return action if action else 'proceed'

    def _show_dedup_settings(self):
        """查重设置对话框"""
        dlg = Toplevel(self.root)
        dlg.title("查重设置")
        dlg.resizable(False, False)
        dlg.configure(bg=COLOR_CARD)
        dlg.grab_set()
        dlg.transient(self.root)

        # 居中
        dlg.update_idletasks()
        dw, dh = 360, 240
        x = self.root.winfo_x() + (self.root.winfo_width() - dw) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dh) // 2
        dlg.geometry(f"{dw}x{dh}+{x}+{y}")

        Label(dlg, text="🔍 查重设置",
              font=('Microsoft YaHei', 12, 'bold'),
              bg=COLOR_CARD, fg=COLOR_TEXT).pack(pady=(18, 10))

        # 启用查重
        Checkbutton(dlg, text="启用查重（检测已在输出文件夹中的重复文件）",
                    variable=self.dedup_enabled,
                    bg=COLOR_CARD, activebackground=COLOR_CARD,
                    fg=COLOR_TEXT, selectcolor=COLOR_ACCENT,
                    font=FONT_NORMAL, command=self._on_dedup_toggle).pack(anchor='w', padx=20, pady=(0, 10))

        # 处理方式
        mode_frame = Frame(dlg, bg=COLOR_CARD)
        mode_frame.pack(anchor='w', padx=20, pady=(0, 10))
        Label(mode_frame, text="重复时操作：", font=FONT_BOLD,
              bg=COLOR_CARD, fg=COLOR_TEXT).pack(side=LEFT)

        for txt, val in [("自动跳过", "skip"), ("自动删除", "delete"), ("每次询问", "ask")]:
            Radiobutton(mode_frame, text=txt, variable=self.dedup_mode,
                        value=val, bg=COLOR_CARD,
                        activebackground=COLOR_CARD,
                        fg=COLOR_TEXT, selectcolor=COLOR_ACCENT,
                        font=FONT_SMALL).pack(side=LEFT, padx=6)

        # 扫描按钮
        btn_frame = Frame(dlg, bg=COLOR_CARD)
        btn_frame.pack(pady=(10, 0))
        Button(btn_frame, text="立即扫描输出文件夹",
               command=lambda: [dlg.destroy(), self._manual_scan_dedup()],
               bg=COLOR_BTN, fg='white', font=FONT_BOLD,
               padx=12, pady=5, bd=0, cursor='hand2').pack(side=LEFT, padx=6)
        _bind_hover(btn_frame.winfo_children()[-1], COLOR_BTN, '#2563eb')

        Button(btn_frame, text="关闭", command=dlg.destroy,
               bg=COLOR_BTN_ALT, fg='white', font=FONT_BOLD,
               padx=12, pady=5, bd=0, cursor='hand2').pack(side=LEFT, padx=6)
        _bind_hover(btn_frame.winfo_children()[-1], COLOR_BTN_ALT, '#4b5563')

        dlg.wait_window(dlg)
        self.save_config()

    def _on_dedup_toggle(self):
        """启用/禁用查重时触发"""
        if self.dedup_enabled.get():
            self._dedup_hash_valid = False  # 启用时标记缓存需要刷新
            self._flash_status("🔍 查重已启用，下次分类时将扫描输出文件夹", duration=2000)
        else:
            self._flash_status("查重已禁用", duration=2000)

    def _manual_scan_dedup(self):
        """手动触发哈希扫描"""
        self._dedup_hash_valid = False
        self._scan_output_hashes()

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
        if ext in ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.heic'):
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

        # ── 1b. .livp 从内部图片读取 EXIF ──
        if ext == '.livp' and HAS_LIVP:
            try:
                livp = LivpFile(filepath)
                img = livp.image_pil()
                exif = getattr(img, '_getexif', lambda: None)()
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

        # 2d. 两位年份格式（如 24.6.13 / 24-06-13 / 24_06_13，常见于手动命名）
        #     格式A：YY.M.D[.HH.MM[.SS]] — 点号分隔，可选时分秒（贪心，先匹配最长）
        for pat in [
            r'(?<!\d)(\d{2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})(?!\d)',
            r'(?<!\d)(\d{2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})(?!\d)',
            r'(?<!\d)(\d{2})\.(\d{1,2})\.(\d{1,2})(?!\d)',
        ]:
            m = re.search(pat, basename)
            if m:
                g = [int(x) for x in m.groups()]
                yy, mo, day = g[0], g[1], g[2]
                if not (1 <= mo <= 12 and 1 <= day <= 31):
                    continue
                year = 2000 + yy
                try:
                    if len(g) == 6:
                        dt = datetime.datetime(year, mo, day, g[3], g[4], g[5])
                    elif len(g) == 5:
                        dt = datetime.datetime(year, mo, day, g[3], g[4])
                    else:
                        dt = datetime.datetime(year, mo, day)
                    if self._is_valid_date(dt):
                        fmt = "%Y-%m-%d %H:%M" if len(g) >= 5 else "%Y-%m-%d"
                        return dt.strftime(fmt)
                except ValueError:
                    continue
        #     格式B：YY-MM-DD 或 YY_MM_DD（防止误截4位年份末尾两位）
        m = re.search(r'(?<!\d)(\d{2})[-_](\d{2})[-_](\d{2})(?!\d)', basename)
        if m:
            yy, mo, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= mo <= 12 and 1 <= day <= 31:
                start = m.start()
                if not (start >= 2 and basename[start-2:start].isdigit()):
                    year = 2000 + yy
                    try:
                        dt = datetime.datetime(year, mo, day)
                        if self._is_valid_date(dt):
                            return dt.strftime("%Y-%m-%d")
                    except ValueError:
                        pass

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
        if ext not in ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.heic'):
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
        """将 EXIF GPS 的度分秒格式转为十进制坐标，兼容 Rational 和 float 两种格式"""
        def _to_float(v):
            try:
                return v[0] / v[1]  # Rational / IFDRational
            except TypeError:
                return float(v)     # 直接 float

        d = _to_float(dms[0])
        m = _to_float(dms[1])
        s = _to_float(dms[2])
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

        # 4. 两位年份格式（YY.M.D / YY-MM-DD / YY_MM_DD）
        for pat in [
            r'(?<!\d)(\d{2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})(?!\d)',
            r'(?<!\d)(\d{2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})(?!\d)',
            r'(?<!\d)(\d{2})\.(\d{1,2})\.(\d{1,2})(?!\d)',
        ]:
            m = re.search(pat, basename)
            if m:
                g = [int(x) for x in m.groups()]
                yy, mo, day = g[0], g[1], g[2]
                if not (1 <= mo <= 12 and 1 <= day <= 31):
                    continue
                year = 2000 + yy
                try:
                    if len(g) == 6:
                        dt = datetime.datetime(year, mo, day, g[3], g[4], g[5])
                    elif len(g) == 5:
                        dt = datetime.datetime(year, mo, day, g[3], g[4])
                    else:
                        dt = datetime.datetime(year, mo, day)
                    if self._is_valid_date(dt):
                        return dt
                except ValueError:
                    continue
        m = re.search(r'(?<!\d)(\d{2})[-_](\d{2})[-_](\d{2})(?!\d)', basename)
        if m:
            yy, mo, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= mo <= 12 and 1 <= day <= 31:
                start = m.start()
                if not (start >= 2 and basename[start-2:start].isdigit()):
                    year = 2000 + yy
                    try:
                        dt = datetime.datetime(year, mo, day)
                        if self._is_valid_date(dt):
                            return dt
                    except ValueError:
                        pass

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

    # ── 图片渲染（供 show_current 和旋转共用）─────────────────
    def _display_image(self, img):
        """按当前缩放模式将 PIL Image 显示到预览区（支持当前旋转角度）"""
        frame_w = self.img_frame.winfo_width() - 10
        frame_h = self.img_frame.winfo_height() - 10
        if frame_w < 50 or frame_h < 50:
            return

        # 应用旋转
        if self._current_rotation % 360 != 0:
            img = img.rotate(self._current_rotation, Image.Resampling.BICUBIC, expand=True)

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

    # ── 旋转操作 ─────────────────────────────────────────────
    def _rotate_left(self):
        """逆时针旋转 90°"""
        self._current_rotation = (self._current_rotation - 90) % 360
        self._apply_rotation_display()

    def _rotate_right(self):
        """顺时针旋转 90°"""
        self._current_rotation = (self._current_rotation + 90) % 360
        self._apply_rotation_display()

    def _apply_rotation_display(self):
        """重新加载当前图片并应用旋转"""
        if not self.all_images:
            return
        self._stop_motion_playback()
        f = self.all_images[self.ptr]
        ext = os.path.splitext(f)[1].lower()
        if ext in self.vid_ext or ext in self.swf_ext:
            return
        try:
            img = Image.open(f)
            self._display_image(img)
            # 更新旋转角度标签
            if self._current_rotation % 360 != 0:
                self._rot_label.config(text=f"已旋转 {self._current_rotation}°（移动时自动保存）")
            else:
                self._rot_label.config(text="")
        except Exception:
            pass

    def _get_rotated_image(self, filepath):
        """如果当前有旋转，返回旋转后的图片副本；否则返回 None"""
        if self._current_rotation % 360 == 0 or not self.all_images:
            return None
        if not os.path.abspath(self.all_images[self.ptr]) == os.path.abspath(filepath):
            return None
        try:
            img = Image.open(filepath)
            return img.rotate(self._current_rotation, Image.Resampling.BICUBIC, expand=True)
        except Exception:
            return None

    def _get_file_type_label(self, filepath):
        """返回文件类型的 emoji + 中文标签"""
        ext = os.path.splitext(filepath)[1].lower()
        if ext in self.vid_ext:
            return "🎬 视频"
        elif ext in self.swf_ext:
            return "🔦 Flash"
        elif ext in ('.jpg', '.jpeg'):
            return "🖼️ JPEG"
        elif ext == '.png':
            return "🖼️ PNG"
        elif ext == '.gif':
            return "🖼️ GIF"
        elif ext == '.bmp':
            return "🖼️ BMP"
        elif ext in ('.tiff', '.tif'):
            return "🖼️ TIFF"
        elif ext == '.ico':
            return "🔖 ICO"
        elif ext == '.heic':
            return "🖼️ HEIC"
        elif ext == '.livp':
            return "🎬 Live Photo"
        else:
            return f"📄 {ext}"

    def show_current(self):
        # ── 停止上一次动图播放 ──
        self._stop_motion_playback()
        # ── 重置旋转角度 ──
        self._current_rotation = 0
        self._rot_label.config(text="")

        if not self.all_images: return
        f = self.all_images[self.ptr]
        ext = os.path.splitext(f)[1].lower()

        if ext in self.swf_ext:
            # Flash 文件无法预览，仅提示
            self.img_label.config(
                image="",
                text=f"Flash 文件：{os.path.basename(f)}\n双击此处用默认程序打开",
                fg='#1a5fb4', font=FONT_NORMAL, bg='white')
        elif ext in self.livp_ext:
            # ── .livp 实况照片：默认显示静态图，悬停 0.2s 后播放视频 ──
            if HAS_LIVP:
                try:
                    livp = LivpFile(f)
                    img = livp.image_pil()
                    self._livp_static_img = img   # 保存静态图供恢复用
                    self._display_image(img)

                    # 预先解压 MOV 到临时文件（若有 cv2）
                    self._livp_video_path = None
                    if HAS_CV2:
                        vid_bytes = None
                        try:
                            vid_bytes = livp.video_bytes()
                        except Exception:
                            pass
                        if vid_bytes:
                            import tempfile as _tf
                            tmp = _tf.NamedTemporaryFile(delete=False, suffix='.mov')
                            tmp.write(vid_bytes)
                            tmp.close()
                            self._livp_video_path = tmp.name
                            self._motion_temp_file = tmp.name  # 交给 _stop_motion_playback 清理

                    # 绑定悬停事件
                    self._bind_livp_hover()

                except Exception as e:
                    self.img_label.config(
                        text=f"无法加载 .livp：{e}",
                        image="", fg='red', font=FONT_NORMAL, bg='white')
            else:
                self.img_label.config(
                    image="",
                    text=f"Live Photo：{os.path.basename(f)}\n（需要 livp.py 模块）\n双击此处用默认程序打开",
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
                self._display_image(img)

                # ── 检测并自动播放动图 ──
                motion = self._detect_motion_photo(f)
                if motion and HAS_CV2:
                    video_path = motion.get('video_path')
                    if motion.get('embedded') and not video_path:
                        video_path = self._extract_embedded_video(f)
                        if video_path:
                            self._motion_temp_file = video_path
                        else:
                            self._flash_status("⚠️ 动图视频提取失败", duration=3000)
                    if video_path:
                        seek_us = motion.get('presentation_us')
                        self._start_motion_playback(video_path, seek_us=seek_us)
            except Exception as e:
                self.img_label.config(text=f"无法加载图片：{e}", fg='red')

        # ── 自动校正文件日期（文件名日期 vs 创建时间偏差 > 1天则修正）──
        if self._fix_file_date(f):
            self._flash_status("📅 已校正文件日期为文件名记录的时间", duration=2500)

        # ── 更新右上角信息标签 ──
        self._update_info_label(f)

        # ── 更新左上角类型标签 ──
        self._type_label.config(text=self._get_file_type_label(f))

        # ── 更新底部文件名显示 ──
        self._filename_label.config(text=os.path.basename(f))

        # ── 异步查重检查（不阻塞UI）──
        if self.dedup_enabled.get():
            self.root.after(50, lambda: self._async_check_duplicate(f))

    def _async_check_duplicate(self, filepath):
        """异步检查当前文件是否在输出文件夹中存在（文件名+大小匹配）"""
        if not self.dedup_enabled.get():
            return

        # 如果缓存无效，后台扫描
        if not self._dedup_hash_valid:
            if not self._dedup_scanning:
                self.root.after(100, self._start_bg_scan)
            self._dup_label.config(text="🔄 扫描中...", fg=COLOR_TEXT_SEC)
            return

        # 文件名 + 大小匹配
        try:
            fsize = os.path.getsize(filepath)
            fname = os.path.basename(filepath)
            key = (fname, fsize)
        except Exception:
            return

        # 查找相同文件名+大小的文件
        dup_paths = self._dedup_hash_cache.get(key, [])
        if dup_paths:
            self._dup_label.config(
                text=f"⚠️ 重复: {os.path.basename(dup_paths[0])}",
                fg=COLOR_DANGER)
            return

        self._dup_label.config(text="✅ 未重复", fg=COLOR_SUCCESS)

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
        date_str = self._get_file_datetime(filepath)
        ext = os.path.splitext(filepath)[1].lower()

        # ── 日期来源标注 ──
        date_note = ""
        if date_str:
            basename = os.path.splitext(os.path.basename(filepath))[0]
            from_exif = False
            if ext in ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.heic'):
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

        # ── .livp：从内部图片提取 EXIF + 视频信息 ──
        livp_info = {}   # 存放 .livp 专属信息（内部格式/分辨率/视频时长等）
        if ext == '.livp' and HAS_LIVP:
            try:
                livp = LivpFile(filepath)
                img_pil = livp.image_pil()
                w, h = img_pil.width, img_pil.height
                livp_info['img_w'] = w
                livp_info['img_h'] = h
                livp_info['img_fmt'] = (livp.image_format or 'jpeg').upper()
                livp_info['img_name'] = livp.image_name or ''
                livp_info['vid_name'] = livp.video_name or ''
                # EXIF from internal image
                exif = getattr(img_pil, '_getexif', lambda: None)()
                if exif:
                    # 尝试用内部 EXIF 填充 exif_info（只补空缺）
                    from PIL.ExifTags import TAGS
                    _tag_map = {271: '设备_Make', 272: '设备_Model', 33437: 'FNumber',
                                33434: 'ExposureTime', 34855: 'ISOSpeedRatings',
                                37386: 'FocalLength', 41989: 'FocalLengthIn35mmFilm',
                                37385: 'Flash', 40962: 'PixelXDimension', 40963: 'PixelYDimension'}
                    # 直接调用完整的 EXIF 解析
                    import io as _io
                    buf = _io.BytesIO()
                    img_pil.save(buf, 'JPEG')
                    buf.seek(0)
                    _img2 = Image.open(buf)
                    _ex2 = _img2._getexif()
                    if _ex2 and not exif_info:
                        # 临时借用 _get_exif_data 的路径无法处理内存图，直接手动填入
                        make = _ex2.get(271, '')
                        model = _ex2.get(272, '')
                        if make and model:
                            exif_info['设备'] = model if model.startswith(make) else f"{make} {model}"
                        fnum = _ex2.get(33437)
                        if fnum:
                            try:
                                exif_info['光圈'] = f"f/{fnum[0]/fnum[1]:.1f}"
                            except Exception:
                                pass
                        exp = _ex2.get(33434)
                        if exp:
                            try:
                                n, d = exp
                                exif_info['快门'] = f"1/{d}s" if n == 1 else f"{n}/{d}s"
                            except Exception:
                                pass
                        iso = _ex2.get(34855)
                        if iso:
                            exif_info['ISO'] = str(iso)
                        focal = _ex2.get(37386)
                        if focal:
                            try:
                                exif_info['焦距'] = f"{focal[0]/focal[1]:.0f}mm"
                            except Exception:
                                pass
                        focal35 = _ex2.get(41989)
                        if focal35:
                            exif_info['等效焦距'] = f"{focal35}mm"
                        gps = _ex2.get(34853, {})
                        if isinstance(gps, dict):
                            lat_dms = gps.get(2)
                            lat_ref = gps.get(1)
                            lon_dms = gps.get(4)
                            lon_ref = gps.get(3)
                            if lat_dms and lat_ref and lon_dms and lon_ref:
                                try:
                                    lat = self._dms_to_decimal(lat_dms, lat_ref)
                                    lon = self._dms_to_decimal(lon_dms, lon_ref)
                                    exif_info['GPS纬度'] = f"{lat:.4f}° {lat_ref}"
                                    exif_info['GPS经度'] = f"{lon:.4f}° {lon_ref}"
                                except Exception:
                                    pass
                # 读取 MOV 视频信息（时长/帧率/分辨率）
                if HAS_CV2 and livp.video_name:
                    try:
                        import io as _io2, tempfile as _tf2
                        vbytes = livp.video_bytes()
                        tmp_v = _tf2.NamedTemporaryFile(delete=False, suffix='.mov')
                        tmp_v.write(vbytes)
                        tmp_v.close()
                        cap = cv2.VideoCapture(tmp_v.name)
                        if cap.isOpened():
                            vw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            vh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            vfps = cap.get(cv2.CAP_PROP_FPS)
                            vframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                            if vw > 0 and vh > 0:
                                livp_info['vid_res'] = f"{vw}×{vh}"
                            if vfps > 0 and vframes > 0:
                                dur = vframes / vfps
                                livp_info['vid_dur'] = f"{dur:.1f}s"
                                livp_info['vid_fps'] = f"{vfps:.0f}fps"
                            cap.release()
                        try:
                            os.remove(tmp_v.name)
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                img_pil = None
        else:
            img_pil = None

        # ── 位置信息判断 ──
        has_gps = ('GPS纬度' in exif_info and 'GPS经度' in exif_info)
        if has_gps:
            location_str = f"📍 {exif_info['GPS纬度']}, {exif_info['GPS经度']}"
        else:
            location_str = ""

        # ── 动图检测 ──
        motion = self._detect_motion_photo(filepath) if ext in self.img_ext else None
        motion_str = ""
        if ext == '.livp':
            # .livp 始终是 Live Photo
            hover_hint = " (悬停预览)" if HAS_CV2 and livp_info.get('vid_name') else ""
            motion_str = f"📸 Live Photo{hover_hint}"
        elif motion:
            motion_labels = {'apple': '🎬 Live Photo', 'android': '🎬 Motion Photo', 'vivo': '🎬 动图'}
            motion_str = motion_labels.get(motion['type'], '🎬 动图')

        lines = []
        if motion_str:
            lines.append(motion_str)
        if date_str:
            lines.append(f"{self._shorten_date(date_str)} {date_note}".strip())

        if not self._info_expanded:
            # ── 简洁模式 ──
            if ext == '.livp' and livp_info:
                # Live Photo 简洁：分辨率 | 设备 | 视频时长
                livp_parts = []
                if 'img_w' in livp_info and 'img_h' in livp_info:
                    livp_parts.append(self._resolution_label(livp_info['img_w'], livp_info['img_h']))
                if '设备' in exif_info:
                    livp_parts.append(exif_info['设备'])
                if 'vid_dur' in livp_info:
                    livp_parts.append(f"🎬{livp_info['vid_dur']}")
                if livp_parts:
                    lines.append("|".join(livp_parts))
                # 拍摄参数
                shot_parts = []
                for k in ('光圈', '快门', 'ISO'):
                    if k in exif_info:
                        shot_parts.append(exif_info[k])
                if shot_parts:
                    lines.append("|".join(shot_parts))
            elif ext in self.vid_ext and video_info:
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

            if location_str:
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

            # .livp 的详细信息
            if ext == '.livp' and livp_info:
                if 'img_w' in livp_info:
                    lines.append(f"📐 照片分辨率: {livp_info['img_w']} × {livp_info['img_h']}")
                if 'img_fmt' in livp_info:
                    lines.append(f"🖼️ 照片格式: {livp_info['img_fmt']}")
                if livp_info.get('vid_name'):
                    vid_line = f"🎬 视频: {livp_info.get('vid_res', '')} {livp_info.get('vid_fps', '')} {livp_info.get('vid_dur', '')}"
                    lines.append(vid_line.strip())

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

            # 图片 EXIF 详情（含 .livp 内部提取的）
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

            if location_str:
                lines.append(location_str)
            lines.append("[I] 收起 ▲")

        return lines

    def _update_info_label(self, filepath):
        """更新预览区右上角的信息标签"""
        lines = self._build_info_lines(filepath)
        self._info_label.config(text="\n".join(lines))

        # 双击打开 Google Maps（仅当有 GPS 坐标时生效）
        exif_info = self._get_exif_data(filepath)
        has_gps = ('GPS纬度' in exif_info and 'GPS经度' in exif_info)
        if has_gps:
            lat_str, lon_str = exif_info['GPS纬度'], exif_info['GPS经度']
            lat = float(re.search(r'[\d.]+', lat_str).group())
            lon = float(re.search(r'[\d.]+', lon_str).group())
            if 'S' in lat_str:
                lat = -lat
            if 'W' in lon_str:
                lon = -lon
            url = f"https://www.google.com/maps?q={lat},{lon}"
            self._info_label.bind('<Double-Button-1>',
                                 lambda e, u=url: webbrowser.open(u))
        else:
            self._info_label.unbind('<Double-Button-1>')

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

    # ── 动图（Live Photo / Motion Photo）检测 ──────────────────
    _GCAM_NS = 'http://ns.google.com/photos/1.0/camera/'

    def _detect_motion_photo(self, filepath):
        """检测动图，返回 dict 或 None。
        返回格式: {'type': 'apple'|'android'|'vivo', 'video_path': ...}
                  或 {'type': 'android', 'embedded': True, 'presentation_us': int|None}
        """
        base, ext = os.path.splitext(filepath)
        ext_lower = ext.lower()

        # ── 1. Apple Live Photo: 同名 .mov 配对 ──
        for mov_ext in ('.mov', '.MOV'):
            mov_path = base + mov_ext
            if os.path.isfile(mov_path) and os.path.getsize(mov_path) > 0:
                return {'type': 'apple', 'video_path': mov_path}

        # ── 2. Android Motion Photo: XMP 嵌入标记 ──
        if ext_lower in ('.jpg', '.jpeg'):
            try:
                img = Image.open(filepath)
                xmp_data = img.info.get('xmp') or img.info.get('XML:com.apple.markup')
                if not xmp_data:
                    # Pillow 可能未提取 XMP，回退到二进制搜索
                    xmp_data = self._extract_xmp_binary(filepath)
                if xmp_data:
                    is_motion = False
                    presentation_us = None
                    # bytes -> str（Pillow JPEG XMP 可能返回 bytes）
                    if isinstance(xmp_data, bytes):
                        xmp_data = xmp_data.decode('utf-8', errors='ignore')
                    # 解析 PresentationTimestampUs（照片时刻在视频中的位置）
                    m_ts = re.search(
                        r'GCamera:MotionPhotoPresentationTimestampUs=["\']?(\d+)',
                        xmp_data)
                    if m_ts:
                        presentation_us = int(m_ts.group(1))
                    try:
                        root = ET.fromstring(xmp_data)
                        for elem in root.iter():
                            # 同时检查 tag 和 attrib（小米等设备将 MotionPhoto=1 放在 rdf:Description 属性中）
                            if 'MotionPhoto' in elem.tag or 'MotionPhoto' in ' '.join(elem.attrib):
                                val = elem.text
                                if val is None or not val.strip():
                                    val = elem.attrib.get(
                                        '{http://ns.google.com/photos/1.0/camera/}MotionPhoto')
                                if val and val.strip() == '1':
                                    is_motion = True
                                    break
                            if 'MicroVideo' in elem.tag or 'MicroVideo' in ' '.join(elem.attrib):
                                val = elem.text
                                if val is None or not val.strip():
                                    val = elem.attrib.get(
                                        '{http://ns.google.com/photos/1.0/camera/}MicroVideo')
                                if val and val.strip() == '1':
                                    is_motion = True
                                    break
                    except ET.ParseError:
                        pass
                    # 字符串搜索兜底（无论 ET 是否成功）
                    if not is_motion:
                        if 'MotionPhoto="1"' in xmp_data or 'MotionPhoto=1' in xmp_data \
                           or 'MicroVideo="1"' in xmp_data or 'MicroVideo=1' in xmp_data:
                            is_motion = True
                    if is_motion:
                        return {'type': 'android', 'embedded': True,
                                'presentation_us': presentation_us}
            except Exception:
                pass

        # ── 3. vivo 独立配对: 同名 .mp4 ──
        for mp4_ext in ('.mp4', '.MP4'):
            mp4_path = base + mp4_ext
            if os.path.isfile(mp4_path) and os.path.getsize(mp4_path) > 0:
                return {'type': 'vivo', 'video_path': mp4_path}

        return None

    def _extract_xmp_binary(self, filepath):
        """从 JPEG 二进制中提取 XMP packet（Pillow 未能提取时的回退方案）"""
        try:
            with open(filepath, 'rb') as f:
                data = f.read(65536)  # XMP 通常在文件头部 64KB 内
            # 搜索 XMP packet 起止标记
            start = data.find(b'<x:xmpmeta')
            if start == -1:
                start = data.find(b'<xmp:xmpmeta')
            if start == -1:
                start = data.find(b'<rdf:RDF')
            if start == -1:
                return None
            end = data.find(b'</x:xmpmeta>', start)
            if end == -1:
                end = data.find(b'</xmp:xmpmeta>', start)
            if end == -1:
                end = data.find(b'</rdf:RDF>', start)
            if end == -1:
                return None
            end += len(b'</rdf:RDF>') if b'</rdf:RDF>' in data[start:] else \
                  len(b'</x:xmpmeta>') if b'</x:xmpmeta>' in data[start:] else \
                  len(b'</xmp:xmpmeta>')
            return data[start:end].decode('utf-8', errors='ignore')
        except Exception:
            return None

    # ── 动图嵌入视频提取 ──────────────────────────────────────
    def _extract_embedded_video(self, filepath):
        """从 Android Motion Photo 的 JPEG 文件中提取嵌入的视频，返回临时文件路径"""
        try:
            file_size = os.path.getsize(filepath)

            # ── 方案1：从 XMP Container Directory 解析 Item:Length ──
            xmp = self._extract_xmp_binary(filepath)
            if xmp:
                # 搜索 MotionPhoto 条目的 Length（属性顺序可能不同）
                m = re.search(
                    r'Item:Semantic="MotionPhoto"[^>]*?Item:Length="(\d+)"', xmp)
                if not m:
                    m = re.search(
                        r'Item:Length="(\d+)"[^>]*?Item:Semantic="MotionPhoto"', xmp)
                if m:
                    length = int(m.group(1))
                    video_start = file_size - length
                    if video_start > 0 and video_start < file_size:
                        with open(filepath, 'rb') as f:
                            f.seek(video_start)
                            video_data = f.read()
                        if b'ftyp' in video_data[:32]:
                            tmp = tempfile.NamedTemporaryFile(
                                suffix='.mp4', delete=False)
                            tmp.write(video_data)
                            tmp.close()
                            return tmp.name

            # ── 方案2（回退）：rfind(FFD9) + Samsung footer ──
            with open(filepath, 'rb') as f:
                data = f.read()

            eof_pos = data.rfind(b'\xff\xd9')
            if eof_pos == -1:
                return None
            video_start = eof_pos + 2
            if video_start >= len(data):
                return None
            video_data = data[video_start:]

            samsung_footer = b'MotionPhoto_Data\x00'
            samsung_pos = video_data.find(samsung_footer)
            if samsung_pos > 0:
                video_data = video_data[:samsung_pos]

            if b'ftyp' not in video_data[:32]:
                return None

            tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            tmp.write(video_data)
            tmp.close()
            return tmp.name
        except Exception:
            return None

    # ── 动图自动播放 ──────────────────────────────────────────
    def _start_motion_playback(self, video_path, seek_us=None, keep_livp=False):
        """开始播放动图视频（循环），seek_us 为起始微秒偏移
        keep_livp=True 时不销毁 .livp 悬停状态（Leave 事件保持绑定，离开可恢复静态图）"""
        if not HAS_CV2:
            self._flash_status("⚠️ 需要安装 opencv-python 才能播放动图", duration=3000)
            return
        if keep_livp:
            # ── 仅清理动图播放状态，保留 .livp 悬停绑定 ──
            self._motion_playing = False
            if self._motion_after_id is not None:
                self.root.after_cancel(self._motion_after_id)
                self._motion_after_id = None
            if self._motion_cap is not None:
                self._motion_cap.release()
                self._motion_cap = None
        else:
            self._stop_motion_playback()
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self._flash_status("⚠️ 无法打开动图视频", duration=3000)
                return
            # 从照片时刻开始播放（MotionPhotoPresentationTimestampUs）
            if seek_us and seek_us > 0:
                fps = cap.get(cv2.CAP_PROP_FPS) or 30
                seek_frame = int(seek_us / 1_000_000 * fps)
                if seek_frame > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, seek_frame)
            self._motion_cap = cap
            self._motion_playing = True
            self._motion_next_frame()
        except Exception:
            self._stop_motion_playback()

    def _motion_next_frame(self):
        """读取并显示下一帧视频"""
        if not self._motion_playing or not self._motion_cap:
            return
        try:
            ret, frame = self._motion_cap.read()
            if not ret:
                # 视频结束，回到开头循环
                self._motion_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._motion_cap.read()
                if not ret:
                    self._stop_motion_playback()
                    return

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)

            frame_w = self.img_frame.winfo_width() - 10
            frame_h = self.img_frame.winfo_height() - 10
            if frame_w < 50 or frame_h < 50:
                self._motion_after_id = self.root.after(33, self._motion_next_frame)
                return

            # 保持比例适应窗口（使用 BILINEAR 加速）
            img_ratio = img.width / img.height
            frame_ratio = frame_w / frame_h
            if img.width <= frame_w and img.height <= frame_h:
                ph = ImageTk.PhotoImage(img)
            elif img_ratio > frame_ratio:
                new_w = frame_w
                new_h = int(frame_w / img_ratio)
                resized = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                ph = ImageTk.PhotoImage(resized)
            else:
                new_h = frame_h
                new_w = int(frame_h * img_ratio)
                resized = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                ph = ImageTk.PhotoImage(resized)

            self.img_label.config(image=ph, text="")
            self.img_label.image = ph
        except Exception:
            self._stop_motion_playback()
            return

        self._motion_after_id = self.root.after(33, self._motion_next_frame)

    def _stop_motion_playback(self):
        """停止动图播放，释放资源"""
        # 取消 .livp 悬停延迟定时器
        if self._livp_hover_after is not None:
            self.root.after_cancel(self._livp_hover_after)
            self._livp_hover_after = None
        # 解绑悬停事件（切换文件时清除）
        self._unbind_livp_hover()
        # 清空 .livp 静态图缓存
        self._livp_static_img = None
        self._livp_video_path = None

        self._motion_playing = False
        if self._motion_after_id is not None:
            self.root.after_cancel(self._motion_after_id)
            self._motion_after_id = None
        if self._motion_cap is not None:
            self._motion_cap.release()
            self._motion_cap = None
        # 清理临时提取的视频文件
        if self._motion_temp_file is not None:
            try:
                os.remove(self._motion_temp_file)
            except Exception:
                pass
            self._motion_temp_file = None

    def _bind_livp_hover(self):
        """为预览区绑定 .livp 悬停事件"""
        self.img_label.bind('<Enter>', self._livp_hover_enter)
        self.img_label.bind('<Leave>', self._livp_hover_leave)

    def _unbind_livp_hover(self):
        """解绑 .livp 悬停事件"""
        try:
            self.img_label.unbind('<Enter>')
            self.img_label.unbind('<Leave>')
        except Exception:
            pass

    def _livp_hover_enter(self, event=None):
        """鼠标进入预览区：0.2s 后开始播放 .livp 视频"""
        if self._livp_hover_after is not None:
            self.root.after_cancel(self._livp_hover_after)
        if self._livp_video_path and HAS_CV2:
            self._livp_hover_after = self.root.after(200, self._livp_start_play)

    def _livp_hover_leave(self, event=None):
        """鼠标离开预览区：取消定时，停止播放，恢复静态图"""
        if self._livp_hover_after is not None:
            self.root.after_cancel(self._livp_hover_after)
            self._livp_hover_after = None
        # 停止视频播放（不清理临时文件，因为文件还要用）
        self._motion_playing = False
        if self._motion_after_id is not None:
            self.root.after_cancel(self._motion_after_id)
            self._motion_after_id = None
        if self._motion_cap is not None:
            self._motion_cap.release()
            self._motion_cap = None
        # 恢复静态图
        if self._livp_static_img is not None:
            self._display_image(self._livp_static_img)

    def _livp_start_play(self):
        """悬停 0.2s 后触发：开始播放 .livp 内嵌视频（保持 livp 悬停状态）"""
        self._livp_hover_after = None
        if self._livp_video_path and HAS_CV2:
            self._start_motion_playback(self._livp_video_path, seek_us=None, keep_livp=True)

    def _add_paired_action(self, src_image, dest_folder, action):
        """联动移动/复制配对文件（Live Photo .mov / vivo .mp4）到 pending_actions"""
        motion = self._detect_motion_photo(src_image)
        if not motion or not motion.get('video_path'):
            return
        paired_src = motion['video_path']
        # ── 检查是否已存在对同一源文件的操作 ──
        if any(a.get('src') == paired_src for a in self.pending_actions):
            return  # 已有操作，跳过
        paired_name = os.path.basename(paired_src)
        paired_dst = os.path.join(dest_folder, paired_name)
        # 处理目标重名
        base_p, ext_p = os.path.splitext(paired_name)
        c = 1
        while os.path.exists(paired_dst):
            paired_dst = os.path.join(dest_folder, f"{base_p}_{c}{ext_p}")
            c += 1
        self.pending_actions.append({
            'action': action, 'src': paired_src, 'dst': paired_dst, 'idx': None
        })

    def _add_paired_delete(self, src_image):
        """联动删除配对文件（Live Photo .mov / vivo .mp4）到 pending_actions"""
        motion = self._detect_motion_photo(src_image)
        if not motion or not motion.get('video_path'):
            return
        paired_src = motion['video_path']
        # ── 检查是否已存在对同一源文件的操作 ──
        if any(a.get('src') == paired_src for a in self.pending_actions):
            return  # 已有操作，跳过
        self.pending_actions.append({
            'action': 'delete', 'src': paired_src, 'dst': None, 'idx': None
        })

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
                fg=COLOR_TEXT)
            self._progress_var.set(pct)
            self._progress_label.config(
                text=f"{pct:.0f}%  ({done}/{total_session})")
        else:
            self.status.config(text="", fg=COLOR_TEXT)
            self._progress_var.set(0)
            self._progress_label.config(text="")

        # 刷新应用按钮状态
        n = len(self.pending_actions)
        if n > 0:
            self._apply_btn.config(
                text=f"应用 ({n})",
                state=NORMAL,
                bg=COLOR_SUCCESS, fg='white'
            )
        else:
            self._apply_btn.config(
                text="已应用",
                state=DISABLED,
                bg='#e5e7eb', fg='#9ca3af'
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
        self._stop_motion_playback()
        if self.pending_actions:
            count = len(self.pending_actions)
            classify_n = sum(1 for a in self.pending_actions if a['action'] != 'delete')
            delete_n = sum(1 for a in self.pending_actions if a['action'] == 'delete')

            # 自定义弹窗：应用 / 放弃 / 取消
            result = {'choice': None}

            dlg = Toplevel(self.root)
            dlg.title("未应用的操作")
            dlg.resizable(False, False)
            dlg.configure(bg=COLOR_CARD)
            dlg.grab_set()
            dlg.transient(self.root)

            # 居中显示
            dlg.update_idletasks()
            dw, dh = 380, 160
            x = self.root.winfo_x() + (self.root.winfo_width() - dw) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - dh) // 2
            dlg.geometry(f"{dw}x{dh}+{x}+{y}")

            Label(dlg, text=f"还有 {count} 项未应用的操作",
                  font=('', 11, 'bold'), bg=COLOR_CARD,
                  fg=COLOR_TEXT).pack(pady=(18, 4))
            Label(dlg, text=f"{classify_n} 项分类  ·  {delete_n} 项删除",
                  fg=COLOR_TEXT_SEC, bg=COLOR_CARD).pack()

            btn_frame = Frame(dlg, bg=COLOR_CARD)
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

            btn_apply = Button(btn_frame, text="应用我的分类", command=on_apply,
                   bg=COLOR_SUCCESS, fg='white', font=('', 10, 'bold'),
                   padx=12, pady=4, bd=0, cursor='hand2')
            btn_apply.pack(side=LEFT, padx=6)
            _bind_hover(btn_apply, COLOR_SUCCESS, '#059669')
            btn_discard = Button(btn_frame, text="放弃分类", command=on_discard,
                   bg=COLOR_DANGER, fg='white', font=('', 10),
                   padx=12, pady=4, bd=0, cursor='hand2')
            btn_discard.pack(side=LEFT, padx=6)
            _bind_hover(btn_discard, COLOR_DANGER, '#dc2626')
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
        # ── 联动删除配对文件（Live Photo .mov / vivo .mp4）──
        self._add_paired_delete(src)
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
        rotation = self._current_rotation if self._current_rotation % 360 != 0 else 0
        self.pending_actions.append({
            'action': action, 'src': src, 'dst': dst, 'idx': self.ptr,
            'rotation': rotation
        })
        # ── 联动移动配对文件（Live Photo .mov / vivo .mp4）──
        self._add_paired_action(src, fo, action)
        # ── 旋转模式时：如果是复制则直接覆盖目标为旋转后版本 ──
        #    如果是移动则覆盖源文件为旋转后版本（因为移动就是搬走）
        #    实际保存延迟到 _do_apply 执行时
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
            if not os.path.exists(act['src']):
                failed += 1
                errors.append(f"{os.path.basename(act['src'])}：文件不存在或已被删除")
                continue
            try:
                rotation = act.get('rotation', 0)
                if rotation and rotation % 360 != 0 and act.get('dst'):
                    # 有旋转：先执行复制/移动，再覆盖目标为旋转后版本
                    save_target = act['dst']
                    if act['action'] == 'copy':
                        shutil.copy2(act['src'], save_target)
                    elif act['action'] == 'move':
                        shutil.move(act['src'], save_target)
                    # 保存旋转后的图片
                    self._save_rotated_image(save_target, rotation)
                elif act['action'] == 'copy':
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

    def _save_rotated_image(self, filepath, rotation):
        """打开图片，旋转后覆盖保存（保持原格式和 EXIF）"""
        try:
            img = Image.open(filepath)
            rotated = img.rotate(rotation, Image.Resampling.BICUBIC, expand=True)
            # 保持原格式保存
            save_kwargs = {}
            if 'exif' in img.info:
                save_kwargs['exif'] = img.info['exif']
            if filepath.lower().endswith('.png'):
                rotated.save(filepath, format='PNG')
            elif filepath.lower().endswith(('.jpg', '.jpeg')):
                rotated.save(filepath, format='JPEG', quality=95, **save_kwargs)
            elif filepath.lower().endswith('.heic'):
                # Pillow 默认不支持 HEIC 写入，回退到 JPEG
                jpg_path = os.path.splitext(filepath)[0] + '.jpg'
                rotated.save(jpg_path, format='JPEG', quality=95, **save_kwargs)
            else:
                # 其他格式尝试直接保存
                rotated.save(filepath, **save_kwargs)
        except Exception:
            pass  # 旋转保存失败不影响主操作

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
            # ── 查重设置 ──
            'dedup_enabled': self.dedup_enabled.get(),
            'dedup_mode':    self.dedup_mode.get(),
            # ── 进度断点 ──
            'last_ptr':       self.ptr,
            'last_anchor':    anchor,
            # ── 窗口几何信息 ──
            'window_geometry': self.root.geometry(),
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
                # ── 恢复查重设置 ──
                self.dedup_enabled.set(cfg.get('dedup_enabled', False))
                self.dedup_mode.set(cfg.get('dedup_mode', 'skip'))
                # ── 恢复进度断点 ──
                self._saved_ptr    = cfg.get('last_ptr', 0)
                self._saved_anchor = cfg.get('last_anchor', None)
                # ── 恢复窗口几何信息 ──
                self._saved_geometry = cfg.get('window_geometry', '')
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

    def _global_create_subfolder(self):
        """选择已有文件夹作为分类仓库，默认打开输入路径的父目录"""
        input_path = self.input_folder.get()
        initial_dir = os.path.dirname(input_path) if input_path and os.path.isdir(input_path) else ""

        new_path = filedialog.askdirectory(
            parent=self.root,
            title="选择分类文件夹",
            initialdir=initial_dir if initial_dir else None
        )
        if not new_path:
            return

        n = self.folder_count_var.get()

        # 找第一个空槽位
        target_idx = None
        for i in range(n):
            if not self.output_folders[i]["path"].get().strip():
                target_idx = i
                break

        # 所有槽位都有路径，自动增加一个
        if target_idx is None:
            target_idx = n
            self.folder_count_var.set(n + 1)
            self._on_folder_count_change()

        self.output_folders[target_idx]["path"].set(new_path)
        if target_idx < len(self.out_entries):
            self.out_entries[target_idx].set(new_path)
        self.save_config()
        self.update_display()

    def remove_folder(self, idx):
        """删除指定分类槽位（后续槽位前移，不删除磁盘文件）"""
        n = self.folder_count_var.get()
        if n <= 2:
            return  # 最少保留 2 个

        # 后续槽位路径依次前移
        for i in range(idx, n - 1):
            self.output_folders[i]["path"].set(
                self.output_folders[i + 1]["path"].get()
            )
        # 清空最后一个槽位
        self.output_folders[n - 1]["path"].set("")

        # 减少数量并刷新 UI
        self.folder_count_var.set(n - 1)
        self._on_folder_count_change()

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
