"""
HaiScript 图片处理模块头文件
提供图片加载、创建、编辑、保存等能力。
"""
from typing import List, Optional, Tuple, Dict


formats: List[str]
"""支持的图片格式列表，如 ['PNG', 'JPEG', 'BMP', 'GIF', 'TIFF', 'WEBP']。"""


class Image:
    """图片对象，封装位图数据。"""

    width: int
    """图片宽度。"""

    height: int
    """图片高度。"""

    mode: str
    """图片模式，如 'RGB'、'RGBA'、'L'。"""

    format: Optional[str]
    """原始图片格式。"""


def load(path: str) -> Image:
    """从文件加载图片。"""
    ...


def create(width: int, height: int, color: Tuple[int, int, int] = (255, 255, 255)) -> Image:
    """创建指定大小的空白图片。"""
    ...


def info(path: str) -> Dict[str, Any]:
    """获取图片信息 (width, height, mode, format)。"""
    ...


def save(img: Image, path: str, fmt: Optional[str] = None) -> bool:
    """保存图片到文件。"""
    ...


def resize(img: Image, w: int, h: int) -> Image:
    """调整图片大小。"""
    ...


def thumbnail(img: Image, w: int, h: int) -> Image:
    """生成缩略图。"""
    ...


def rotate(img: Image, angle: float) -> Image:
    """旋转图片。"""
    ...


def crop(img: Image, x: int, y: int, w: int, h: int) -> Image:
    """裁剪图片区域。"""
    ...


def get_pixel(img: Image, x: int, y: int) -> List[int]:
    """获取指定像素颜色。"""
    ...


def set_pixel(img: Image, x: int, y: int, color: List[int]) -> None:
    """设置指定像素颜色。"""
    ...


def to_gray(img: Image) -> Image:
    """转换为灰度图。"""
    ...


def to_grayscale(img: Image) -> Image:
    """to_gray 的别名。"""
    ...
