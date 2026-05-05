import os
import joblib
import pandas as pd
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
import matplotlib.pyplot as plt
from datetime import datetime

# ===================== 全局配置 =====================
# 设定中文字体，防止生成的图片中文字符显示为方块
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False 

def generate_spatial_biomass_map(model_path, raster_dir, output_path):
    # 1. 加载模型
    print(f"正在加载模型: {model_path}")
    model = joblib.load(model_path)
    
    # 获取模型训练时“记忆”的特征名称和顺序
    expected_features = model.feature_names_in_
    print(f"\n模型一共需要 {len(expected_features)} 个特征。")
    print(f"正在自动匹配并读取: {list(expected_features)}\n")

    # 2. 建立所有可能的文件名映射字典（包含了别名和重命名兼容）
    base_mapping = {
        'ARVI': 'ARVI.tif', 'Blue': 'Blue.tif', 'DEM': 'DEM.tif', 'DVI': 'DVI.tif',
        'EVI': 'EVI.tif', 'GNDVI': 'GNDVI.tif', 'Green': 'Green.tif',
        'MeanVH': 'MeanVH.tif', 'MeanVV': 'MeanVV.tif', 'MNDVI': 'MNDVI.tif',
        'NDVI': 'NDVI.tif', 'NDWI': 'NDWI.tif', 'NIR': 'NIR.tif', 'Red': 'Red.tif',
        'SAVI': 'SAVI.tif', 'SWIR1': 'SWIR1.tif', 'SWIR2': 'SWIR2.tif', 'TIR': 'TIR.tif',
        'jindu': 'jindu.tif', 'weidu': 'weidu.tif', 
        '经度': 'jindu.tif', '纬度': 'weidu.tif', 
        
        # 兼容地形因子各种命名
        'Slope': 'podu.tif', 'podu': 'podu.tif',
        'Aspect': 'poxiangi.tif', 'poxiang': 'poxiangi.tif', 'poxiangi': 'poxiangi.tif',
        
        # 兼容雷达因子各种命名
        'VV_VH': 'VV_VH.tif', 'VV/VH': 'VV_VH.tif', 'vv_VH': 'VV_VH.tif',
        'Radar': 'Radar.tif', 'radar': 'Radar.tif', '(VV-VH)/(VV+VH)': 'Radar.tif'
    }
    # 批量把 BIO1 到 BIO19 塞进字典
    for i in range(1, 20):
        base_mapping[f'BIO{i}'] = f'BIO{i}.tif'

    # 3. 选取基准图层 (强制统一对齐到 NIR 的尺寸)
    master_file = os.path.join(raster_dir, 'NIR.tif')
    with rasterio.open(master_file) as src_master:
        master_profile = src_master.profile
        master_transform = src_master.transform
        master_crs = src_master.crs
        master_shape = (src_master.height, src_master.width)

    # 4. 根据模型需要的特征，精准提取和重采样
    data_dict = {}
    
    for feature in expected_features:
        # 衍生特征（稍后自己算），暂时跳过
        if feature in ['RDVI', 'RVI', 'GDVI']:
            continue
            
        if feature not in base_mapping:
            raise ValueError(f"❌ 找不到特征 '{feature}' 对应的tif文件，请检查拼写或文件夹！")
            
        file_name = base_mapping[feature]
        file_path = os.path.join(raster_dir, file_name)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ 文件夹里缺少模型必须的栅格文件: {file_name}")

        # 读取并动态对齐
        with rasterio.open(file_path) as src:
            if (src.height, src.width) == master_shape and src.transform == master_transform:
                band_data = src.read(1).astype(np.float32)
            else:
                print(f"  -> 正在对齐特征 [{feature}] (尺寸校准中)...")
                band_data = np.zeros(master_shape, dtype=np.float32)
                reproject(
                    source=rasterio.band(src, 1),
                    destination=band_data,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=master_transform,
                    dst_crs=master_crs,
                    resampling=Resampling.bilinear
                )
            data_dict[feature] = band_data.flatten()

    # 5. 生成衍生特征 (自动补充模型需要的计算值)
    def _get_band_temp(band_name):
        """如果衍生特征需要基础波段但基础波段没被读取，临时抓取并对齐"""
        if band_name in data_dict: 
            return data_dict[band_name]
        with rasterio.open(os.path.join(raster_dir, base_mapping[band_name])) as src:
            if (src.height, src.width) == master_shape: 
                return src.read(1).astype(np.float32).flatten()
            else:
                band_data = np.zeros(master_shape, dtype=np.float32)
                reproject(rasterio.band(src, 1), band_data, src_transform=src.transform, src_crs=src.crs, dst_transform=master_transform, dst_crs=master_crs, resampling=Resampling.bilinear)
                return band_data.flatten()

    print("正在处理衍生特征计算...")
    if 'RDVI' in expected_features or 'RVI' in expected_features:
        nir = _get_band_temp('NIR')
        red = _get_band_temp('Red')
        if 'RDVI' in expected_features: 
            data_dict['RDVI'] = (nir - red) / np.sqrt(np.abs(nir + red) + 1e-8)
        if 'RVI' in expected_features: 
            data_dict['RVI'] = nir / (red + 1e-8)
            
    if 'GDVI' in expected_features:
        nir = _get_band_temp('NIR')
        green = _get_band_temp('Green')
        data_dict['GDVI'] = nir - green

    # 6. 构建数据表：严格按照模型需要的特征顺序排序
    X_spatial = pd.DataFrame(data_dict)[expected_features]

    # 7. 清理空值 (将黑边、无效数据填0)
    print("正在清理无效值...")
    X_spatial.replace([np.inf, -np.inf], np.nan, inplace=True)
    X_spatial.fillna(0, inplace=True)

    # 8. 执行空间预测
    print(f"正在执行全空间预测，像素总数: {len(X_spatial)}...")
    y_pred = model.predict(X_spatial)

    # 9. 将结果写回 TIF 数据集
    print("正在保存 .tif 地理数据文件...")
    biomass_map = y_pred.reshape(master_shape)

    master_profile.update(
        dtype=rasterio.float32,
        count=1,
        compress='lzw'
    )

    with rasterio.open(output_path, 'w', **master_profile) as dst:
        dst.write(biomass_map.astype(rasterio.float32), 1)

    # ===================== 10. 新增：生成红色高清渲染图 =====================
    print("正在生成红色高清热力图 (.png)...")
    
    # 过滤掉预测值为0或以下的区域（通常是黑边或无效区域），使其变透明/白色
    biomass_plot = np.where(biomass_map <= 0, np.nan, biomass_map)
    
    plt.figure(figsize=(12, 10))
    # cmap='Reds' 设定颜色为：数值越大越红
    img = plt.imshow(biomass_plot, cmap='Reds') 
    
    # 添加图例颜色条
    cbar = plt.colorbar(img, shrink=0.8)
    cbar.set_label('预测生物量 AGB (mg/ha)', fontsize=14)
    
    plt.title('空间生物量预测热力图', fontsize=18, fontweight='bold', pad=15)
    plt.axis('off') # 关掉四周的坐标轴
    
    # 自动保存为 png
    png_path = output_path.replace('.tif', '_渲染图.png')
    plt.savefig(png_path, dpi=300, bbox_inches='tight', transparent=True)
    plt.close()
    
    print(f"\n🎉 任务圆满完成！")
    print(f"📍 TIF 数据源: {output_path}")
    print(f"🖼️ 红色热力图: {png_path}")

# ===================== 配置运行参数 =====================
if __name__ == "__main__":
    # 使用你最新报错的那次模型路径
    MODEL_FILE = r"F:\ComputerDe\RandomForest_model_20260306_133244.joblib" 
    RASTER_FOLDER = r"F:\ComputerDe\特征栅格"
    SAVE_PATH = os.path.join(r"F:\ComputerDe", f"Final_Biomass_Map_{datetime.now().strftime('%Y%m%d_%H%M')}.tif")

    generate_spatial_biomass_map(MODEL_FILE, RASTER_FOLDER, SAVE_PATH)