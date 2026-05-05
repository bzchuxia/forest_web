import rasterio
import numpy as np

# 用任意一个现有栅格作为模板
with rasterio.open("DEM.tif") as src:
    meta = src.meta.copy()
    height, width = src.shape
    transform = src.transform

    # 生成经纬度网格
    x_coords = np.zeros((height, width), dtype=np.float32)
    y_coords = np.zeros((height, width), dtype=np.float32)

    for i in range(height):
        for j in range(width):
            x, y = transform * (j, i)
            x_coords[i, j] = x
            y_coords[i, j] = y

    # 写入 jindu.tif (经度/UTM X)
    meta.update(dtype="float32", count=1)
    with rasterio.open("jindu.tif", "w", **meta) as dst:
        dst.write(x_coords, 1)

    # 写入 weidu.tif (纬度/UTM Y)
    with rasterio.open("weidu.tif", "w", **meta) as dst:
        dst.write(y_coords, 1)

print("✅ jindu.tif 和 weidu.tif 生成完成")