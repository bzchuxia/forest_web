from pyspark.sql import SparkSession
from pyspark import SparkConf
import logging
import os
import json
import time

# ===================== Windows 环境兼容配置 =====================
os.environ['HADOOP_USER_NAME'] = 'root'

if 'HADOOP_CONF_DIR' in os.environ:
    del os.environ['HADOOP_CONF_DIR']

os.environ['HADOOP_HOME'] = r'F:\hadoop-3.1.3'
os.environ['PATH'] = os.path.join(os.environ['HADOOP_HOME'], 'bin') + os.pathsep + os.environ['PATH']

# ===================== Spark 引擎（只读取单个栅格文件） =====================
class SparkEngine:
    def __init__(self):
        self.spark = None
        self.is_available = False

    def init_spark(self):
        if self.spark is not None:
            return

        try:
            conf = SparkConf()
            conf.set("spark.driver.host", "127.0.0.1")
            conf.set("spark.hadoop.io.native.lib.available", "false")
            conf.set("spark.rpc.message.maxSize", "256")
            conf.set("spark.driver.maxResultSize", "2g")

            self.spark = SparkSession.builder \
                .appName("ForestRasterViewer") \
                .config(conf=conf) \
                .getOrCreate()

            self.spark.sparkContext.setLogLevel("WARN")
            self.is_available = True
            logging.info("✅ Spark 栅格数据引擎启动成功")

        except Exception as e:
            logging.error(f"❌ Spark 启动失败: {str(e)}")
            self.is_available = False

    def get_single_raster_info(self, file_path: str):
        """
        只做一件事：获取单个 TIFF 文件的信息，不遍历目录
        """
        try:
            hadoop = self.spark._jvm.org.apache.hadoop
            conf = self.spark._jsc.hadoopConfiguration()
            Path = hadoop.fs.Path
            fs = Path(file_path).getFileSystem(conf)

            status = fs.getFileStatus(Path(file_path))
            return {
                "file_name": status.getPath().getName(),
                "size_bytes": status.getLen(),
                "size_mb": round(status.getLen() / 1024 / 1024, 2),
                "modify_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(status.getModificationTime() / 1000)),
                "path": str(status.getPath())
            }
        except Exception as e:
            logging.error(f"❌ 获取文件信息失败: {str(e)}")
            return None

    def query_data(self, sql_query: str = None) -> str:
        """
        对外接口：直接返回你指定的栅格文件信息
        你可以在这里写死文件路径，或者根据前端请求动态指定
        """
        try:
            if self.spark is None:
                self.init_spark()

            if not self.is_available:
                return json.dumps({"status": "error", "message": "Spark 未启动"}, ensure_ascii=False)

            # 直接指定你要读取的 TIFF 文件路径（替换成你需要的文件）
            target_file = "hdfs://localhost:9870/forest/raster/DEM.tif"
            file_info = self.get_single_raster_info(target_file)

            if not file_info:
                return json.dumps({"status": "error", "message": "获取文件信息失败"}, ensure_ascii=False)

            return json.dumps({
                "status": "success",
                "total_count": 1,
                "raster_file": file_info,
                "message": "成功读取指定栅格文件"
            }, ensure_ascii=False)

        except Exception as e:
            err = str(e)
            logging.error(f"❌ 查询失败: {err}")
            return json.dumps({
                "status": "error",
                "message": f"获取栅格数据失败: {err}"
            }, ensure_ascii=False)

    def stop(self):
        try:
            if self.spark is not None:
                self.spark.stop()
            logging.info("✅ Spark 已安全关闭")
        except:
            pass

# ===================== 全局单例 =====================
spark_engine = SparkEngine()