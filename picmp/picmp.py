#!/usr/bin/env python3
"""picmp - 图像质量对比工具

用法:
  单张对比: python picmp.py img_a.png img_b.png [-o output_dir]
  批量对比: python picmp.py --batch dir_a/ dir_b/ [-o output_dir]
"""

import argparse
import base64
import csv
import json
import math
import os
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from skimage.metrics import structural_similarity

# 支持的图像格式
SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

# 配置文件路径（与脚本同目录）
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """加载配置文件，不存在则返回空字典。"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ============================================================
# 1. 图像读取与校验
# ============================================================

def read_image(path: str) -> np.ndarray:
    """读取图像，返回 BGR numpy 数组。失败则退出。"""
    p = Path(path)
    if not p.exists():
        print(f"错误: 文件不存在 - {path}", file=sys.stderr)
        sys.exit(1)
    if p.suffix.lower() not in SUPPORTED_EXTS:
        print(f"错误: 不支持的格式 '{p.suffix}' - {path}", file=sys.stderr)
        sys.exit(1)
    img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"错误: 无法读取图像 - {path}", file=sys.stderr)
        sys.exit(1)
    return img


def check_size_match(img_a: np.ndarray, img_b: np.ndarray, path_a: str, path_b: str):
    """检查两张图尺寸是否一致。"""
    if img_a.shape != img_b.shape:
        print(
            f"错误: 图像尺寸不匹配\n"
            f"  {path_a}: {img_a.shape[1]}x{img_a.shape[0]} ({img_a.shape[2] if len(img_a.shape) > 2 else 1}ch)\n"
            f"  {path_b}: {img_b.shape[1]}x{img_b.shape[0]} ({img_b.shape[2] if len(img_b.shape) > 2 else 1}ch)",
            file=sys.stderr,
        )
        sys.exit(1)


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """转换为灰度图。"""
    if len(img.shape) == 2:
        return img
    if img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def ensure_bgr(img: np.ndarray) -> np.ndarray:
    """确保图像为 3 通道 BGR。"""
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


# ============================================================
# 2. 指标计算
# ============================================================

def calc_mse(img_a: np.ndarray, img_b: np.ndarray) -> float:
    """计算 MSE (Mean Squared Error)。"""
    diff = img_a.astype(np.float64) - img_b.astype(np.float64)
    return float(np.mean(diff ** 2))


def calc_mae(img_a: np.ndarray, img_b: np.ndarray) -> float:
    """计算 MAE (Mean Absolute Error)。"""
    diff = img_a.astype(np.float64) - img_b.astype(np.float64)
    return float(np.mean(np.abs(diff)))


def calc_psnr(img_a: np.ndarray, img_b: np.ndarray) -> float:
    """计算 PSNR。相同图像返回 inf。"""
    mse = calc_mse(img_a, img_b)
    if mse == 0:
        return float("inf")
    max_pixel = 255.0
    return float(10 * math.log10((max_pixel ** 2) / mse))


def calc_ssim(gray_a: np.ndarray, gray_b: np.ndarray):
    """计算 SSIM，返回 (score, ssim_map)。"""
    score, ssim_map = structural_similarity(gray_a, gray_b, full=True)
    return float(score), ssim_map.astype(np.float64)


def calc_histogram_correlation(img_a: np.ndarray, img_b: np.ndarray) -> dict:
    """计算 BGR 各通道直方图相关性。"""
    a_bgr = ensure_bgr(img_a)
    b_bgr = ensure_bgr(img_b)
    channels = {"B": 0, "G": 1, "R": 2}
    result = {}
    for name, idx in channels.items():
        hist_a = cv2.calcHist([a_bgr], [idx], None, [256], [0, 256])
        hist_b = cv2.calcHist([b_bgr], [idx], None, [256], [0, 256])
        cv2.normalize(hist_a, hist_a)
        cv2.normalize(hist_b, hist_b)
        corr = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
        result[name] = round(float(corr), 6)
    return result


def calc_pixel_diff_percent(img_a: np.ndarray, img_b: np.ndarray, threshold: int = 1) -> float:
    """计算超过阈值的像素差异百分比。"""
    diff = np.abs(img_a.astype(np.int16) - img_b.astype(np.int16))
    if len(diff.shape) == 3:
        diff = np.max(diff, axis=2)  # 任意通道超过阈值即算
    num_diff = np.count_nonzero(diff > threshold)
    total = diff.shape[0] * diff.shape[1]
    return round(float(num_diff / total * 100), 4)


def compute_all_metrics(img_a: np.ndarray, img_b: np.ndarray, thresholds: list = None) -> dict:
    """计算所有指标，返回指标字典和 ssim_map。"""
    if thresholds is None:
        thresholds = [1, 5, 10]
    gray_a = to_grayscale(img_a)
    gray_b = to_grayscale(img_b)
    ssim_score, ssim_map = calc_ssim(gray_a, gray_b)
    hist_corr = calc_histogram_correlation(img_a, img_b)

    metrics = {
        "PSNR (dB)": calc_psnr(img_a, img_b),
        "SSIM": ssim_score,
        "MSE": calc_mse(img_a, img_b),
        "MAE": calc_mae(img_a, img_b),
        "Histogram Corr (B)": hist_corr["B"],
        "Histogram Corr (G)": hist_corr["G"],
        "Histogram Corr (R)": hist_corr["R"],
    }
    for t in thresholds:
        metrics[f"Pixel Diff % (thr={t})"] = calc_pixel_diff_percent(img_a, img_b, threshold=t)

    return metrics, ssim_map


# ============================================================
# 3. 差异图生成
# ============================================================

def generate_diff_heatmap(img_a: np.ndarray, img_b: np.ndarray, out_path: str):
    """生成差异热力图 (蓝=小差异, 红=大差异)。"""
    a_bgr = ensure_bgr(img_a).astype(np.float64)
    b_bgr = ensure_bgr(img_b).astype(np.float64)
    diff = np.mean(np.abs(a_bgr - b_bgr), axis=2)
    # 归一化到 0-255
    if diff.max() > 0:
        diff_norm = (diff / diff.max() * 255).astype(np.uint8)
    else:
        diff_norm = diff.astype(np.uint8)
    heatmap = cv2.applyColorMap(diff_norm, cv2.COLORMAP_JET)
    cv2.imwrite(out_path, heatmap)


def generate_amplified_diff(img_a: np.ndarray, img_b: np.ndarray, out_path: str, factor: int = 10):
    """生成放大差异图 (差值 × factor)。"""
    a_bgr = ensure_bgr(img_a).astype(np.float64)
    b_bgr = ensure_bgr(img_b).astype(np.float64)
    diff = np.abs(a_bgr - b_bgr) * factor
    diff = np.clip(diff, 0, 255).astype(np.uint8)
    cv2.imwrite(out_path, diff)


def generate_ssim_map(ssim_map: np.ndarray, out_path: str):
    """保存 SSIM map 为灰度 PNG。"""
    ssim_vis = ((1 - ssim_map) * 255).clip(0, 255).astype(np.uint8)  # 反转：差异越大越亮
    cv2.imwrite(out_path, ssim_vis)


# ============================================================
# 4. 输出与报告
# ============================================================

def print_single_result(pair_name: str, metrics: dict):
    """终端打印单对结果。"""
    print(f"\n{'='*50}")
    print(f"  对比: {pair_name}")
    print(f"{'='*50}")
    print(f"  {'指标':<25} {'值':>15}")
    print(f"  {'-'*40}")
    for key, val in metrics.items():
        if val == float("inf"):
            val_str = "∞ (相同)"
        elif isinstance(val, float):
            val_str = f"{val:.6f}"
        else:
            val_str = str(val)
        print(f"  {key:<25} {val_str:>15}")
    print()


def print_batch_summary(all_results: list):
    """终端打印批量汇总。"""
    if not all_results:
        return

    print(f"\n{'='*60}")
    print(f"  批量汇总 ({len(all_results)} 组对比)")
    print(f"{'='*60}")

    # 收集所有指标名
    metric_keys = list(all_results[0]["metrics"].keys())

    # 打印每对的简要结果
    header = f"  {'文件对':<30} {'PSNR':>8} {'SSIM':>8} {'MSE':>10}"
    print(header)
    print(f"  {'-'*56}")
    for r in all_results:
        m = r["metrics"]
        psnr_s = "∞" if m["PSNR (dB)"] == float("inf") else f"{m['PSNR (dB)']:.2f}"
        print(f"  {r['pair_name']:<30} {psnr_s:>8} {m['SSIM']:>8.4f} {m['MSE']:>10.2f}")

    # 汇总统计
    print(f"\n  {'--- 汇总统计 ---':^56}")
    print(f"  {'指标':<25} {'平均':>10} {'最小':>10} {'最大':>10}")
    print(f"  {'-'*55}")
    for key in metric_keys:
        vals = [r["metrics"][key] for r in all_results if r["metrics"][key] != float("inf")]
        if vals:
            avg = sum(vals) / len(vals)
            print(f"  {key:<25} {avg:>10.4f} {min(vals):>10.4f} {max(vals):>10.4f}")
        else:
            print(f"  {key:<25} {'∞':>10} {'∞':>10} {'∞':>10}")
    print()


def save_json_report(results: list, output_dir: str):
    """保存 JSON 报告。"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_pairs": len(results),
        "results": [],
    }
    for r in results:
        entry = {
            "pair_name": r["pair_name"],
            "image_a": r["path_a"],
            "image_b": r["path_b"],
            "metrics": {},
        }
        for k, v in r["metrics"].items():
            entry["metrics"][k] = None if v == float("inf") else v
        report["results"].append(entry)

    out_path = os.path.join(output_dir, "report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  JSON 报告已保存: {out_path}")


def save_csv_report(results: list, output_dir: str):
    """保存 CSV 报告 (批量模式)。"""
    if not results:
        return
    out_path = os.path.join(output_dir, "report.csv")
    metric_keys = list(results[0]["metrics"].keys())

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pair_name", "image_a", "image_b"] + metric_keys)
        for r in results:
            row = [r["pair_name"], r["path_a"], r["path_b"]]
            for k in metric_keys:
                v = r["metrics"][k]
                row.append("inf" if v == float("inf") else v)
            writer.writerow(row)

        # 汇总行
        writer.writerow([])
        for stat_name, stat_fn in [("AVG", lambda vs: sum(vs)/len(vs)), ("MIN", min), ("MAX", max)]:
            row = [stat_name, "", ""]
            for k in metric_keys:
                vals = [r["metrics"][k] for r in results if r["metrics"][k] != float("inf")]
                row.append(round(stat_fn(vals), 6) if vals else "N/A")
            writer.writerow(row)

    print(f"  CSV 报告已保存: {out_path}")


def img_to_base64(path: str) -> str:
    """读取图片文件，返回 base64 data URI。"""
    ext = Path(path).suffix.lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "bmp": "image/bmp", "tiff": "image/tiff", "tif": "image/tiff"}
    mime_type = mime.get(ext.lstrip("."), "image/png")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime_type};base64,{data}"


def generate_html_report(results: list, output_dir: str, label_a: str = "原图 A", label_b: str = "原图 B") -> str:
    """读取 template.html 模板，填充数据，生成报告。"""
    # 构建 JS 数据
    pairs_js = []
    for r in results:
        metrics_obj = {}
        for k, v in r["metrics"].items():
            metrics_obj[k] = None if v == float("inf") else round(v, 6)
        pairs_js.append({
            "name": r["pair_name"],
            "imgA": img_to_base64(r["path_a"]),
            "imgB": img_to_base64(r["path_b"]),
            "heatmap": img_to_base64(r["diff_heatmap"]),
            "amplified": img_to_base64(r["diff_amplified"]),
            "ssim": img_to_base64(r["ssim_map"]),
            "metrics": metrics_obj,
        })

    pairs_json = json.dumps(pairs_js, ensure_ascii=False)

    # 读取模板文件
    template_path = Path(__file__).parent / "template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 替换占位符
    html = html.replace("{{PAIRS_JSON}}", pairs_json)
    html = html.replace("{{LABEL_A}}", label_a)
    html = html.replace("{{LABEL_B}}", label_b)

    out_path = os.path.join(output_dir, "report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML 报告已保存: {out_path}")
    return out_path


def ensure_output_dir(output_dir: str) -> str:
    """创建输出目录。"""
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def get_pair_output_dir(output_dir: str, pair_name: str) -> str:
    """创建对比对子目录。"""
    safe_name = pair_name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    pair_dir = os.path.join(output_dir, safe_name)
    os.makedirs(pair_dir, exist_ok=True)
    return pair_dir


# ============================================================
# 5. 单张对比 & 批量对比
# ============================================================

def compare_single(path_a: str, path_b: str, output_dir: str,
                   amplify_factor: int = 10, thresholds: list = None) -> dict:
    """对比一对图像，返回结果字典。"""
    img_a = read_image(path_a)
    img_b = read_image(path_b)
    check_size_match(img_a, img_b, path_a, path_b)

    metrics, ssim_map = compute_all_metrics(img_a, img_b, thresholds)

    pair_name = Path(path_a).stem

    # 打印结果
    print_single_result(pair_name, metrics)

    # 生成差异图
    pair_dir = get_pair_output_dir(output_dir, pair_name)
    heatmap_path = os.path.join(pair_dir, "diff_heatmap.png")
    amplified_path = os.path.join(pair_dir, "diff_amplified.png")
    ssim_path = os.path.join(pair_dir, "ssim_map.png")
    generate_diff_heatmap(img_a, img_b, heatmap_path)
    generate_amplified_diff(img_a, img_b, amplified_path, factor=amplify_factor)
    generate_ssim_map(ssim_map, ssim_path)
    print(f"  差异图已保存到: {pair_dir}/")

    return {
        "pair_name": pair_name,
        "path_a": str(Path(path_a).resolve()),
        "path_b": str(Path(path_b).resolve()),
        "metrics": metrics,
        "diff_heatmap": heatmap_path,
        "diff_amplified": amplified_path,
        "ssim_map": ssim_path,
    }


def scan_directories(dir_a: str, dir_b: str) -> list:
    """递归扫描两个目录，按相对路径配对。"""
    root_a, root_b = Path(dir_a), Path(dir_b)
    files_a = {str(p.relative_to(root_a)): p for p in root_a.rglob("*")
               if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS}
    files_b = {str(p.relative_to(root_b)): p for p in root_b.rglob("*")
               if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS}

    if not files_a:
        print(f"错误: 目录 {dir_a} 中没有支持的图像文件", file=sys.stderr)
        sys.exit(1)
    if not files_b:
        print(f"错误: 目录 {dir_b} 中没有支持的图像文件", file=sys.stderr)
        sys.exit(1)

    matched = sorted(set(files_a.keys()) & set(files_b.keys()))
    only_a = sorted(set(files_a.keys()) - set(files_b.keys()))
    only_b = sorted(set(files_b.keys()) - set(files_a.keys()))

    if only_a:
        print(f"  警告: 以下文件仅在 {dir_a} 中: {', '.join(only_a)}")
    if only_b:
        print(f"  警告: 以下文件仅在 {dir_b} 中: {', '.join(only_b)}")

    if not matched:
        print("错误: 两个目录中没有匹配的文件名", file=sys.stderr)
        sys.exit(1)

    print(f"  找到 {len(matched)} 组匹配的图像对\n")
    return [(str(files_a[name]), str(files_b[name])) for name in matched]


def compare_batch(dir_a: str, dir_b: str, output_dir: str,
                  amplify_factor: int = 10, thresholds: list = None) -> list:
    """批量对比两个目录。"""
    pairs = scan_directories(dir_a, dir_b)
    all_results = []

    for i, (pa, pb) in enumerate(pairs, 1):
        print(f"--- [{i}/{len(pairs)}] ---")
        try:
            result = compare_single(pa, pb, output_dir, amplify_factor, thresholds)
            all_results.append(result)
        except SystemExit:
            print(f"  跳过: {Path(pa).name} (尺寸不匹配或读取失败)")
            continue

    return all_results


# ============================================================
# 6. 主函数
# ============================================================

def main():
    cfg = load_config()

    parser = argparse.ArgumentParser(
        description="picmp - 图像质量对比工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python picmp.py                          (使用 config.json)\n"
            "  python picmp.py img_a.png img_b.png\n"
            "  python picmp.py --batch dir_a/ dir_b/\n"
        ),
    )
    parser.add_argument("inputs", nargs="*", help="两张图像路径，或 --batch 模式下两个目录路径")
    parser.add_argument("--batch", action="store_true", default=None, help="批量模式")
    parser.add_argument("-o", "--output", default=None, help="输出目录")
    parser.add_argument("--no-open", action="store_true", help="不自动打开 HTML 报告")

    args = parser.parse_args()

    # 合并配置：命令行 > config.json > 默认值
    is_batch = args.batch if args.batch else cfg.get("mode") == "batch"
    output_dir = args.output or cfg.get("output", "picmp_output")
    amplify_factor = cfg.get("amplify_factor", 10)
    thresholds = cfg.get("diff_threshold", [1, 5, 10])
    label_a = cfg.get("label_a", "原图 A")
    label_b = cfg.get("label_b", "原图 B")

    # 确定输入路径
    if args.inputs and len(args.inputs) == 2:
        input_a, input_b = args.inputs
    elif is_batch:
        input_a = cfg.get("dir_a", "")
        input_b = cfg.get("dir_b", "")
    else:
        input_a = cfg.get("image_a", "")
        input_b = cfg.get("image_b", "")

    if not input_a or not input_b:
        print("错误: 未指定输入。请传入命令行参数或配置 config.json", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    ensure_output_dir(output_dir)
    html_path = None

    if is_batch:
        for d in [input_a, input_b]:
            if not os.path.isdir(d):
                print(f"错误: {d} 不是有效目录", file=sys.stderr)
                sys.exit(1)

        print(f"批量对比模式: {input_a} vs {input_b}")
        all_results = compare_batch(input_a, input_b, output_dir, amplify_factor, thresholds)

        if all_results:
            print_batch_summary(all_results)
            save_json_report(all_results, output_dir)
            save_csv_report(all_results, output_dir)
            html_path = generate_html_report(all_results, output_dir, label_a, label_b)
    else:
        result = compare_single(input_a, input_b, output_dir, amplify_factor, thresholds)
        save_json_report([result], output_dir)
        html_path = generate_html_report([result], output_dir, label_a, label_b)

    print(f"完成! 输出目录: {os.path.abspath(output_dir)}")

    # 自动打开 HTML 报告
    if not args.no_open and html_path:
        webbrowser.open(Path(html_path).resolve().as_uri())


if __name__ == "__main__":
    main()
