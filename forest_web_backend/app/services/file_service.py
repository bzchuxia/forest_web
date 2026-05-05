import os
import tempfile
import shutil
from fastapi import HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from starlette.responses import Response
from io import BytesIO
from app.core.config import settings
from urllib.parse import unquote

# ===================== HDFS 客户端配置 =====================
try:
    from hdfs import InsecureClient
    
    # Hadoop 集群配置（可根据实际环境调整）
    HDFS_URL = "http://localhost:9870"
    HDFS_USER = "hadoop"
    HDFS_ROOT = "/forest"
    
    # 初始化 HDFS 客户端
    hdfs_client = InsecureClient(HDFS_URL, user=HDFS_USER)
    HDFS_ENABLED = True
    print(f"✅ HDFS 客户端已初始化：{HDFS_URL}")
except ImportError:
    hdfs_client = None
    HDFS_ENABLED = False
    print("⚠️ HDFS 客户端未安装（pip install hdfs），仅支持本地文件操作")
except Exception as e:
    hdfs_client = None
    HDFS_ENABLED = False
    print(f"⚠️ HDFS 连接失败：{str(e)}，仅支持本地文件操作")

# ===================== 核心路径配置（本地模式根目录） =====================
# 本地biomass_results目录：项目根目录/data/biomass_results
LOCAL_BIOMASS_RESULTS_DIR = os.path.join(settings.BASE_DATA_DIR, "biomass_results")
os.makedirs(LOCAL_BIOMASS_RESULTS_DIR, exist_ok=True)
print(f"✅ 本地biomass_results目录：{LOCAL_BIOMASS_RESULTS_DIR}")

# ===================== HDFS 工具函数 =====================
def is_hdfs_path(file_path: str) -> bool:
    """判断是否为 HDFS 路径"""
    return file_path.startswith("/") and HDFS_ENABLED and hdfs_client and hdfs_client.status(file_path, strict=False)

def download_hdfs_file(hdfs_path: str, local_dir: str = None) -> str:
    """
    从 HDFS 下载文件到本地临时目录
    :param hdfs_path: HDFS 文件路径
    :param local_dir: 本地目录（None 则使用临时目录）
    :return: 本地文件路径
    """
    if not HDFS_ENABLED or not hdfs_client:
        raise HTTPException(status_code=500, detail="HDFS 客户端未启用")
    
    # 创建临时目录
    if local_dir is None:
        local_dir = tempfile.mkdtemp(prefix="hdfs_temp_")
    
    # 确保目录存在
    os.makedirs(local_dir, exist_ok=True)
    
    # 下载文件
    local_file_path = os.path.join(local_dir, os.path.basename(hdfs_path))
    try:
        hdfs_client.download(hdfs_path, local_file_path, overwrite=True)
        print(f"✅ 从 HDFS 下载文件：{hdfs_path} -> {local_file_path}")
        return local_file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HDFS 文件下载失败：{str(e)}")

def read_hdfs_file_to_bytes(hdfs_path: str) -> bytes:
    """读取 HDFS 文件内容为字节流"""
    if not HDFS_ENABLED or not hdfs_client:
        raise HTTPException(status_code=500, detail="HDFS 客户端未启用")
    
    try:
        with hdfs_client.read(hdfs_path) as reader:
            return reader.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取 HDFS 文件失败：{str(e)}")

# ===================== 核心文件路径处理（适配biomass_results） =====================
def get_biomass_results_file_path(filename: str) -> str:
    """
    专门处理biomass_results目录下的文件路径（本地模式优先）
    :param filename: 文件名（如 xxx.png）
    :return: 本地文件绝对路径
    """
    # 1. 本地模式：直接拼接biomass_results目录
    local_file_path = os.path.join(LOCAL_BIOMASS_RESULTS_DIR, filename)
    local_file_path = os.path.normpath(local_file_path)  # 规范化路径
    
    # 2. 存在性校验
    if not os.path.exists(local_file_path):
        raise HTTPException(
            status_code=404,
            detail=f"本地biomass_results文件不存在：{filename}\n实际查找路径：{local_file_path}"
        )
    
    # 3. 越权校验（确保在允许的目录内）
    if not local_file_path.startswith(settings.BASE_DATA_DIR):
        raise HTTPException(
            status_code=403,
            detail=f"无权访问该文件：{filename}\n允许访问的目录：{settings.BASE_DATA_DIR}"
        )
    
    return local_file_path

def get_file_path(file_path: str) -> str:
    """
    通用文件路径处理（保留原有逻辑，兼容其他目录）
    :param file_path: 输入路径（本地路径/HDFS 路径/相对路径）
    :return: 本地文件绝对路径
    """
    # 1. 处理 HDFS 路径
    if is_hdfs_path(file_path):
        # 下载 HDFS 文件到临时目录
        return download_hdfs_file(file_path)
    
    # 2. 处理本地路径
    abs_path = os.path.abspath(os.path.join(settings.BASE_DATA_DIR, file_path))
    abs_path = os.path.normpath(abs_path)
    
    # 3. 越权校验
    allowed_dir = os.path.abspath(settings.BASE_DATA_DIR)
    if not abs_path.startswith(allowed_dir):
        raise HTTPException(
            status_code=403,
            detail=f"无权访问该文件：{file_path}\n允许访问的目录：{allowed_dir}"
        )
    
    # 4. 存在性校验
    if not os.path.exists(abs_path):
        raise HTTPException(
            status_code=404,
            detail=f"文件不存在：{file_path}\n实际查找路径：{abs_path}"
        )
    
    return abs_path

# ===================== 文件下载功能（支持 HDFS） =====================
def get_file_download_response(file_path: str):
    """
    获取文件下载响应（适配前端下载功能，支持 HDFS 文件）
    """
    try:
        # 处理 HDFS 文件
        if is_hdfs_path(file_path):
            filename = os.path.basename(file_path)
            
            # 读取 HDFS 文件内容
            file_content = read_hdfs_file_to_bytes(file_path)
            file_bytes = BytesIO(file_content)
            
            # 构建响应
            from urllib.parse import quote
            encoded_filename = quote(filename, safe='')
            headers = {
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "X-HDFS-Source": file_path
            }
            
            return StreamingResponse(
                content=file_bytes,
                media_type="application/octet-stream",
                headers=headers
            )
        
        # 处理本地文件
        abs_path = get_file_path(file_path)
        filename = os.path.basename(abs_path)
        
        # 对文件名进行 URL 编码，以兼容不同浏览器
        from urllib.parse import quote
        encoded_filename = quote(filename, safe='')
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
        
        return FileResponse(
            path=abs_path,
            headers=headers,
            media_type="application/octet-stream"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

# ===================== 图片预览功能（专门适配biomass_results） =====================
def get_biomass_results_image_response(filename: str):
    """
    专门处理biomass_results目录下的图片预览（本地模式）
    :param filename: 图片文件名（如 xxx.png）
    :return: StreamingResponse
    """
    # 1. 获取精准的本地文件路径
    local_file_path = get_biomass_results_file_path(filename)
    
    # 2. 校验图片格式
    image_extensions = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".bmp"]
    if not any(local_file_path.lower().endswith(ext) for ext in image_extensions):
        raise HTTPException(status_code=400, detail=f"该文件不是图片：{filename}")
    
    # 3. 读取图片并返回流响应
    try:
        with open(local_file_path, "rb") as f:
            image_bytes = BytesIO(f.read())
        
        # 确定媒体类型
        ext = os.path.splitext(local_file_path)[1].lower()
        media_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".tif": "image/tiff",
            ".tiff": "image/tiff",
            ".gif": "image/gif",
            ".bmp": "image/bmp"
        }
        media_type = media_type_map.get(ext, "image/png")
        
        return StreamingResponse(
            content=image_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{unquote(filename)}",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取biomass_results图片失败：{str(e)}")

def get_image_preview_response(file_path: str):
    """
    通用图片预览（保留原有逻辑）
    """
    # 定义支持的图片格式
    image_extensions = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".bmp"]
    
    try:
        # 处理 HDFS 图片文件
        if is_hdfs_path(file_path):
            # 校验文件扩展名
            if not any(file_path.lower().endswith(ext) for ext in image_extensions):
                raise HTTPException(status_code=400, detail=f"HDFS 文件不是图片：{file_path}")
            
            # 读取 HDFS 图片内容
            image_content = read_hdfs_file_to_bytes(file_path)
            image_bytes = BytesIO(image_content)
            
            # 确定媒体类型
            ext = os.path.splitext(file_path)[1].lower()
            media_type_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".tif": "image/tiff",
                ".tiff": "image/tiff",
                ".gif": "image/gif",
                ".bmp": "image/bmp"
            }
            media_type = media_type_map.get(ext, "image/png")
            
            return StreamingResponse(
                content=image_bytes,
                media_type=media_type,
                headers={"X-HDFS-Source": file_path}
            )
        
        # 处理本地图片文件
        abs_path = get_file_path(file_path)
        
        # 校验是否为图片文件
        if not any(abs_path.lower().endswith(ext) for ext in image_extensions):
            raise HTTPException(status_code=400, detail=f"该文件不是图片：{file_path}")
        
        # 读取图片并返回流响应
        with open(abs_path, "rb") as f:
            image_bytes = BytesIO(f.read())
        
        return StreamingResponse(
            content=image_bytes,
            media_type="image/png"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取图片失败：{str(e)}")

# ===================== 辅助函数：清理临时文件 =====================
def cleanup_temp_files(temp_dir_pattern: str = "hdfs_temp_"):
    """
    清理 HDFS 临时下载文件
    :param temp_dir_pattern: 临时目录前缀
    """
    try:
        import glob
        import shutil
        
        # 查找所有临时目录
        temp_dirs = glob.glob(os.path.join(tempfile.gettempdir(), f"{temp_dir_pattern}*"))
        
        for temp_dir in temp_dirs:
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"🗑️ 清理临时目录：{temp_dir}")
        
        return {"status": "success", "message": f"清理了 {len(temp_dirs)} 个临时目录"}
    except Exception as e:
        print(f"⚠️ 清理临时文件失败：{str(e)}")
        return {"status": "failed", "error": str(e)}