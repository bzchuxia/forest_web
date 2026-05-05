# -*- coding: utf-8 -*-
"""
空间生物量预测模块（企业级优化版 - 纯净本地计算模式）
核心特性：
1. 严格遵循SOLID原则，函数职责单一
2. 精准异常捕获，避免误判文件缺失
3. 路径解析增强，兼容多场景文件查找 (仅限本地)
4. 完善的日志系统，便于问题定位
5. 企业级容错机制，非核心错误不中断流程
6. 【重要变更】移除所有 HDFS 直接操作逻辑，假设输入均为本地路径
"""
import os
import logging
import sys
import tempfile
import shutil
import warnings
import re
import traceback
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# 第三方库导入 (保留 hdfs 导入以防万一，但不再使用)
# from hdfs import InsecureClient 
import joblib
import pandas as pd
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import xy as transform_xy
from rasterio.mask import mask
from rasterio.errors import RasterioIOError
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  
from pyproj import Transformer, CRS
import json
import fiona
from hdfs import InsecureClient
from app.core.config import settings


# ===================== 企业级配置与日志（核心优化1） =====================
# 1. 日志配置（企业级标准：分级、格式化、输出到文件+控制台）
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "biomass_prediction.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("biomass_prediction")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

# 2. 环境变量配置（企业级：集中管理，避免散列）
ENV_CONFIG = {
    "PROJ_DEBUG": "0",
    "PROJ_LIB": "",
    "CPLE_APP_APP_DEFINED": "IGNORE",
    "CPLE_IGNORE_GEO_KEYS": "YES",
    "GTIFF_SRS_SOURCE": "EPSG",
    "GDAL_DISABLE_READDIR_ON_OPEN": "YES",
    "PYTHONIOENCODING": "utf-8"
}
for key, value in ENV_CONFIG.items():
    os.environ[key] = value

# 3. 系统编码强制设置
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 4. 警告过滤（仅保留严重警告）
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=RuntimeWarning)

# 5. Rasterio/GDAL日志降级
logging.getLogger("rasterio._env").setLevel(logging.ERROR)
logging.getLogger("GDAL").setLevel(logging.ERROR)
logging.getLogger("rasterio").setLevel(logging.ERROR)

# ===================== 企业级数据结构（核心优化2） =====================
@dataclass(frozen=True)
class AppConfig:
    """应用配置类（企业级：类型安全，不可变）"""
    # HDFS 配置已移除，由全局 config 统一管理，此处仅保留本地计算相关配置
    BASE_DATA_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data")
    RASTER_DIR: str = ""
    TIMESTAMP_PATTERN: re.Pattern = re.compile(r'^\d{8}_\d{6}$')
    BATCH_SIZE: int = 100000
    MAX_GRIDS: int = 1000

# 初始化配置
try:
    from app.core.config import settings
    app_config = AppConfig(
        BASE_DATA_DIR=getattr(settings, 'BASE_DATA_DIR', AppConfig.BASE_DATA_DIR),
        RASTER_DIR=getattr(settings, 'RASTER_DIR', "")
    )
except ImportError:
    app_config = AppConfig()

# 补全栅格目录
if not app_config.RASTER_DIR:
    app_config = AppConfig(
        **{k: v for k, v in app_config.__dict__.items() if k != "RASTER_DIR"},
        RASTER_DIR=os.path.join(app_config.BASE_DATA_DIR, "raster")
    )
    # hdfs保存
def get_hdfs_client():
    hdfs_url = f"http://{settings.HDFS_HOST}:{settings.HDFS_PORT}"
    return InsecureClient(hdfs_url, user=settings.HDFS_USER)

def upload_to_hdfs(local_path: str, hdfs_relative_path: str):
    try:
        client = get_hdfs_client()
        hdfs_full_path = f"/forest/results/heatmap/{hdfs_relative_path.lstrip('/')}"
        hdfs_dir = os.path.dirname(hdfs_full_path)
        client.makedirs(hdfs_dir)
        client.upload(hdfs_full_path, local_path, overwrite=True)
        logger.info(f"✅ 上传 HDFS 成功: {hdfs_full_path}")
        return hdfs_full_path
    except Exception as e:
        logger.error(f"❌ HDFS 上传失败: {str(e)}")
        return None
    
# ===================== 全局资源初始化（核心优化3） =====================
# 1. Matplotlib配置（企业级：统一样式）
plt.rcParams.update({
    'font.sans-serif': ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS'],
    'axes.unicode_minus': False,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'figure.figsize': (12, 10),
    'font.size': 12
})

# HDFS 客户端初始化逻辑已移除，不再在此处管理连接

# ===================== 工具函数（企业级重构） =====================
def safe_remove(path: str) -> None:
    """安全删除文件/目录（企业级：无异常中断）"""
    try:
        if os.path.isfile(path):
            os.remove(path)
            logger.debug(f"删除文件成功：{path}")
        elif os.path.isdir(path):
            shutil.rmtree(path)
            logger.debug(f"删除目录成功：{path}")
    except Exception as e:
        logger.warning(f"清理文件失败 {path}: {str(e)}")

def validate_timestamp(timestamp: str) -> str:
    """校验时间戳（企业级：严格校验+友好提示）"""
    if not isinstance(timestamp, str):
        raise ValueError(f"时间戳必须为字符串类型（当前：{type(timestamp)}）")
    
    # 兼容纯数字格式
    clean_ts = timestamp.replace("_", "")
    if len(clean_ts) == 14 and clean_ts.isdigit():
        timestamp = f"{clean_ts[:8]}_{clean_ts[8:]}"
    
    if not app_config.TIMESTAMP_PATTERN.match(timestamp):
        raise ValueError(
            f"时间戳格式错误！必须为 YYYYMMDD_HHMMSS（当前：{timestamp}）"
        )
    return timestamp

def convert_abs_to_virtual_path(abs_path: str) -> str:
    """绝对路径转虚拟路径（企业级：边界检查）"""
    if not abs_path or not isinstance(abs_path, str):
        return ""
    if abs_path.startswith(app_config.BASE_DATA_DIR):
        return abs_path.replace(app_config.BASE_DATA_DIR, "/data", 1)
    return abs_path

# ===================== 路径解析（核心优化：仅限本地查找） =====================
def resolve_file_path(
    file_path: str, 
    file_type: str = "raster", 
    temp_dir: str = None, 
    timestamp: str = ""
) -> str:
    """
    解析文件路径
    【重要变更】移除了 HDFS 下载逻辑。
    查找优先级：
    1. 传入的绝对路径（存在则直接返回）
    2. 模型文件优先查找biomass_results目录（兼容旧路径）
    3. 虚拟路径转换为本地路径
    4. 本地相对路径（多目录兜底）
    """
    logger.info(f"\n解析文件路径 - 原始路径：{file_path}，类型：{file_type}，时间戳：{timestamp}")
    
    # 步骤1：处理时间戳替换（仅当*存在且时间戳有效时）
    final_ts = ""
    if timestamp:
        try:
            final_ts = validate_timestamp(timestamp)
        except ValueError:
            logger.warning(f"时间戳格式无效，跳过替换：{timestamp}")
    
    # 步骤2：替换路径中的*
    if "*" in file_path and final_ts:
        file_path = file_path.replace("*", final_ts)
        logger.info(f"路径*替换完成：{file_path}")
    elif "*" in file_path:
        logger.warning("无法替换*：时间戳为空或无效")
    
    # 步骤3：虚拟路径转换
    if file_path.startswith("/data/"):
        file_path = os.path.join(app_config.BASE_DATA_DIR, file_path.replace("/data/", "", 1))
        logger.info(f"虚拟路径转换完成：{file_path}")
    
    # 步骤4：绝对路径直接返回（核心：优先本地文件）
    if os.path.isabs(file_path) and os.path.exists(file_path):
        logger.info(f"找到绝对路径文件：{file_path}")
        return file_path
    
    # 步骤5：模型文件特殊处理（兼容biomass_results目录）
    if file_type == "model" and final_ts:
        file_name = os.path.basename(file_path)
        model_candidate_paths = [
            os.path.join(app_config.BASE_DATA_DIR, "biomass_results", final_ts, file_name),
            os.path.join(app_config.BASE_DATA_DIR, "biomass_results", file_name),
            file_path
        ]
        for candidate in model_candidate_paths:
            if os.path.exists(candidate):
                logger.info(f"找到模型文件：{candidate}")
                return candidate
    
    # 步骤6：初始化临时目录（如果需要创建临时文件，但目前逻辑主要做查找）
    if not temp_dir:
        temp_dir = tempfile.mkdtemp(prefix=f"biomass_{file_type}_")
    
    # 步骤7：本地多目录兜底查找（核心优化：避免文件误判缺失）
    local_check_paths = [
        file_path,
        os.path.join(app_config.BASE_DATA_DIR, file_path),
        os.path.join(app_config.BASE_DATA_DIR, "biomass_results", file_path),
        os.path.join(app_config.RASTER_DIR, file_path),
        os.path.join(os.getcwd(), file_path)
    ]
    
    for check_path in local_check_paths:
        abs_check_path = os.path.abspath(check_path)
        if os.path.exists(abs_check_path):
            logger.info(f"本地兜底找到文件：{abs_check_path}")
            return abs_check_path
    
    # 最终未找到（企业级：详细日志）
    raise FileNotFoundError(
        f"文件不存在：{file_path}\n"
        f"已检查路径：{local_check_paths}\n"
        f"本地基础目录：{app_config.BASE_DATA_DIR}\n"
        f"提示：请确保上层服务 (task_service) 已将 HDFS 文件下载至本地"
    )

# ===================== GeoJSON生成（企业级：容错增强） =====================
def tif_to_geojson(
    tif_path: str, 
    geojson_path: str, 
    timestamp: str, 
    threshold: float = 0, 
    max_grids: int = app_config.MAX_GRIDS
) -> None:
    """生成GeoJSON"""
    timestamp = validate_timestamp(timestamp)
    temp_dir = tempfile.mkdtemp(prefix=f"biomass_geojson_{timestamp}_")
    
    try:
        local_tif_path = resolve_file_path(tif_path, "raster", temp_dir)
        logger.info(f"开始生成GeoJSON{local_tif_path} -> {geojson_path}")
        
        with rasterio.open(local_tif_path) as src:
            biomass_data = src.read(1).astype(np.float32)
            transform = src.transform
            height, width = biomass_data.shape
            
            # 处理NoData
            nodata_values = [src.nodata, -9999, -32768, np.nan]
            for ndv in nodata_values:
                if ndv is not None and not np.isnan(ndv):
                    biomass_data = np.where(biomass_data == ndv, np.nan, biomass_data)
            
            # 坐标转换（核心优化：容错+默认CRS）
            src_crs = None
            try:
                if src.crs and src.crs.is_valid:
                    src_crs = src.crs.to_string()
                else:
                    src_crs = "EPSG:32650"
                transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
            except Exception as e:
                logger.warning(f"坐标转换器初始化失败 使用默认CRS{str(e)}")
                transformer = Transformer.from_crs("EPSG:32650", "EPSG:4326", always_xy=True)
            
            # 动态计算方格大小（企业级：避免内存溢出）
            total_pixels = height * width
            pixels_per_grid = max(1, int(np.sqrt(total_pixels / max_grids)))
            logger.info(f"GeoJSON方格大小{pixels_per_grid}x{pixels_per_grid}，最大方格数：{max_grids}")
            
            features = []
            valid_grids = 0
            invalid_grids = 0
            
            for row in range(0, height, pixels_per_grid):
                for col in range(0, width, pixels_per_grid):
                    try:
                        row_end = min(row + pixels_per_grid, height)
                        col_end = min(col + pixels_per_grid, width)
                        
                        # 过滤无效数据
                        grid_biomass = biomass_data[row:row_end, col:col_end]

                        logger.debug(f"网格({row},{col})原始数据统计：min={grid_biomass.min()}, max={grid_biomass.max()}, mean={grid_biomass.mean()}")

                        valid_mask = ~np.isnan(grid_biomass) & (grid_biomass >= threshold)
                        valid_biomass = grid_biomass[valid_mask]
                        
                        if len(valid_biomass) == 0:
                            invalid_grids += 1
                            continue
                        
                        # 计算统计值
                        avg_biomass = float(np.mean(valid_biomass))
                        min_biomass = float(np.min(valid_biomass))
                        max_biomass = float(np.max(valid_biomass))
                        
                        # 坐标转换
                        coords = []
                        for r, c in [(row, col), (row, col_end), (row_end, col_end), (row_end, col)]:
                            try:
                                lon_utm, lat_utm = transform_xy(transform, r, c)
                                lon, lat = transformer.transform(lon_utm, lat_utm)
                                coords.append((float(lon), float(lat)))
                            except Exception as e:
                                logger.warning(f"网格({row},{col})坐标转换失败，使用默认坐标：{str(e)}")
                                center_x, center_y = transform * ((col + col_end) / 2, (row + row_end) /2)
                                coords.append((center_x, center_y))

                        coords.append(coords[0])  # 闭合多边形
                        
                        # 构建Feature
                        feature = {
                            "type": "Feature",
                            "geometry": {"type": "Polygon", "coordinates": [coords]},
                            "properties": {
                                "biomass": avg_biomass,
                                "min_biomass": min_biomass,
                                "max_biomass": max_biomass,
                                "timestamp": timestamp,
                                "grid_id": f"{row}_{col}" # 增加 Grid ID 便于前端调试
                            }
                        }
                        features.append(feature)
                        valid_grids += 1
                        
                    except Exception as e:
                        invalid_grids += 1
                        logger.debug(f"网格({row},{col})处理失败：{str(e)}")
                        continue
            
            # 生成GeoJSON
            geojson = {
                "type": "FeatureCollection",
                "features": features,
                "properties": {
                    "timestamp": timestamp,
                    "valid_grids": valid_grids,
                    "invalid_grids": invalid_grids,
                    "threshold": threshold
                }
            }
            # 定义一个安全的序列化函数
            def safe_serializer(obj):
                if isinstance(obj, (np.integer, np.floating)):
                    return float(obj) # 强制转为 Python float
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            # 保存文件
            os.makedirs(os.path.dirname(geojson_path), exist_ok=True)
            with open(geojson_path, 'w', encoding='utf-8') as f:
                json.dump(geojson, f, ensure_ascii=False, indent=2,default=safe_serializer)
            
            logger.info(f"GeoJSON生成完成：{geojson_path}（有效方格：{valid_grids}，无效方格：{invalid_grids}）")
    
    except Exception as e:
        logger.error(f"GeoJSON生成失败：{str(e)}", exc_info=True)
        raise
    finally:
        safe_remove(temp_dir)

def convert_numpy_types(obj):
    """
    递归地将对象中的 NumPy 数据类型转换为 Python 原生类型。
    """
    if isinstance(obj, np.generic):
        # 如果是单个数值，直接转换为 int 或 float
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    elif isinstance(obj, dict):
        # 如果是字典，递归处理键值对
        return {convert_numpy_types(k): convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        # 如果是列表或元组，递归处理元素
        return [convert_numpy_types(item) for item in obj]
    return obj

# ===================== 核心预测函数（企业级重构） =====================
def generate_spatial_biomass_map(
    model_path: str, 
    feature_list_path: str, 
    raster_dir: str = None, 
    output_path: str = None,
    timestamp: Optional[str] = None,
    model_name: str = "unknown_model"
) -> Dict[str, str]:
    """
    生成空间生物量热力图（企业级核心函数）
    :param model_path: 模型路径（必须是本地路径）
    :param feature_list_path: 特征列表路径（必须是本地路径）
    :param raster_dir: 栅格目录（必须是本地路径）
    :param output_path: 输出路径
    :param timestamp: 时间戳（YYYYMMDD_HHMMSS）
    :param model_name: 模型名称
    :return: 生成文件路径字典
    """
    # 初始化返回结果
    result_files = {
        "tif_path": "", "png_path": "", "geojson_path": "",
        "virtual_tif_path": "", "virtual_png_path": "", "virtual_geojson_path": "",
        "timestamp": ""
    }
    
    # 临时目录（企业级：唯一标识）
    temp_dir = None
    
    try:
        # 1. 基础校验（企业级：前置检查）
        if not timestamp:
            raise ValueError("必须传入时间戳（YYYYMMDD_HHMMSS）")
        timestamp = validate_timestamp(timestamp)
        result_files["timestamp"] = timestamp
        logger.info(f"开始空间生物量预测 - 时间戳：{timestamp}，模型：{model_name}")
        
        # 2. 目录配置（企业级：集中管理）
        raster_dir = raster_dir or app_config.RASTER_DIR
        heatmap_dir = os.path.join(app_config.BASE_DATA_DIR, "heatmap", timestamp, model_name)
        os.makedirs(heatmap_dir, exist_ok=True)
        
        # 3. 输出路径配置（企业级：规范命名）
        if output_path is None:
            output_filename = f"空间生物量预测_{timestamp}.tif"
            output_path = os.path.join(heatmap_dir, output_filename)
        else:
            output_filename = os.path.basename(output_path)
            if model_name not in output_filename:
                name_without_ext = os.path.splitext(output_filename)[0]
                output_filename = f"{name_without_ext}_{model_name}_{timestamp}.tif"
            output_path = os.path.join(heatmap_dir, output_filename)
        
        # 4. 临时目录初始化
        temp_dir = tempfile.mkdtemp(prefix=f"biomass_pred_{timestamp}_{os.urandom(4).hex()}_")
        logger.info(f"临时目录：{temp_dir}，输出目录：{heatmap_dir}")
        
        # 5. 加载模型和特征列表（核心优化：精准异常捕获）
        logger.info("加载模型和特征列表...")
        try:
            # 注意：resolve_file_path 现在只进行本地查找
            local_model_path = resolve_file_path(model_path, "model", temp_dir, timestamp)
            local_feature_list_path = resolve_file_path(feature_list_path, "model", temp_dir, timestamp)
            
            model = joblib.load(local_model_path)
            expected_features = joblib.load(local_feature_list_path)
            expected_features = [str(f).strip() for f in expected_features]
            
            logger.info(f"模型加载成功：{local_model_path}")
            logger.info(f"特征列表加载成功，共{len(expected_features)}个特征：{', '.join(expected_features)}")
        except FileNotFoundError as e:
            logger.error(f"模型/特征列表文件缺失：{str(e)}")
            raise
        except Exception as e:
            logger.error(f"模型加载失败：{str(e)}", exc_info=True)
            raise
        
        # 6. 特征映射（企业级：集中管理）
        feature_mapping = {
            'ARVI': 'ARVI.tif', 'Blue': 'Blue.tif', 'DEM': 'DEM.tif', 
            'DVI': 'DVI.tif', 'EVI': 'EVI.tif', 'GNDVI': 'GNDVI.tif',
            'Green': 'Green.tif', 'MeanVH': 'MeanVH.tif', 'MeanVV': 'MeanVV.tif',
            'MNDVI': 'MNDVI.tif', 'NDVI': 'NDVI.tif', 'NDWI': 'NDWI.tif',
            'NIR': 'NIR.tif', 'Red': 'Red.tif', 'SAVI': 'SAVI.tif',
            'SWIR1': 'SWIR1.tif', 'SWIR2': 'SWIR2.tif', 'TIR': 'TIR.tif',
            'jindu': 'jindu.tif', 'weidu': 'weidu.tif', '经度': 'jindu.tif', '纬度': 'weidu.tif',
            'Slope': 'podu.tif', 'podu': 'podu.tif',
            'Aspect': 'poxiangi.tif', 'poxiang': 'poxiangi.tif', 'poxiangi': 'poxiangi.tif',
            'VV_VH': 'VV_VH.tif', 'VV/VH': 'VV_VH.tif', 'vv_VH': 'VV_VH.tif',
            'Radar': 'Radar.tif', 'radar': 'Radar.tif', '(VV-VH)/(VV+VH)': 'Radar.tif',
            'BIO1': 'BIO1.tif', 'BIO2': 'BIO2.tif', 'BIO3': 'BIO3.tif',
            'BIO4': 'BIO4.tif', 'BIO5': 'BIO5.tif', 'BIO6': 'BIO6.tif',
            'BIO7': 'BIO7.tif', 'BIO8': 'BIO8.tif', 'BIO9': 'BIO9.tif',
            'BIO10': 'BIO10.tif', 'BIO11': 'BIO11.tif', 'BIO12': 'BIO12.tif',
            'BIO13': 'BIO13.tif', 'BIO14': 'BIO14.tif', 'BIO15': 'BIO15.tif',
            'BIO16': 'BIO16.tif', 'BIO17': 'BIO17.tif', 'BIO18': 'BIO18.tif',
            'BIO19': 'BIO19.tif'
        }
        
        # 7. 栅格目录处理
        local_raster_dir = resolve_file_path(raster_dir, "raster", temp_dir)
        if not os.path.isdir(local_raster_dir):
            raise NotADirectoryError(f"栅格目录不存在：{local_raster_dir}")
        
        # 8. 基准图层选择（企业级：多候选+兜底）
        master_file = None
        master_candidates = ['NIR.tif', 'NDVI.tif', 'Red.tif', 'DEM.tif']
        for candidate in master_candidates:
            candidate_path = os.path.join(local_raster_dir, candidate)
            if os.path.exists(candidate_path):
                master_file = candidate_path
                break
        
        if not master_file:
            tif_files = [f for f in os.listdir(local_raster_dir) if f.endswith('.tif')]
            if not tif_files:
                raise FileNotFoundError(f"栅格目录中无TIF文件：{local_raster_dir}")
            master_file = os.path.join(local_raster_dir, tif_files[0])
        
        logger.info(f"基准图层：{os.path.basename(master_file)}")
        
        with rasterio.open(master_file) as src_master:
            master_profile = src_master.profile.copy()
            master_transform = src_master.transform
            master_crs = src_master.crs or CRS.from_epsg(32650)
            master_shape = (src_master.height, src_master.width)
            master_nodata = src_master.nodata if src_master.nodata is not None else np.nan
        
        # 9. 特征加载与对齐（核心优化：精准异常捕获，避免误判缺失）
        data_dict: Dict[str, np.ndarray] = {}
        missing_features = []
        feature_alias_map = {
            '纬度': 'weidu', '经度': 'jindu', 'Slope': 'podu',
            'poxiang': 'Aspect', 'radar': 'Radar', 'VV/VH': 'VV_VH'
        }
        
        for feature in expected_features:
            # 跳过衍生特征
            if feature in ['RDVI', 'RVI', 'GDVI']:
                continue
            
            try:
                # 特征别名转换
                std_feature = feature_alias_map.get(feature, feature)
                if std_feature not in feature_mapping:
                    missing_features.append(feature)
                    logger.warning(f"特征{feature}无映射关系，标记为缺失")
                    continue
                
                # 构建文件路径
                file_name = feature_mapping[std_feature]
                file_path = os.path.join(local_raster_dir, file_name)
                local_file_path = resolve_file_path(file_path, "raster", temp_dir)
                
                # 读取并对齐特征
                with rasterio.open(local_file_path) as src:
                    src_crs = src.crs or master_crs
                    src_nodata = src.nodata if src.nodata is not None else 0
                    band_data = src.read(1).astype(np.float32)
                    
                    # 对齐尺寸（核心优化：仅当必要时重投影）
                    if (src.height, src.width) != master_shape or src.transform != master_transform:
                        logger.info(f"对齐特征{feature}：尺寸{src.height}x{src.width} -> {master_shape[0]}x{master_shape[1]}")
                        aligned_data = np.full(master_shape, master_nodata, dtype=np.float32)
                        reproject(
                            source=band_data,
                            destination=aligned_data,
                            src_transform=src.transform,
                            src_crs=src_crs,
                            dst_transform=master_transform,
                            dst_crs=master_crs,
                            resampling=Resampling.bilinear,
                            src_nodata=src_nodata,
                            dst_nodata=master_nodata
                        )
                        band_data = aligned_data
                
                # 处理NoData
                band_data = np.where(
                    (band_data == src_nodata) | np.isnan(band_data) | np.isinf(band_data),
                    master_nodata,
                    band_data
                )
                data_dict[feature] = band_data.flatten()
                logger.info(f"特征{feature}加载成功")
                
            # 仅捕获文件相关异常（核心优化：避免误判）
            except (FileNotFoundError, RasterioIOError) as e:
                missing_features.append(feature)
                logger.error(f"特征{feature}文件缺失/读取失败：{str(e)}")
            # 其他异常仅警告，不标记为缺失（避免误判）
            except Exception as e:
                logger.warning(f"特征{feature}处理警告：{str(e)}")
                continue
        
        # 检查缺失特征（企业级：明确提示）
        if missing_features:
            raise ValueError(f"缺少必要特征文件：{', '.join(missing_features)}")
        
        # 10. 衍生特征计算（企业级：容错+日志）
        logger.info("计算衍生特征...")
        
        def _safe_get_band(band_name: str) -> np.ndarray:
            """安全获取波段数据（企业级：复用逻辑）"""
            if band_name in data_dict:
                return data_dict[band_name].copy()
            
            file_name = feature_mapping.get(band_name, f"{band_name}.tif")
            file_path = os.path.join(local_raster_dir, file_name)
            local_file_path = resolve_file_path(file_path, "raster", temp_dir)
            
            with rasterio.open(local_file_path) as src:
                src_crs = src.crs or master_crs
                src_nodata = src.nodata or 0
                src_data = src.read(1).astype(np.float32)
                
                if (src.height, src.width) != master_shape:
                    aligned_data = np.zeros(master_shape, dtype=np.float32)
                    reproject(
                        source=src_data,
                        destination=aligned_data,
                        src_transform=src.transform,
                        src_crs=src_crs,
                        dst_transform=master_transform,
                        dst_crs=master_crs,
                        resampling=Resampling.bilinear,
                        src_nodata=src_nodata,
                        dst_nodata=master_nodata
                    )
                    band_data = aligned_data.flatten()
                else:
                    band_data = src_data.flatten()
            
            return np.where((band_data == src_nodata) | np.isnan(band_data), master_nodata, band_data)
        
        # 计算衍生特征
        if 'RDVI' in expected_features or 'RVI' in expected_features:
            nir = _safe_get_band('NIR')
            red = _safe_get_band('Red')
            
            if 'RDVI' in expected_features:
                denominator = np.sqrt(np.abs(nir + red) + 1e-8)
                data_dict['RDVI'] = (nir - red) / denominator
                logger.info("衍生特征RDVI计算完成")
            
            if 'RVI' in expected_features:
                data_dict['RVI'] = nir / (red + 1e-8)
                logger.info("衍生特征RVI计算完成")
        
        if 'GDVI' in expected_features:
            nir = _safe_get_band('NIR')
            green = _safe_get_band('Green')
            data_dict['GDVI'] = nir - green
            logger.info("衍生特征GDVI计算完成")
        
        # 11. 预测数据构建（企业级：数据清洗）
        logger.info("构建预测数据集...")
        feature_data = []
        for feat in expected_features:
            if feat not in data_dict:
                raise ValueError(f"特征{feat}数据缺失")
            feature_data.append(data_dict[feat])
        
        X_spatial = np.column_stack(feature_data)
        X_spatial_df = pd.DataFrame(X_spatial, columns=expected_features)
        
        # 数据清洗（企业级：处理极值和空值）
        X_spatial_df = X_spatial_df.replace([np.inf, -np.inf], np.nan)
        X_spatial_df = X_spatial_df.fillna(X_spatial_df.mean())
        logger.info(f"预测数据集构建完成，共{len(X_spatial_df)}条记录")
        
        # 12. 批量预测（企业级：进度日志）
        logger.info(f"开始批量预测，批次大小：{app_config.BATCH_SIZE}")
        y_pred = []
        total_batches = (len(X_spatial_df) + app_config.BATCH_SIZE - 1) // app_config.BATCH_SIZE

        X_spatial_df = X_spatial_df.fillna(X_spatial_df.mean())
        X_spatial_df = X_spatial_df.fillna(0)
        # 第三步：检查是否还有 NaN（日志确认）
        nan_count = X_spatial_df.isna().sum().sum()
        if nan_count > 0:
            logger.warning(f"⚠️ 仍有 {nan_count} 个 NaN，将全部替换为 0")
            X_spatial_df = X_spatial_df.fillna(0)
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * app_config.BATCH_SIZE
            end_idx = min((batch_idx + 1) * app_config.BATCH_SIZE, len(X_spatial_df))
            batch_pred = model.predict(X_spatial_df.iloc[start_idx:end_idx])
            y_pred.extend(batch_pred)
            
            progress = (end_idx / len(X_spatial_df)) * 100
            logger.info(f"预测进度：{progress:.1f}%（批次{batch_idx+1}/{total_batches}）")
        
        y_pred = np.array(y_pred)
        logger.info("空间预测完成")
        
        # 13. 保存TIF文件（企业级：NoData恢复）
        logger.info("保存TIF文件...")
        biomass_map = y_pred.reshape(master_shape)
        
        # 恢复NoData值
        original_data = _safe_get_band('NIR').reshape(master_shape)
        biomass_map = np.where(np.isnan(original_data), master_nodata, biomass_map)
        
        # 更新Profile（企业级：压缩+大文件支持）
        master_profile.update(
            dtype=rasterio.float32,
            count=1,
            compress='lzw',
            nodata=master_nodata,
            BIGTIFF='IF_SAFER',
            tiled=True,
            blockxsize=256,
            blockysize=256
        )
        
        # 保存文件
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with rasterio.open(output_path, 'w', **master_profile) as dst:
            dst.write(biomass_map.astype(rasterio.float32), 1)
        
        result_files["tif_path"] = output_path
        result_files["virtual_tif_path"] = convert_abs_to_virtual_path(output_path)
        logger.info(f"TIF文件保存成功：{output_path}")
        
        # 14. 边界裁剪（企业级：非核心错误不中断）
        logger.info("尝试按边界裁剪...")
        boundary_file_name = 'maoershan_boundary.geojson'
        boundary_paths = [
            os.path.join(app_config.BASE_DATA_DIR, 'boundary', boundary_file_name),
            os.path.join(local_raster_dir, boundary_file_name),
            os.path.join(temp_dir, boundary_file_name)
        ]
        
        boundary_local_path = None
        for path in boundary_paths:
            if os.path.exists(path):
                boundary_local_path = path
                break
        
        # 执行裁剪
        if boundary_local_path and os.path.exists(boundary_local_path):
            try:
                with fiona.open(boundary_local_path, "r") as shapefile:
                    shapes = [f["geometry"] for f in shapefile if f["geometry"]]
                
                if shapes:
                    with rasterio.open(output_path) as src:
                        out_image, out_transform = mask(
                            src, shapes, crop=True, nodata=master_nodata,
                            filled=True, all_touched=True
                        )
                        out_meta = src.meta.copy()
                    
                    out_meta.update({
                        "transform": out_transform,
                        "height": out_image.shape[1],
                        "width": out_image.shape[2]
                    })
                    
                    with rasterio.open(output_path, "w", **out_meta) as dest:
                        dest.write(out_image)
                    
                    biomass_map = out_image[0]
                    logger.info("边界裁剪完成")
            except Exception as e:
                logger.warning(f"边界裁剪失败（非核心错误，继续执行）：{str(e)}")
        else:
            logger.warning("边界文件未找到，跳过裁剪")
        
        # 15. 生物量统计（企业级：分位数统计）
        valid_biomass = biomass_map[~np.isnan(biomass_map) & (biomass_map > 0)]
        if len(valid_biomass) > 0:
            min_biomass = np.percentile(valid_biomass, 2)  # 2%分位数（过滤异常值）
            max_biomass = np.percentile(valid_biomass, 98)  # 98%分位数
            avg_biomass = np.mean(valid_biomass)
            logger.info(f"生物量统计 - 最小值：{min_biomass:.2f}，最大值：{max_biomass:.2f}，平均值：{avg_biomass:.2f} 吨/公顷")
        else:
            min_biomass = 0.1
            max_biomass = 100
            logger.warning("无有效生物量数据，使用默认范围")
        
        # 16. 生成GeoJSON
        geojson_filename = f"Biomass_Prediction_{timestamp}.geojson"
        geojson_path = os.path.join(os.path.dirname(output_path), geojson_filename)
        tif_to_geojson(output_path, geojson_path, timestamp, threshold=min_biomass)
        
        result_files["geojson_path"] = geojson_path
        result_files["virtual_geojson_path"] = convert_abs_to_virtual_path(geojson_path)
        
        # 17. 生成PNG渲染图
        logger.info("生成PNG渲染图...")
        biomass_plot = np.where(biomass_map <= min_biomass, np.nan, biomass_map)
        
        plt.clf()
        img = plt.imshow(biomass_plot, cmap='RdYlBu_r', vmin=min_biomass, vmax=max_biomass)
        cbar = plt.colorbar(img, shrink=0.8)
        cbar.set_label('预测生物量 AGB (吨/公顷)', fontsize=14)
        plt.title(f'空间生物量预测热力图 ({timestamp})', fontsize=18, fontweight='bold', pad=15)
        plt.axis('off')
        
        png_filename = f"Biomass_Prediction_{timestamp}_渲染图.png"
        png_path = os.path.join(os.path.dirname(output_path), png_filename)
        plt.savefig(png_path, dpi=300, bbox_inches='tight', transparent=True)
        plt.close()
        
        result_files["png_path"] = png_path
        result_files["virtual_png_path"] = convert_abs_to_virtual_path(png_path)
        logger.info(f"PNG渲染图保存成功：{png_path}")
        
        valid_biomass = biomass_map[~np.isnan(biomass_map) & (biomass_map > 0)]
        stats = {
            "feature_count": int(np.sum(~np.isnan(biomass_map))), # 有效像元数
            "min_biomass": float(np.percentile(valid_biomass, 2)) if len(valid_biomass) > 0 else 0.0,
            "max_biomass": float(np.percentile(valid_biomass, 98)) if len(valid_biomass) > 0 else 0.0,
            "avg_biomass": float(np.mean(valid_biomass)) if len(valid_biomass) > 0 else 0.0
        }
        
        # 将统计信息合并到返回结果中
        result_files["statistics"] = stats
        # 同时也放一个顶层的 feature_count 兼容旧代码
        result_files["feature_count"] = stats["feature_count"]
        
        # ===================== 自动上传到 HDFS =====================
        upload_to_hdfs(result_files["tif_path"], f"{timestamp}/{os.path.basename(result_files['tif_path'])}")
        upload_to_hdfs(result_files["png_path"], f"{timestamp}/{os.path.basename(result_files['png_path'])}")
        upload_to_hdfs(result_files["geojson_path"], f"{timestamp}/{os.path.basename(result_files['geojson_path'])}")

        # 结果汇总
        logger.info("\n===== 空间预测完成 =====")
        logger.info(f"TIF文件：{result_files['tif_path']}")
        logger.info(f"PNG文件：{result_files['png_path']}")
        logger.info(f"GeoJSON文件：{result_files['geojson_path']}")
        logger.info("========================")
        
        return result_files
    
    except ValueError as ve:
        logger.error(f"业务逻辑错误：{str(ve)}")
        raise
    except Exception as e:
        logger.error(f"系统错误：{str(e)}", exc_info=True)
        raise
    finally:
        # 清理临时目录（企业级：确保执行）
        if temp_dir:
            safe_remove(temp_dir)
            logger.info(f"临时目录清理完成：{temp_dir}")

# ===================== 本地测试入口（企业级：规范测试） =====================
if __name__ == "__main__":
    """本地测试入口（仅调试使用）"""
    # 测试配置
    TEST_MODEL_PATH = r"D:\\desktop\\forest_web\\forest_web_backend\data\biomass_results\\PowerSHAP_RF_model_20260318_035444.joblib"
    TEST_FEATURE_LIST_PATH = r"D:\desktop\\forest_web\\forest_web_backend\data\biomass_results\\PowerSHAP_RF_feature_list_20260318_035444.joblib"
    TEST_TIMESTAMP = "20260318_035444"
    TEST_MODEL_NAME = "RF"
    
    try:
        # 执行测试
        logger.info("开始本地测试...")
        result = generate_spatial_biomass_map(
            model_path=TEST_MODEL_PATH,
            feature_list_path=TEST_FEATURE_LIST_PATH,
            timestamp=TEST_TIMESTAMP,
            model_name=TEST_MODEL_NAME
        )
        logger.info(f"本地测试成功！结果：{result}")
        print(f"\n测试成功！生成文件：")
        print(f"TIF: {result['tif_path']}")
        print(f"PNG: {result['png_path']}")
        print(f"GeoJSON: {result['geojson_path']}")
    except Exception as e:
        logger.error(f"本地测试失败：{str(e)}", exc_info=True)
        print(f"\n测试失败：{str(e)}")
        sys.exit(1)