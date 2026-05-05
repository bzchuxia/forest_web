# app/ml/fs_layer.py
import os
import shutil
import tempfile
import logging
import io
from abc import ABC, abstractmethod
from typing import Optional, BinaryIO

# 修复导入：hdfs 库的具体异常位置可能不同，建议捕获通用异常或具体检查
# 通常 hdfs.client.HdfsError 是存在的，但为了稳健，我们捕获 Exception 并在内部判断
try:
    from hdfs import InsecureClient
    # 尝试导入具体异常，如果失败则使用通用 Exception 代替
    try:
        from hdfs.client import HdfsError
    except ImportError:
        HdfsError = Exception 
except ImportError:
    # 如果连 hdfs 库都没安装，定义一个占位符，防止导入报错
    InsecureClient = None
    HdfsError = Exception

logger = logging.getLogger("biomass_prediction")

# ===================== 抽象基类 =====================
class FileSystem(ABC):
    """文件系统抽象基类"""
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        pass
    
    @abstractmethod
    def download(self, remote_path: str, local_path: str) -> str:
        """将远程/逻辑路径文件下载到本地临时路径，返回本地绝对路径"""
        pass
    
    @abstractmethod
    def upload(self, local_path: str, remote_path: str) -> bool:
        """将本地文件上传到远程/逻辑路径"""
        pass
    
    @abstractmethod
    def read_bytes(self, path: str) -> bytes:
        """直接读取文件内容字节流（用于joblib加载等）"""
        pass

# ===================== 本地实现 =====================
class LocalFileSystem(FileSystem):
    """本地文件系统实现"""
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        logger.info("✅ 文件系统模式：LOCAL (仅使用本地磁盘)")

    def _resolve(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        # 处理虚拟路径 /data/...
        if path.startswith("/data/"):
            return os.path.join(self.base_dir, path.replace("/data/", "", 1))
        # 处理相对路径
        return os.path.join(self.base_dir, path)

    def exists(self, path: str) -> bool:
        return os.path.exists(self._resolve(path))

    def download(self, remote_path: str, local_path: str) -> str:
        src = self._resolve(remote_path)
        if not os.path.exists(src):
            raise FileNotFoundError(f"本地文件不存在：{src}")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(src, local_path)
        return local_path

    def upload(self, local_path: str, remote_path: str) -> bool:
        dest = self._resolve(remote_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(local_path, dest)
        logger.info(f"本地保存成功：{dest}")
        return True

    def read_bytes(self, path: str) -> bytes:
        full_path = self._resolve(path)
        with open(full_path, 'rb') as f:
            return f.read()

# ===================== HDFS 实现 =====================
class HDFSFileSystem(FileSystem):
    """HDFS 文件系统实现 (带本地缓存机制)"""
    def __init__(self, hdfs_url: str, user: str, root: str):
        if InsecureClient is None:
            raise ImportError("hdfs 库未安装")
            
        self.client = InsecureClient(hdfs_url, user=user)
        self.root = root
        # 注意：这里不再测试连接！测试连接放在工厂模式中。
        # 如果在这里测试连接失败，会导致类实例化失败，无法进行后续的降级处理。
        logger.debug(f"HDFS 客户端已初始化 (未验证连接): {hdfs_url}")

    def _resolve(self, path: str) -> str:
        if path.startswith(self.root):
            return path
        if path.startswith("/data/"):
            # 映射逻辑：/data/xxx -> {root}/data/xxx
            return f"{self.root}/data/{path.replace('/data/', '', 1)}"
        # 默认映射到 root 下
        return f"{self.root}/{path.lstrip('/')}"

    def exists(self, path: str) -> bool:
        try:
            return self.client.status(self._resolve(path), strict=False) is not None
        except Exception:
            return False

    def download(self, remote_path: str, local_path: str) -> str:
        hdfs_path = self._resolve(remote_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        # hdfs 库的 download 方法
        self.client.download(hdfs_path, local_path, overwrite=True)
        return local_path

    def upload(self, local_path: str, remote_path: str) -> bool:
        hdfs_path = self._resolve(remote_path)
        try:
            self.client.upload(hdfs_path, local_path, overwrite=True)
            logger.info(f"HDFS 上传成功：{hdfs_path}")
            return True
        except Exception as e:
            logger.warning(f"HDFS 上传失败：{e}")
            return False

    def read_bytes(self, path: str) -> bytes:
        hdfs_path = self._resolve(path)
        # hdfs 库的 read 返回的是一个类似文件的对象
        with self.client.read(hdfs_path) as reader:
            return reader.read()

# ===================== 智能工厂 (核心降级逻辑) =====================
class FileSystemFactory:
    _instance: Optional[FileSystem] = None
    _mode: str = "unknown"

    @classmethod
    def get_instance(cls, config: any) -> FileSystem:
        """
        单例模式获取文件系统实例。
        策略：优先尝试 HDFS，失败则自动降级为 Local。
        """
        if cls._instance:
            return cls._instance
        
        # 1. 尝试初始化 HDFS
        try:
            logger.info(f"正在尝试连接 HDFS: {config.HDFS_URL} ...")
            
            # 实例化客户端 (此时不抛异常)
            client = InsecureClient(config.HDFS_URL, user=config.HDFS_USER)
            
            # 【关键】主动测试连接 (ping)
            # 如果 HDFS 没启动，这里会抛出 HdfsError 或 ConnectionError
            client.status("/", strict=False) 
            
            # 连接成功，创建 HDFS 实例
            cls._instance = HDFSFileSystem(
                hdfs_url=config.HDFS_URL,
                user=config.HDFS_USER,
                root=config.HDFS_ROOT
            )
            cls._mode = "HDFS"
            logger.info(f"✅ 文件系统模式：HDFS ({config.HDFS_URL})")
            return cls._instance
            
        except Exception as e:
            # 2. 捕获任何异常 (连接拒绝、超时、库缺失等)
            logger.warning(f"⚠️ HDFS 连接失败 ({type(e).__name__}: {str(e)})")
            logger.warning("   系统已自动降级为 [本地模式]。所有文件操作将在本地磁盘进行。")
            
        # 3. 降级为本地模式
        cls._instance = LocalFileSystem(base_dir=config.BASE_DATA_DIR)
        cls._mode = "LOCAL"
        return cls._instance

    @classmethod
    def get_mode(cls) -> str:
        return cls._mode

# ===================== 全局便捷函数 =====================
def get_fs(config: any = None) -> FileSystem:
    """
    获取文件系统实例。
    如果是第一次调用，需要传入 config 进行初始化。
    """
    if FileSystemFactory._instance is None:
        if config is None:
            # 如果没有 config 且未初始化，尝试从 app.config 导入
            try:
                from app.core.config import settings
                config = settings
            except ImportError:
                raise RuntimeError("未初始化文件系统且无法自动加载配置。请在首次调用时传入 config 参数。")
        
        return FileSystemFactory.get_instance(config)
    
    return FileSystemFactory._instance