# app/core/hdfs_config.py
from hdfs import InsecureClient
import os
import sys

# ===================== 1. 基础配置 =====================
# 是否启用 HDFS (可通过环境变量覆盖，例如: export HDFS_ENABLED=false)
HDFS_ENABLED = os.getenv("HDFS_ENABLED", "True").lower() == "true"

# HDFS 连接信息
HDFS_HOST = os.getenv("HDFS_HOST", "localhost")
HDFS_PORT = int(os.getenv("HDFS_PORT", "9000"))
HDFS_USER = os.getenv("HDFS_USER", "hadoop")

# 构建标准的 HDFS URL (格式: http://host:port)
# 注意：hdfs.InsecureClient 通常使用 WebHDFS 协议 (HTTP)，端口通常是 9870 (Hadoop 3.x) 或 50070 (Hadoop 2.x)
# 如果你的 9000 是 IPC 端口，InsecureClient 可能连不上。
# 🔥 重要：请确认你的 NameNode WebHDFS 端口。如果是默认 Hadoop 3.x，通常是 9870。
# 这里为了兼容你的配置，先保留 9000，但如果连接失败，请尝试改为 9870 或 50070
WEBHDFS_PORT = int(os.getenv("WEBHDFS_PORT", "9870")) 
HDFS_URL = f"http://{HDFS_HOST}:{WEBHDFS_PORT}"

# ===================== 2. 目录结构配置 (统一命名) =====================
HDFS_ROOT = "/forest"             
HDFS_TASK_ROOT = "/forest/tasks"  
HDFS_RESULTS_ROOT = "/forest/results" 
HDFS_DATA_ROOT = "/forest/data"       # 新增：用于存放原始数据集
HDFS_RASTER_ROOT = "/forest/raster"  # 新增：用于存放遥感影像
HDFS_TEMP_ROOT = "/forest/temp"   

# 本地回退目录
LOCAL_TASK_ROOT = "./data/task"
os.makedirs(LOCAL_TASK_ROOT, exist_ok=True)

# ===================== 3. 客户端初始化 =====================
hdfs_client = None

if HDFS_ENABLED:
    try:
        print(f"🚀 正在初始化 HDFS 客户端...")
        print(f"   URL: {HDFS_URL}")
        print(f"   User: {HDFS_USER}")
        
        # 初始化客户端
        hdfs_client = InsecureClient(HDFS_URL, user=HDFS_USER)
        
        # 测试连接 (检查根目录)
        if hdfs_client.status(HDFS_ROOT, strict=False):
            print(f"✅ HDFS 连接成功！根目录 {HDFS_ROOT} 存在。")
        else:
            print(f"⚠️ HDFS 根目录 {HDFS_ROOT} 不存在，尝试创建...")
            hdfs_client.makedirs(HDFS_ROOT)
            print(f"📁 已创建根目录：{HDFS_ROOT}")

        # 自动创建所有必要的子目录
        required_dirs = [
            HDFS_TASK_ROOT, 
            HDFS_RESULTS_ROOT, 
            HDFS_DATA_ROOT, 
            HDFS_RASTER_ROOT, 
            HDFS_TEMP_ROOT
        ]
        
        created_count = 0
        for dir_path in required_dirs:
            if not hdfs_client.status(dir_path, strict=False):
                hdfs_client.makedirs(dir_path)
                print(f"   📁 创建子目录：{dir_path}")
                created_count += 1
        
        if created_count > 0:
            print(f"✅ 共创建 {created_count} 个新目录。")
        else:
            print("✅ 所有必要目录已存在。")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ HDFS 初始化失败：{error_msg}")
        print("⚠️ 系统将在 3 秒后自动降级为 LOCAL 模式运行。")
        
        # 可选：如果是端口错误，给出提示
        if "Connection refused" in error_msg:
            print(f"💡 提示：连接被拒绝。请检查:")
            print(f"   1. Hadoop NameNode 是否启动？")
            print(f"   2. WebHDFS 端口是否正确？(当前配置: {WEBHDFS_PORT}, 尝试改为 9870 或 50070)")
            print(f"   3. 防火墙是否阻止了连接？")
        
        # 降级处理
        HDFS_ENABLED = False
        hdfs_client = None
        
        # 等待一下让开发者看到日志
        import time
        time.sleep(2)

else:
    print("ℹ️  HDFS 模式已被环境变量禁用，系统将使用 LOCAL 模式。")

# ===================== 4. 导出最终状态 =====================
# 方便其他模块导入时直接判断
SYSTEM_MODE = "HDFS" if HDFS_ENABLED else "LOCAL"
print(f"🌟 当前系统存储模式：【{SYSTEM_MODE}】")

# 如果最终降级了，确保 client 是 None
if not HDFS_ENABLED:
    hdfs_client = None