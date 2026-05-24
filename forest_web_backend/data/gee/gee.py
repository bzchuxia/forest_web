import ee
import geemap
import geopandas as gpd
import os
import time
from datetime import datetime

# ====================== 【你只改这里】 ======================
SHP_PATH = r"D:/desktop/forest_web/forest_web_backend/data/帽儿山林地shp.shp"
TEMP_OUTPUT = r"D:/desktop/forest_web/forest_web_backend/temp/temp_sentinel"  # 临时目录
FLUME_MONITOR_DIR = r"F:/Docker/bigdata/flume/monitor"  # Flume 监控目录
CLOUD_COVERAGE = 20
# ============================================================

# 初始化GEE
ee.Initialize()

# 创建目录
os.makedirs(TEMP_OUTPUT, exist_ok=True)
os.makedirs(FLUME_MONITOR_DIR, exist_ok=True)

# 读取shp
gdf = gpd.read_file(SHP_PATH)
roi = geemap.geopandas_to_ee(gdf)

# 时间范围：2023年至今
start_date = "2023-01-01"
end_date = datetime.today().strftime("%Y-%m-%d")

# 加载哨兵2号
sentinel = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
           .filterBounds(roi)
           .filterDate(start_date, end_date)
           .filter(ee.Filter.lt('CLOUD_COVERAGE_ASSESSMENT', CLOUD_COVERAGE))
           .select(['B2', 'B3', 'B4', 'B8']))

count = sentinel.size().getInfo()
print(f"✅ 共找到 {count} 张影像")

# 日志文件（Flume 会实时读取这个文件！）
log_file = os.path.join(FLUME_MONITOR_DIR, "sentinel_data.log")

# 批量下载 + 输出给 Flume
image_list = sentinel.toList(count)

for i in range(count):
    try:
        img = ee.Image(image_list.get(i))
        date = img.date().format('YYYY-MM-dd').getInfo()
        img_id = img.id().getInfo()
        cloud = img.get('CLOUD_COVERAGE_ASSESSMENT').getInfo()

        print(f"正在处理：{date}")

        # 临时下载
        out_path = os.path.join(TEMP_OUTPUT, f"{date}_{img_id}.tif")
        geemap.download_ee_image(
            img.clip(roi),
            filename=out_path,
            region=roi.geometry(),
            scale=10,
            crs="EPSG:4326"
        )

        # ==============================================
        # 🔥 关键：生成 Flume 采集的日志行
        # ==============================================
        log_line = (
            f"{time.time()},{date},{img_id},{cloud},{os.path.abspath(out_path)}\n"
        )

        # 写入 Flume 监控目录
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_line)

        print(f"✅ 已写入 Flume 采集日志：{log_line}")

    except Exception as e:
        print(f"❌ 失败：{e}")

print("\n🎉 全部完成！Flume 已可以采集数据！")