from hdfs import InsecureClient
from app.core.config import settings

HDFS_CLIENT = InsecureClient('http://localhost:9870', user='hadoop')

def hdfs_exists(path: str) -> bool:
    return HDFS_CLIENT.status(path, strict=False) is not None

def hdfs_read_file(path: str):
    with HDFS_CLIENT.read(path, encoding='utf-8') as f:
        return f.read()

def hdfs_download_file(hdfs_path: str, local_path: str):
    HDFS_CLIENT.download(hdfs_path, local_path, overwrite=True)

def hdfs_list_files(path: str) -> list:
    return HDFS_CLIENT.list(path)