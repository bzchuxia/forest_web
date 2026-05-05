from pyspark.sql import SparkSession

# 尝试创建一个简单的 Spark 会话
spark = SparkSession.builder \
    .appName("TestApp") \
    .master("local[*]") \
    .config("spark.driver.host", "127.0.0.1") \
    .config("spark.driver.port", "0") \
    .getOrCreate()

print("✅ Spark 环境配置成功！版本:", spark.version)

# 做一个简单的计算测试
data = [("Alice", 1), ("Bob", 2)]
df = spark.createDataFrame(data, ["Name", "ID"])
df.show()

spark.stop()