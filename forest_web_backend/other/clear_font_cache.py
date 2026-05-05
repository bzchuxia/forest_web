import matplotlib
import os
import shutil

# 获取缓存目录路径
cache_dir = matplotlib.get_cachedir()
print(f"📂 正在检查 Matplotlib 缓存目录：{cache_dir}")

if os.path.exists(cache_dir):
    # 遍历删除所有 fontlist 开头的文件
    for file in os.listdir(cache_dir):
        if file.startswith("fontlist"):
            full_path = os.path.join(cache_dir, file)
            try:
                os.remove(full_path)
                print(f"✅ 已删除缓存文件：{full_path}")
            except PermissionError:
                print(f"❌ 无法删除 {full_path}，请关闭所有 Python 进程后手动删除！")
    
    print("\n🎉 缓存清理完成！请务必重启你的后端服务！")
else:
    print("⚠️ 未找到缓存目录。")