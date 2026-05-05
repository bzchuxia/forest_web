from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
import os
import urllib.parse
from io import BytesIO
from app.services.file_service import (
    get_file_download_response, 
    get_image_preview_response,
    get_biomass_results_image_response, 
    get_biomass_results_file_path      
)

router = APIRouter(tags=["文件操作"])

# 本地目录配置
from app.core.config import settings
LOCAL_BIOMASS_RESULTS_DIR = os.path.join(settings.BASE_DATA_DIR, "biomass_results")
os.makedirs(LOCAL_BIOMASS_RESULTS_DIR, exist_ok=True)
OS_SEP = os.sep
# 安全路径校验（防止路径遍历攻击）
def safe_join(base_dir: str, *paths) -> str:
    """安全拼接路径，防止路径遍历攻击"""
    # 拼接路径
    joined_path = os.path.normpath(os.path.join(base_dir, *paths))
    # 校验路径是否在基础目录内
    if not joined_path.startswith(os.path.normpath(base_dir) + OS_SEP) and joined_path != os.path.normpath(base_dir):
        raise HTTPException(status_code=403, detail="非法路径：禁止访问基础目录外的文件")
    return joined_path

# ===================== 热力图文件接口（heatmap） =====================
@router.api_route("/heatmap/{filename:path}", methods=["GET", "HEAD"])
async def get_heatmap_file(filename: str):
    try:
        # 1. 解码文件名（处理URL编码）
        filename_decoded = urllib.parse.unquote(filename)
        filename_decoded = filename_decoded.replace("/", OS_SEP).replace("\\", OS_SEP)
        
        # 2. 安全拼接路径：映射到 BASE_DATA_DIR/heatmap/ 目录
        local_heatmap_dir = os.path.join(settings.BASE_DATA_DIR, "heatmap")
        os.makedirs(local_heatmap_dir, exist_ok=True)
        
        try:
            local_file_path = safe_join(local_heatmap_dir, filename_decoded)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"路径格式错误：{str(e)}")
        
        # 3. 检查文件是否存在
        if not os.path.exists(local_file_path):
            raise HTTPException(status_code=404, detail=f"热力图文件不存在：{local_file_path}")
        
        # 4. 检查文件读取权限
        if not os.access(local_file_path, os.R_OK):
            raise HTTPException(status_code=403, detail=f"无热力图文件读取权限：{local_file_path}")
        
        # 5. 媒体类型映射（支持 GeoJSON/TIF/PNG 等）
        ext = os.path.splitext(local_file_path)[1].lower()
        media_type_map = {
            ".geojson": "application/json",
            ".json": "application/json",
            ".tif": "image/tiff",
            ".tiff": "image/tiff",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg"
        }
        media_type = media_type_map.get(ext, "application/octet-stream")
        
        # 6. 返回文件响应
        disposition_type = "inline" if ext in [".geojson", ".json", ".png", ".jpg", ".jpeg"] else "attachment"
        return FileResponse(
            local_file_path,
            media_type=media_type,
            filename=filename_decoded,
            headers={
                "Content-Disposition": f"{disposition_type}; filename*=UTF-8''{urllib.parse.quote(filename_decoded)}",
                "Cache-Control": "no-cache"
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载热力图文件失败：{str(e)}")

# ===================== 通用data目录文件接口 =====================
@router.get("/data/{filename:path}")
async def get_data_file(filename: str):
    """
    访问后端data目录下的文件（如simple_heatmap.png）
    前端访问路径：/api/file/data/simple_heatmap.png
    后端映射路径：settings.BASE_DATA_DIR/simple_heatmap.png
    """
    try:
        # 1. 解码文件名（处理URL编码，兼容中文/特殊字符）
        filename_decoded = urllib.parse.unquote(filename)
        filename_decoded = filename_decoded.replace("/", OS_SEP).replace("\\", OS_SEP)
        
        # 2. 安全拼接路径：映射到BASE_DATA_DIR
        try:
            local_file_path = safe_join(settings.BASE_DATA_DIR, filename_decoded)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"路径格式错误：{str(e)}")
        
        # 3. 检查文件是否存在
        if not os.path.exists(local_file_path):
            raise HTTPException(status_code=404, detail=f"文件不存在：{local_file_path}")
        
        # 4. 检查文件读取权限
        if not os.access(local_file_path, os.R_OK):
            raise HTTPException(status_code=403, detail=f"无文件读取权限：{local_file_path}")
        
        # 5. 判断文件类型：图片返回预览，其他返回下载
        ext = os.path.splitext(local_file_path)[1].lower()
        image_extensions = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".bmp"]
        
        if ext in image_extensions:
            # 图片文件：返回预览（inline）
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
            
            # 读取图片并返回流响应
            with open(local_file_path, "rb") as f:
                image_bytes = BytesIO(f.read())
            
            return StreamingResponse(
                content=image_bytes,
                media_type=media_type,
                headers={
                    "Content-Disposition": f"inline; filename*=UTF-8''{urllib.parse.quote(filename_decoded)}",
                    "Cache-Control": "no-cache"
                }
            )
        else:
            # 非图片文件：返回下载
            media_type = "application/octet-stream"
            return FileResponse(
                local_file_path,
                media_type=media_type,
                filename=filename_decoded,
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename_decoded)}",
                    "Cache-Control": "no-cache"
                }
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载data目录文件失败：{str(e)}")

# ===================== 预测文件接口（biomass_results）=====================
@router.api_route("/biomass_results/{filename:path}", methods=["GET", "HEAD"])
async def get_prediction_file(filename: str):
    try:
        # 1. 解码文件名（处理URL编码，兼容中文/特殊字符）
        filename_decoded = urllib.parse.unquote(filename)
        # 2. 替换路径分隔符（统一为系统分隔符）
        filename_decoded = filename_decoded.replace("/", OS_SEP).replace("\\", OS_SEP)
        
        # 3. 安全拼接路径（防止路径遍历）
        try:
            local_file_path = safe_join(LOCAL_BIOMASS_RESULTS_DIR, filename_decoded)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"路径格式错误：{str(e)}")
        
        # 4. 检查文件是否存在
        if not os.path.exists(local_file_path):
            raise HTTPException(status_code=404, detail=f"文件不存在：{local_file_path}")
        
        # 5. 检查文件读取权限
        if not os.access(local_file_path, os.R_OK):
            raise HTTPException(status_code=403, detail=f"无文件读取权限：{local_file_path}")
        
        # 6. 媒体类型映射（补充.joblib/.pkl支持）
        ext = os.path.splitext(local_file_path)[1].lower()
        media_type_map = {
            ".tif": "image/tiff",
            ".tiff": "image/tiff",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".json": "application/json",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".geojson": "application/json",
            ".joblib": "application/octet-stream",  # 新增：支持joblib文件
            ".pkl": "application/octet-stream"      # 新增：支持pickle文件
        }
        media_type = media_type_map.get(ext, "application/octet-stream")
        
        # 7. 本地文件直接返回（优化响应头，解决307重定向 + 强制下载.joblib）
        disposition_type = "attachment" if ext in [".joblib", ".pkl", ".csv"] else "inline"
        return FileResponse(
            local_file_path,
            media_type=media_type,
            filename=filename_decoded,
            headers={
                "Content-Disposition": f"{disposition_type}; filename*=UTF-8''{urllib.parse.quote(filename_decoded)}",
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff"  # 防止浏览器解析错误
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        # 精准捕获所有异常，返回具体错误信息
        raise HTTPException(status_code=500, detail=f"加载预测文件失败：{str(e)}")

# ===================== 图表文件接口（charts） =====================
@router.get("/charts/{filename:path}")
async def get_chart_file(filename: str):
    try:
        filename_decoded = urllib.parse.unquote(filename)
        filename_decoded = filename_decoded.replace("/", OS_SEP).replace("\\", OS_SEP)
        
        # charts目录也统一到data下
        local_charts_dir = os.path.join(settings.BASE_DATA_DIR, "charts")
        os.makedirs(local_charts_dir, exist_ok=True)
        
        # 安全路径拼接
        local_file_path = safe_join(local_charts_dir, filename_decoded)
        
        # 检查文件存在性和权限
        if not os.path.exists(local_file_path):
            raise HTTPException(status_code=404, detail=f"本地图表文件不存在：{local_file_path}")
        if not os.access(local_file_path, os.R_OK):
            raise HTTPException(status_code=403, detail=f"无图表文件读取权限：{local_file_path}")
        
        return FileResponse(
            local_file_path,
            media_type="image/png",
            filename=filename_decoded,
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{urllib.parse.quote(filename_decoded)}",
                "Cache-Control": "no-cache"
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载图表失败：{str(e)}")

# ===================== 特征栅格接口（raster） =====================
@router.get("/raster/{filename:path}")
async def get_raster_file(filename: str):
    try:
        filename_decoded = urllib.parse.unquote(filename)
        filename_decoded = filename_decoded.replace("/", OS_SEP).replace("\\", OS_SEP)
        
        # 特征栅格目录
        local_raster_dir = os.path.join(settings.BASE_DATA_DIR, "特征栅格")
        os.makedirs(local_raster_dir, exist_ok=True)
        
        # 安全路径拼接
        local_file_path = safe_join(local_raster_dir, filename_decoded)
        
        # 检查文件存在性和权限
        if not os.path.exists(local_file_path):
            raise HTTPException(status_code=404, detail=f"本地栅格文件不存在：{local_file_path}")
        if not os.access(local_file_path, os.R_OK):
            raise HTTPException(status_code=403, detail=f"无栅格文件读取权限：{local_file_path}")
        
        return FileResponse(
            local_file_path,
            media_type="image/tiff",
            filename=filename_decoded,
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{urllib.parse.quote(filename_decoded)}",
                "Cache-Control": "no-cache"
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载栅格失败：{str(e)}")

# ===================== 通用下载接口 =====================
@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    try:
        file_path_decoded = urllib.parse.unquote(file_path)
        file_path_decoded = file_path_decoded.replace("/", OS_SEP).replace("\\", OS_SEP)
        
        # 安全校验：确保下载路径在BASE_DATA_DIR内
        base_dir = os.path.normpath(settings.BASE_DATA_DIR)
        full_path = safe_join(base_dir, file_path_decoded)
        
        # 检查文件存在性和权限
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"下载文件不存在：{full_path}")
        if not os.access(full_path, os.R_OK):
            raise HTTPException(status_code=403, detail=f"无下载文件读取权限：{full_path}")
        
        return get_file_download_response(full_path)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败：{str(e)}")

# ===================== 图片预览接口 =====================
@router.get("/image/{file_path:path}")
async def preview_image(file_path: str):
    try:
        file_path_decoded = urllib.parse.unquote(file_path)
        file_path_decoded = file_path_decoded.replace("/", OS_SEP).replace("\\", OS_SEP)
        
        # 如果是biomass_results的图片，调用专用函数
        if "biomass_results" in file_path_decoded:
            # 提取biomass_results后的文件名
            filename = file_path_decoded.split(f"biomass_results{OS_SEP}")[-1]
            return get_biomass_results_image_response(filename)
        
        # 安全校验
        base_dir = os.path.normpath(settings.BASE_DATA_DIR)
        full_path = safe_join(base_dir, file_path_decoded)
        
        return get_image_preview_response(full_path)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败：{str(e)}")

# ===================== 根接口（测试用） =====================
@router.get("/")
async def get_file(
    path: str = Query(..., description="基于data的相对路径，如 biomass_results/xxx.tif"),
    action: str = Query("preview")
):
    try:
        path_decoded = urllib.parse.unquote(path)
        path_decoded = path_decoded.replace("/", OS_SEP).replace("\\", OS_SEP)

        # 新增：移除开头的 data/ 或 data\ 前缀
        if path_decoded.startswith(f"data{OS_SEP}") or path_decoded.startswith(f"\\data{OS_SEP}") or path_decoded.startswith(f"/data{OS_SEP}"):
            path_decoded = path_decoded.split(f"data{OS_SEP}", 1)[1]
        
        # 优先处理biomass_results（兼容.joblib）
        if "biomass_results" in path_decoded:
            filename = path_decoded.split(f"biomass_results{OS_SEP}")[-1]
            if action == "preview":
                return get_biomass_results_image_response(filename)
            else:
                local_path = get_biomass_results_file_path(filename)
                # 安全校验
                safe_local_path = safe_join(LOCAL_BIOMASS_RESULTS_DIR, filename)
                return get_file_download_response(safe_local_path)
        
        # 其他路径安全校验
        base_dir = os.path.normpath(settings.BASE_DATA_DIR)
        full_path = safe_join(base_dir, path_decoded)
        
        # 区分图片预览和文件下载（兼容.joblib）
        if full_path.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
            return get_image_preview_response(full_path)
        else:
            return get_file_download_response(full_path)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件操作失败：{str(e)}")