# -*- coding: utf-8 -*-
"""
生物量预测模型训练模块（智能自适应版）
核心变更：
1. 【智能】自动判断是否需要 log 变换（基于偏度）
2. 【简化】移除复杂正则化，回归基础模型
3. 【恢复】轻量级特征重要性分析（不剔除特征）
4. 【加速】Stacking 和 RF 使用默认参数，快速收敛
5. 保持前后端接口数据结构完全一致
"""
import pandas as pd
import time
import shap
import os
import sys
import tempfile
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import StackingRegressor, RandomForestRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor, ExtraTreesRegressor
from xgboost import XGBRegressor
from sklearn.linear_model import LassoCV, Lasso, RidgeCV
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.preprocessing import StandardScaler
from scipy.stats import skew
import warnings
import re
from hdfs import InsecureClient
from app.core.config import settings

# ===================== 基础配置 =====================
class MockSettings:
    BASE_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../data")
    DEFAULT_OUTPUT_DIR = os.path.join(BASE_DATA_DIR, "biomass_results")
    DEFAULT_INPUT_FILE = os.path.join(BASE_DATA_DIR, "111.xlsx")

try:
    from app.core.config import settings
    if not hasattr(settings, 'BASE_DATA_DIR'):
        settings.BASE_DATA_DIR = MockSettings.BASE_DATA_DIR
    if not hasattr(settings, 'DEFAULT_OUTPUT_DIR'):
        settings.DEFAULT_OUTPUT_DIR = MockSettings.DEFAULT_OUTPUT_DIR
except ImportError:
    settings = MockSettings()

# ===================== HDFS 上传工具 =====================
def get_hdfs_client():
    hdfs_url = f"http://{settings.HDFS_HOST}:{settings.HDFS_PORT}"
    return InsecureClient(hdfs_url, user=settings.HDFS_USER)

def upload_to_hdfs(local_path, hdfs_relative_path):
    try:
        client = get_hdfs_client()
        hdfs_path = f"/forest/results/result/{hdfs_relative_path.lstrip('/')}"
        hdfs_dir = os.path.dirname(hdfs_path)
        client.makedirs(hdfs_dir)
        client.upload(hdfs_path, local_path, overwrite=True)
        print(f"✅ HDFS 上传成功: {hdfs_path}")
        return hdfs_path
    except Exception as e:
        print(f"❌ HDFS 上传失败: {e}")
        return None
# ===================== 全局配置 =====================
warnings.filterwarnings('ignore')
plt.rcParams['font.family'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300

TIMESTAMP_PATTERN = re.compile(r'^\d{8}_\d{6}$')

# ===================== 工具函数 =====================
def validate_and_format_timestamp(timestamp: str) -> str:
    if not isinstance(timestamp, str):
        raise ValueError(f"时间戳必须为字符串类型")
    clean_ts = timestamp.replace("_", "")
    if len(clean_ts) == 14 and clean_ts.isdigit():
        timestamp = f"{clean_ts[:8]}_{clean_ts[8:]}"
    if not TIMESTAMP_PATTERN.match(timestamp):
        raise ValueError(f"时间戳格式错误！")
    return timestamp

def resolve_local_path(file_path: str, file_type: str = "data", timestamp: str = "") -> str:
    if file_path.startswith("dataset://"):
        dataset_id = file_path.replace("dataset://", "")
        dataset_mapping = {"default": os.path.join(settings.BASE_DATA_DIR, "111.xlsx")}
        return dataset_mapping.get(dataset_id, os.path.join(settings.BASE_DATA_DIR, f"{dataset_id}.xlsx"))
    
    if file_path.startswith("/data/"):
        local_path = file_path.replace("/data/", settings.BASE_DATA_DIR + "/", 1)
        local_path = os.path.normpath(local_path)
        if file_type == "output":
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
        return local_path
    
    if not os.path.isabs(file_path):
        if file_type == "output":
            local_path = os.path.join(settings.BASE_DATA_DIR, file_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            return local_path
        else:
            if os.path.exists(file_path):
                return os.path.abspath(file_path)
            return os.path.join(settings.BASE_DATA_DIR, file_path)
    
    if file_type == "output":
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    return file_path

def convert_abs_to_virtual_path(abs_path: str) -> str:
    if not abs_path:
        return ""
    base_dir = os.path.normpath(settings.BASE_DATA_DIR)
    abs_path = os.path.normpath(abs_path)
    if abs_path.startswith(base_dir):
        return abs_path.replace(base_dir, "/data", 1)
    return abs_path

def log_execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"⏱️ {func.__name__} 执行时间：{end_time - start_time:.2f} 秒")
        if isinstance(result, dict):
            result['train_time'] = end_time - start_time
        return result
    return wrapper

# ===================== 模型保存函数 =====================
def save_model_and_features(model, features, model_name, output_dir, timestamp):
    model_filename = f"{model_name}_model_{timestamp}.joblib"
    model_abs_path = os.path.join(output_dir, model_filename)
    joblib.dump(model, model_abs_path)
    
    feat_filename = f"{model_name}_feature_list_{timestamp}.joblib"
    feat_abs_path = os.path.join(output_dir, feat_filename)
    joblib.dump(features, feat_abs_path)
    
    model_virtual_path = convert_abs_to_virtual_path(model_abs_path)
    feat_virtual_path = convert_abs_to_virtual_path(feat_abs_path)

    # ===================== 上传 HDFS =====================
    hdfs_model = upload_to_hdfs(model_abs_path, f"{timestamp}/{model_filename}")
    hdfs_feat = upload_to_hdfs(feat_abs_path, f"{timestamp}/{feat_filename}")
    
    print(f"✅ 保存 {model_name} 完成（本地+HDFS）")
    return {
        "model_abs_path": model_abs_path,
        "model_virtual_path": model_virtual_path,
        "feat_abs_path": feat_abs_path,
        "feat_virtual_path": feat_virtual_path,
        "hdfs_model_path": hdfs_model,
        "hdfs_feat_path": hdfs_feat
    }

# ===================== 数据增强函数 =====================
def data_augmentation(X, y, augment_times=2, random_state=42):
    np.random.seed(random_state)
    X_aug = X.copy()
    y_aug = y.copy()
    
    for _ in range(augment_times):
        noise = np.random.normal(0, 0.01, X.shape)
        X_noisy = X + noise
        X_aug = pd.concat([X_aug, X_noisy], axis=0)
        y_aug = pd.concat([y_aug, y], axis=0)
    
    X_aug = X_aug.reset_index(drop=True)
    y_aug = y_aug.reset_index(drop=True)
    print(f"✅ 数据增强完成：{len(X)} → {len(X_aug)} 样本")
    return X_aug, y_aug

# ===================== VIF 计算函数 =====================
def calculate_vif(X):
    if not isinstance(X, pd.DataFrame):
        X = pd.DataFrame(X)
    vif_data = pd.DataFrame()
    vif_data["feature"] = X.columns
    try:
        corr_matrix = X.corr()
        inv_corr_matrix = pd.DataFrame(
            np.linalg.pinv(corr_matrix.values),
            index=corr_matrix.index,
            columns=corr_matrix.columns
        )
        vif_data["VIF"] = [inv_corr_matrix.iloc[i, i] for i in range(X.shape[1])]
        return vif_data.sort_values('VIF', ascending=False)
    except Exception as e:
        return pd.DataFrame(columns=["feature", "VIF"])

# ===================== 可视化函数 =====================
def plot_model_results(results_dict, y_test, process_data, output_dir, timestamp):
    """
    综合绘图函数（修正 subplot 调用方式 + 统一 GridSpec 布局）
    返回值：主对比图的路径（字符串）
    """
    import os
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import shap
    from matplotlib import gridspec  # 导入 gridspec

    print("\n==================== 正在生成详细分析图 ====================")

    model_names = list(results_dict.keys())
    n_values = process_data['n_values']
    r2_records = process_data['r2_records']
    rmse_records = process_data['rmse_records']

    # --- 1. 绘制 RMSE 变化曲线 ---
    fig = plt.figure(figsize=(20, 18))
    gs = gridspec.GridSpec(3, len(model_names), figure=fig, hspace=0.3, wspace=0.3)  # 统一布局

    # 绘制 RMSE 曲线（占满第一行所有列）
    ax_rmse = fig.add_subplot(gs[0, :])
    for name, (rmse_list, color) in rmse_records.items():
        ax_rmse.plot(n_values, rmse_list, label=f"{name}", color=color, linewidth=2)
    ax_rmse.set_xlabel("n_estimators", fontsize=12)
    ax_rmse.set_ylabel("RMSE", fontsize=12)
    ax_rmse.set_title("不同模型在不同 n_estimators 下的 RMSE 比较", fontsize=14, fontweight='bold')
    ax_rmse.legend()
    ax_rmse.grid(True, linestyle='--', alpha=0.3)

    # --- 2. 绘制拟合效果图（散点图，每个模型一个子图） ---
    for i, name in enumerate(model_names):
        res = results_dict[name]
        y_pred = res['predictions']
        color = res.get('color', 'blue')

        ax_fit = fig.add_subplot(gs[1, i])  # 第二行，第 i 列
        ax_fit.scatter(y_test, y_pred, alpha=0.6, color=color, edgecolors='black', s=40)

        # 拟合线（确保 coef 是标量）
        coef = np.polyfit(y_test, y_pred, 1)
        fit_line = np.poly1d(coef)
        y_fit = fit_line(y_test)

        # 修正：用 coef[0] 和 coef[1] 分别取斜率和截距
        ax_fit.plot(y_test, y_fit, '-', color='red', label=f'拟合线: y={coef[0]:.2f}x+{coef[1]:.2f}')
        ax_fit.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'k--', label="1:1 Line")

        ax_fit.set_xlabel("真实值")
        ax_fit.set_ylabel("预测值")
        ax_fit.set_title(f"{name}\nR²={res['r2']:.4f}", fontsize=12)
        ax_fit.legend(fontsize=8)

    # --- 3. 绘制指标对比柱状图（R²、RMSE、MAE，每个指标一个子图） ---
    colors_list = [results_dict[m].get('color', 'gray') for m in model_names]

    # R² 柱状图（第三行第 0 列）
    ax_r2 = fig.add_subplot(gs[2, 0])
    r2_vals = [results_dict[m]['r2'] for m in model_names]
    ax_r2.bar(model_names, r2_vals, color=colors_list, edgecolor='black')
    ax_r2.set_ylabel("R²")
    ax_r2.set_title("R² 对比")
    ax_r2.set_ylim(0, 1.1)
    for i, v in enumerate(r2_vals):
        ax_r2.text(i, v + 0.02, f'{v:.3f}', ha='center', fontsize=10)

    # RMSE 柱状图（第三行第 1 列）
    ax_rmse_bar = fig.add_subplot(gs[2, 1])
    rmse_vals = [results_dict[m]['rmse'] for m in model_names]
    ax_rmse_bar.bar(model_names, rmse_vals, color=colors_list, edgecolor='black')
    ax_rmse_bar.set_ylabel("RMSE")
    ax_rmse_bar.set_title("RMSE 对比")
    for i, v in enumerate(rmse_vals):
        ax_rmse_bar.text(i, v + max(rmse_vals)*0.01, f'{v:.3f}', ha='center', fontsize=10)

    # MAE 柱状图（第三行第 2 列）
    ax_mae = fig.add_subplot(gs[2, 2])
    mae_vals = [results_dict[m]['mae'] for m in model_names]
    ax_mae.bar(model_names, mae_vals, color=colors_list, edgecolor='black')
    ax_mae.set_ylabel("MAE")
    ax_mae.set_title("MAE 对比")
    for i, v in enumerate(mae_vals):
        ax_mae.text(i, v + max(mae_vals)*0.01, f'{v:.3f}', ha='center', fontsize=10)

    # 如果模型数量少于 3 个，隐藏多余的空位（可选）
    if len(model_names) < 3:
        # 简单处理：只画存在的模型，多余的列留白
        pass

    plt.suptitle(f"模型训练分析报告 - {timestamp}", fontsize=16, fontweight='bold', y=0.995)

    # 保存图片
    plot_filename = f"详细分析图_{timestamp}.png"
    plot_path = os.path.join(output_dir, plot_filename)

    try:
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"📊 详细分析图已保存至: {plot_path}")
        return convert_abs_to_virtual_path(plot_path)
    except Exception as e:
        print(f"❌ 保存图片失败: {e}")
        return None
    finally:
        plt.close(fig)

# ===================== 模型函数 1：Stacking 集成 =====================
@log_execution_time
def train_stacking_model(X_train, y_train, X_test, y_test, random_state=42):
    print("\n=== 开始训练 Stacking 集成模型 ===")
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    base_models = [
        ('rf', RandomForestRegressor(n_estimators=100, random_state=random_state, n_jobs=-1)),
        ('gbrt', GradientBoostingRegressor(n_estimators=100, random_state=random_state)),
        ('hgb', HistGradientBoostingRegressor(random_state=random_state))
    ]
    meta_model = LassoCV(cv=5, random_state=random_state, max_iter=5000)
    
    stacking_model = StackingRegressor(
        estimators=base_models,
        final_estimator=meta_model,
        cv=5,
        n_jobs=-1
    )
    
    stacking_model.fit(X_train_scaled, y_train)
    final_pred = stacking_model.predict(X_test_scaled)
    
    r2 = r2_score(y_test, final_pred)
    rmse = np.sqrt(mean_squared_error(y_test, final_pred))
    mae = mean_absolute_error(y_test, final_pred)
    
    print(f"✅ Stacking 模型完成 | R²: {r2:.4f}")
    
    return {
        'model': stacking_model,
        'predictions': final_pred.tolist(),
        'r2': float(r2),
        'rmse': float(rmse),
        'mae': float(mae),
        'selected_features': X_train.columns.tolist(),
    }

# ===================== 模型函数 2：基线 RF =====================
@log_execution_time
def train_baseline_rf(X_train, y_train, X_test, y_test, n_estimators_range=range(50, 150, 10), random_state=42):
    print("\n=== 开始训练基线 RF 模型 ===")
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    best_rmse = np.inf
    best_n = 100
    best_model = None
    best_pred = None
    
    search_range = list(n_estimators_range)
    if len(search_range) > 10:
        search_range = search_range[::2]

    for n in search_range:
        rf = RandomForestRegressor(n_estimators=n, random_state=random_state, n_jobs=-1)
        rf.fit(X_train_scaled, y_train)
        pred = rf.predict(X_test_scaled)
        rmse = np.sqrt(mean_squared_error(y_test, pred))
        
        if rmse < best_rmse:
            best_rmse = rmse
            best_n = n
            best_model = rf
            best_pred = pred
    
    r2 = r2_score(y_test, best_pred)
    mae = mean_absolute_error(y_test, best_pred)
    
    print(f"✅ 基线 RF 完成 | 最优 n={best_n} | R²: {r2:.4f}")
    
    return {
        'model': best_model,
        'predictions': best_pred.tolist(),
        'r2': float(r2),
        'rmse': float(best_rmse),
        'mae': float(mae),
        'best_n': best_n,
        'selected_features': X_train.columns.tolist(),
    }

# ===================== 统一调度函数 =====================
def run_all_models(X_train, y_train, X_test, y_test, output_dir, timestamp, random_state=42):
    print("\n==================== 开始运行所有模型 (新版逻辑) ====================")
    
    # 1. 设定模型和颜色
    model_classes = {
        "RandomForest": (RandomForestRegressor, 'blue'),
        "ExtraTrees": (ExtraTreesRegressor, 'green'),  
        "XGBoost": (XGBRegressor, 'orange'),  
        "GBRT": (GradientBoostingRegressor, 'purple')
    }

    # 2. n_estimators 范围
    n_values = list(range(10, 201, 10)) 

    # 3. 存储结果
    best_results = {}
    # 新增：用于存储绘图所需的过程数据
    process_data = {
        'n_values': n_values,
        'r2_records': {},
        'rmse_records': {}
    }

    # 4. 遍历每个模型进行测试
    for name, (ModelClass, color) in model_classes.items():
        best_rmse = np.inf
        best_n = None
        best_pred = None
        best_r2 = 0
        best_mae = 0
        best_model = None
        
        # 记录当前模型在不同 n 下的表现
        current_r2_list = []
        current_rmse_list = []

        for n in n_values:
            try:
                if name == "XGBoost":  
                    model = ModelClass(n_estimators=n, random_state=random_state, verbosity=0)
                else:
                    model = ModelClass(n_estimators=n, random_state=random_state)
                
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                
                # 计算指标
                r2 = r2_score(y_test, y_pred)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                
                # 记录过程数据
                current_r2_list.append(r2)
                current_rmse_list.append(rmse)

                # 如果当前 RMSE 更低，则更新最佳结果
                if rmse < best_rmse:
                    best_rmse = rmse
                    best_n = n
                    best_pred = y_pred.copy()
                    best_r2 = r2
                    best_mae = mean_absolute_error(y_test, y_pred)
                    best_model = model

            except Exception as e:
                print(f"❌ {name} 在 n={n} 时训练失败：{e}")
                continue

        # 保存过程数据用于绘图
        process_data['r2_records'][name] = (current_r2_list, color)
        process_data['rmse_records'][name] = (current_rmse_list, color)

        # 确保至少有一个模型训练成功
        if best_model is not None:
            best_results[name] = {
                'best_r2': best_r2,
                'best_n': best_n,
                'best_rmse': best_rmse,
                'best_mae': best_mae,
                'y_pred': best_pred,
                'model': best_model,
                'color': color
            }
            print(f"✅ {name} 训练完成 - 最佳 n: {best_n}, R²: {best_r2:.4f}, RMSE: {best_rmse:.4f}")
        else:
            print(f"❌ {name} 所有参数尝试均失败")

    if not best_results:
        raise RuntimeError("所有模型训练均失败")

    # ============================================================
    # 5. 构建兼容旧逻辑的 results 字典
    # ============================================================
    results = {}
    for name, res in best_results.items():
        results[name] = {
            'model': res['model'],
            'predictions': res['y_pred'].tolist(),
            'r2': float(res['best_r2']),
            'rmse': float(res['best_rmse']),
            'mae': float(res['best_mae']),
            'selected_features': X_train.columns.tolist(), 
            'train_time': 0 
        }

    # 6. 保存模型文件
    model_files = {}
    for model_name, res in results.items():
        save_result = save_model_and_features(
            model=res['model'],
            features=res['selected_features'],
            model_name=model_name,
            output_dir=output_dir,
            timestamp=timestamp
        )
        model_files[model_name] = save_result

    # 7. 生成对比图 (传入 y_test 和 process_data)
    comparison_plot = plot_model_results(
        results, 
        y_test, 
        process_data, 
        output_dir, 
        timestamp
    )

    # 8. 确定最佳模型
    valid_results = {k: v for k, v in results.items() if 'r2' in v}
    best_model_name = max(valid_results.keys(), key=lambda k: valid_results[k]['r2'])

    # 9. 构建最终返回的 summary
    summary = {
        'all_results': results,
        'best_model_name': best_model_name,
        'best_model': {
            'r2': valid_results[best_model_name]['r2'],
            'rmse': valid_results[best_model_name]['rmse'],
            'mae': valid_results[best_model_name]['mae'],
            'selected_features': valid_results[best_model_name]['selected_features']
        },
        'best_model_files': model_files[best_model_name],
        'all_model_files': model_files,
        'comparison_plot': comparison_plot,
        'timestamp': timestamp,
        'model_metrics': {
            name: {
                'r2': res['r2'],
                'rmse': res['rmse'],
                'mae': res['mae'],
                'train_time': res.get('train_time', 0)
            } for name, res in valid_results.items()
        }
    }

    print(f"\n🏆 最优模型：{summary['best_model_name']} (R²: {summary['best_model']['r2']:.4f})")
    return summary

# ===================== 核心业务函数 =====================
@log_execution_time
def run_biomass_prediction(params: dict):
    temp_dir = None
    try:
        timestamp = params.get("timestamp")
        if not timestamp:
            raise ValueError("❌ 未传入前端时间戳")
        timestamp = validate_and_format_timestamp(timestamp)
        print(f"\n🚀 生物量预测任务启动 - 时间戳：{timestamp}")
        
        input_path = params.get("input_path", os.path.join(settings.BASE_DATA_DIR, "111.xlsx"))
        base_output_dir = settings.DEFAULT_OUTPUT_DIR
        output_dir = os.path.join(base_output_dir, timestamp)
        input_path = resolve_local_path(input_path, "data", timestamp)
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在：{input_path}")
        
        os.makedirs(output_dir, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix=f"biomass_train_{timestamp}_")
        
        print(f"📂 加载数据：{input_path}")
        df = pd.read_excel(input_path)
        original_count = len(df)
        print(f"原始数据量：{original_count} 条")

        y = df['AGB']
        X_raw = df.drop(columns=['AGB'])
        base_seed = 42
        n_iterations = 100

        # 初始化用于保存每次的重要性
        importance_matrix = pd.DataFrame(0.0, index=range(n_iterations), columns=X_raw.columns)
        
        # C. 列名标准化
        rename_mapping = {'podu': 'Slope', 'poxiang': 'Aspect', 'vv_VH': 'VV/VH', 'radar': '(VV-VH)/(VV+VH)'}
        X = X_raw.rename(columns={k: v for k, v in rename_mapping.items() if k in X_raw.columns})
        
        for i in range(n_iterations):
            rf = RandomForestRegressor(n_estimators=100, random_state=base_seed + i)
            rf.fit(X, y)
            importance_matrix.loc[i] = rf.feature_importances_

        # 计算平均特征重要性
        mean_importance = importance_matrix.mean().sort_values(ascending=False)

        # 选出前10个重要特征
        top_features = mean_importance.head(10)
        print("100次随机森林平均重要性前10的特征：")
        print(top_features)

        # 提取前10个特征的数据
        X_selected = X[top_features.index]
        X_train, X_test, y_train, y_test = train_test_split(X_selected, y, test_size=0.2, random_state=639)
        
        # 运行模型
        model_summary = run_all_models(
            X_train, y_train, X_test, y_test,
            output_dir, timestamp,
            random_state=42
        )

        
        # 8. 保存结果 CSV
        print("\n保存结果文件...")
        predictions_data = {'真实值_AGB': y_test.reset_index(drop=True)}
        for name, res in model_summary['all_results'].items():
            predictions_data[f'{name}_预测值_AGB'] = res['predictions']
            
        predictions_df = pd.DataFrame(predictions_data)
        pred_path = os.path.join(output_dir, f"所有模型预测结果_{timestamp}.csv")
        predictions_df.to_csv(pred_path, index=False, encoding='utf-8-sig')
        
        metrics_data = []
        for name, res in model_summary['all_results'].items():
            metrics_data.append({
                '模型名称': name,
                'R²': res['r2'],
                'RMSE': res['rmse'],
                'MAE': res['mae'],
                '特征数': len(res['selected_features']),
                '耗时 (s)': round(res.get('train_time', 0), 2)
            })
        metrics_df = pd.DataFrame(metrics_data)
        metrics_path = os.path.join(output_dir, f"模型评价指标汇总_{timestamp}.csv")
        metrics_df.to_csv(metrics_path, index=False, encoding='utf-8-sig')
        
        # ===================== 上传结果到 HDFS =====================
        upload_to_hdfs(pred_path, f"{timestamp}/所有模型预测结果_{timestamp}.csv")
        upload_to_hdfs(metrics_path, f"{timestamp}/模型评价指标汇总_{timestamp}.csv")
        if model_summary.get('comparison_plot'):
            plot_local = resolve_local_path(model_summary['comparison_plot'], 'data')
            upload_to_hdfs(plot_local, f"{timestamp}/详细分析图_{timestamp}.png")

        # 9. 构建返回结果
        model_metrics_list = [
            {
                "模型名称": name,
                "R²": float(res['r2']),
                "RMSE": float(res['rmse']),
                "MAE": float(res['mae']),
                "使用的特征数": len(res['selected_features']),
                "耗时 (s)": float(res.get('train_time', 0))
            } for name, res in model_summary['all_results'].items()
        ]

        total_feature_count = len(X.columns)
        train_samples_count = int(len(X_train))
        test_samples_count = int(len(X_test))
        
        result = {
            "status": "success",
            "timestamp": timestamp,
            "best_model_name": model_summary['best_model_name'],
            "best_r2": float(model_summary['best_model']['r2']),
            "best_rmse": float(model_summary['best_model']['rmse']),
            "best_mae": float(model_summary['best_model']['mae']),
            "feature_count": total_feature_count,
            "train_samples": train_samples_count,
            "test_samples": test_samples_count,
            "data_cleaning_info": {
                "original_count": original_count,
                "final_count": len(y),
                "removed_outliers": original_count - len(y)
            },
            "best_model": model_summary['best_model_name'],
            "model_metrics": model_metrics_list,
            "all_models": {
                name: {
                    "model_path": files['model_virtual_path'],
                    "feature_list_path": files['feat_virtual_path'],
                    "r2": float(model_summary['model_metrics'].get(name, {}).get('r2', 0.0)),
                    "rmse": float(model_summary['model_metrics'].get(name, {}).get('rmse', 0.0)),
                } for name, files in model_summary['all_model_files'].items()
            },
            "best_model_info": {
                "model_name": model_summary['best_model_name'],
                "model_path": model_summary['best_model_files']['model_virtual_path'],
                "feature_list_path": model_summary['best_model_files']['feat_virtual_path'],
                "r2": float(model_summary['best_model']['r2']),
                "rmse": float(model_summary['best_model']['rmse']),
                "feature_count": int(len(model_summary['best_model']['selected_features']))
            },
            "output_files": {
                "predictions_csv": convert_abs_to_virtual_path(pred_path),
                "metrics_csv": convert_abs_to_virtual_path(metrics_path),
                "best_model": model_summary['best_model_files']['model_virtual_path'],
                "comparison_plot": model_summary['comparison_plot'],
            },
            "statistics": {
                "feature_count": total_feature_count,
                "train_samples": train_samples_count,
                "test_samples": test_samples_count,
                "min_biomass": float(np.min(y_test)),
                "max_biomass": float(np.max(y_test)),
                "avg_biomass": float(np.mean(y_test))
            }
        }

        # 序列化清理
        def filter_serializable(data):
            if isinstance(data, dict):
                return {k: filter_serializable(v) for k, v in data.items() 
                        if k not in ['model', 'scaler', 'boruta', 'explainer', 'base_models', 'meta_model']}
            elif isinstance(data, (np.ndarray, list)):
                return [filter_serializable(i) for i in data] if isinstance(data, list) else data.tolist()
            elif isinstance(data, (np.floating, np.float64, np.float32)):
                return float(data)
            elif isinstance(data, (np.integer, np.int64, np.int32)):
                return int(data)
            else:
                return data if isinstance(data, (int, float, str, bool, type(None))) else str(data)
        
        result = filter_serializable(result)
        
        print(f"\n🎉 优化完成！最优模型 R²：{result['best_r2']:.4f}")
        return result
        
    except Exception as e:
        error_msg = f"❌ 执行失败：{str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            "status": "failed",
            "error": error_msg,
            "timestamp": params.get("timestamp", "")
        }
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                pass

# ===================== 测试入口 =====================
if __name__ == "__main__":
    test_input = r"D:\\desktop\\forest_web\\forest_web_backend\\data\\111.xlsx"
    if not os.path.exists(test_input):
        test_input = os.path.join(settings.BASE_DATA_DIR, "111.xlsx")
        
    test_params = {
        "input_path": test_input,
        "test_size": 0.2,
        "random_state": 42,
        "timestamp": "20260326_140000"
    }
    
    print(f"🚀 开始本地测试，输入文件：{test_params['input_path']}")
    
    if not os.path.exists(test_params['input_path']):
        print(f"❌ 测试文件不存在：{test_params['input_path']}")
        sys.exit(1)
        
    result = run_biomass_prediction(test_params)
    
    if result["status"] == "success":
        print(f"\n✅ 测试成功！")
        print(f"🏆 最优模型：{result['best_model_info']['model_name']} (R²={result['best_r2']:.4f})")
        print(f"📂 输出目录：{settings.DEFAULT_OUTPUT_DIR}/{result['timestamp']}")
    else:
        print(f"\n❌ 测试失败：{result['error']}")
        sys.exit(1)