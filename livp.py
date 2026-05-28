"""
livp — iPhone 实况照片 (Live Photo) 解析模块

LIVP 是 ZIP 压缩包，内含一张图片 (HEIC/JPEG) 和一段视频 (MOV)。

用法:
    from livp import LivpFile, LivpDir

    # 单个文件
    photo = LivpFile("IMG_0001.livp")
    photo.image_bytes()          # -> bytes (HEIC/JPEG 原始数据)
    photo.image_bytes(fmt="jpg") # -> bytes (转为 JPEG)
    photo.video_bytes()          # -> bytes (MOV 数据)
    photo.save_image("out.jpg")  # 保存图片
    photo.save_video("out.mov")  # 保存视频
    photo.info()                 # -> {"image_name": ..., "video_name": ..., ...}

    # 扫描目录
    collection = LivpDir("/path/to/livps")
    for photo in collection:
        photo.save_image(f"output/{photo.stem}.jpg")
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Iterator

from PIL import Image

# 注册 HEIC 解码器（幂等）
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


IMAGE_EXTS = (".heic", ".jpeg", ".jpg")
VIDEO_EXTS = (".mov",)


class LivpFile:
    """单个 LIVP 实况照片文件。"""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            FileNotFoundError(self.path)
        self._names: list[str] | None = None

    def __repr__(self) -> str:
        return f"LivpFile({self.path.name})"

    @property
    def stem(self) -> str:
        """文件名（不含 .livp 后缀）。"""
        return self.path.stem

    # ── ZIP 内部文件列表 ──────────────────────────────────

    def _namelist(self) -> list[str]:
        if self._names is None:
            with zipfile.ZipFile(self.path) as z:
                self._names = z.namelist()
        return self._names

    def _find(self, extensions: tuple[str, ...]) -> str | None:
        for name in self._namelist():
            if any(name.lower().endswith(ext) for ext in extensions):
                return name
        return None

    def _read(self, inner_name: str) -> bytes:
        with zipfile.ZipFile(self.path) as z:
            return z.read(inner_name)

    # ── 提取原始数据 ──────────────────────────────────────

    @property
    def image_name(self) -> str | None:
        """ZIP 内图片文件名。"""
        return self._find(IMAGE_EXTS)

    @property
    def video_name(self) -> str | None:
        """ZIP 内视频文件名。"""
        return self._find(VIDEO_EXTS)

    @property
    def image_format(self) -> str | None:
        """图片格式: 'heic' | 'jpeg' | None。"""
        name = self.image_name
        if name is None:
            return None
        lower = name.lower()
        if lower.endswith(".heic"):
            return "heic"
        return "jpeg"

    def image_bytes(self, fmt: str | None = None) -> bytes:
        """获取图片数据。

        Args:
            fmt: 输出格式。None=原始格式, "jpg"/"jpeg"=转为 JPEG, "png"=转为 PNG。
        """
        name = self.image_name
        if name is None:
            raise FileNotFoundError(f"{self.path} 中未找到图片文件")
        raw = self._read(name)

        if fmt is None or fmt.lower() == self.image_format:
            return raw

        img = Image.open(io.BytesIO(raw))
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        save_fmt = "JPEG" if fmt.lower() in ("jpg", "jpeg") else fmt.upper()
        quality = 92 if save_fmt == "JPEG" else None
        kwargs = {"quality": quality} if quality else {}
        img.save(buf, save_fmt, **kwargs)
        return buf.getvalue()

    def image_pil(self) -> Image.Image:
        """获取 PIL Image 对象。"""
        raw = self.image_bytes()
        img = Image.open(io.BytesIO(raw))
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img

    def video_bytes(self) -> bytes:
        """获取视频 (MOV) 数据。"""
        name = self.video_name
        if name is None:
            raise FileNotFoundError(f"{self.path} 中未找到视频文件")
        return self._read(name)

    # ── 缩略图 ────────────────────────────────────────────

    def thumbnail_bytes(self, size: int = 300, quality: int = 85) -> bytes:
        """生成 JPEG 缩略图。

        Args:
            size: 缩略图最大边长。
            quality: JPEG 质量 (1-100)。
        """
        img = self.image_pil()
        img.thumbnail((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality)
        return buf.getvalue()

    # ── 保存到文件 ────────────────────────────────────────

    def save_image(self, dest: str | Path, fmt: str | None = None) -> Path:
        """保存图片到文件。返回目标路径。"""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if fmt is None:
            # 根据后缀推断
            ext = dest.suffix.lower()
            if ext in (".jpg", ".jpeg"):
                fmt = "jpg"
            elif ext == ".png":
                fmt = "png"
            elif ext == ".heic":
                fmt = None  # 保持原始
        data = self.image_bytes(fmt)
        dest.write_bytes(data)
        return dest

    def save_video(self, dest: str | Path) -> Path:
        """保存视频到文件。返回目标路径。"""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.video_bytes())
        return dest

    # ── 信息 ──────────────────────────────────────────────

    def info(self) -> dict:
        """返回 LIVP 文件信息。"""
        img = self.image_pil()
        return {
            "file": self.path.name,
            "image_name": self.image_name,
            "video_name": self.video_name,
            "image_format": self.image_format,
            "width": img.width,
            "height": img.height,
        }


class LivpDir:
    """目录下所有 LIVP 文件的集合。"""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self._files: list[LivpFile] | None = None

    def __repr__(self) -> str:
        return f"LivpDir({self.directory}, {len(self)} files)"

    def __len__(self) -> int:
        return len(self.files)

    def __iter__(self) -> Iterator[LivpFile]:
        return iter(self.files)

    def __getitem__(self, index: int) -> LivpFile:
        return self.files[index]

    @property
    def files(self) -> list[LivpFile]:
        if self._files is None:
            self._files = [
                LivpFile(p) for p in sorted(self.directory.glob("*.livp"))
            ]
        return self._files

    def extract_all(
        self,
        dest: str | Path,
        image_fmt: str = "jpg",
        overwrite: bool = False,
    ) -> list[Path]:
        """批量提取所有 LIVP 文件的图片和视频。

        Args:
            dest: 输出目录。
            image_fmt: 图片输出格式。
            overwrite: 是否覆盖已存在的文件。

        Returns:
            提取的文件路径列表。
        """
        dest = Path(dest)
        results = []
        for photo in self:
            ext = "jpg" if image_fmt in ("jpg", "jpeg") else image_fmt
            img_dest = dest / f"{photo.stem}.{ext}"
            vid_dest = dest / f"{photo.stem}.mov"
            if overwrite or not img_dest.exists():
                results.append(photo.save_image(img_dest, fmt=image_fmt))
            if overwrite or not vid_dest.exists():
                results.append(photo.save_video(vid_dest))
        return results
