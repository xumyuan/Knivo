# picmp - 图像质量对比工具

命令行图像质量对比工具，支持单张/批量对比，计算多维度质量指标，生成差异可视化图和交互式 HTML 报告。

## 功能

- **单张对比**: 两张图一对一对比
- **批量对比**: 两个目录按文件名自动配对（支持递归子目录）
- **质量指标**: PSNR, SSIM, MSE, MAE, BGR 直方图相关性, 像素差异百分比
- **差异可视化**: 热力图、放大差异图 (10x)、SSIM 结构差异图
- **HTML 报告**: 交互式单文件报告，左右键切换，点击放大，视图开关，拖拽调整布局
- **终端输出**: 格式化表格 + JSON/CSV 报告

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 编辑配置文件
# config.json

# 双击运行（Windows）
run.bat
```

## 用法

```bash
# 使用 config.json 配置（推荐）
python picmp.py

# 单张对比
python picmp.py img_a.png img_b.png

# 指定输出目录
python picmp.py img_a.png img_b.png -o results/

# 批量对比（递归扫描子目录）
python picmp.py --batch dir_a/ dir_b/

# 不自动打开浏览器
python picmp.py --no-open
```

## 配置文件

`config.json` 示例：

```json
{
  "mode": "batch",
  "image_a": "path/to/a.png",
  "image_b": "path/to/b.png",
  "dir_a": "path/to/dir_a",
  "dir_b": "path/to/dir_b",
  "output": "picmp_output",
  "label_a": "原图 A",
  "label_b": "原图 B",
  "amplify_factor": 10,
  "diff_threshold": [1, 5, 10]
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `mode` | `single` 或 `batch` | `single` |
| `image_a` / `image_b` | 单张模式的两张图路径 | - |
| `dir_a` / `dir_b` | 批量模式的两个目录路径 | - |
| `output` | 输出目录 | `picmp_output` |
| `label_a` / `label_b` | HTML 报告中的图片标签名 | `原图 A` / `原图 B` |
| `amplify_factor` | 放大差异图的倍数 | `10` |
| `diff_threshold` | 像素差异百分比的阈值列表 | `[1, 5, 10]` |

## 输出结构

```
output/
├── report.html           # 交互式 HTML 报告（单文件，可独立查看）
├── report.json           # 完整指标 JSON
├── report.csv            # 批量汇总 CSV（仅批量模式）
└── <pair_name>/
    ├── diff_heatmap.png  # 差异热力图（蓝=小差异, 红=大差异）
    ├── diff_amplified.png # 放大差异图（像素差值 x10）
    └── ssim_map.png      # SSIM 结构差异图（越亮=差异越大）
```

## HTML 报告功能

- 上下两栏布局：上栏原图+指标，下栏差异图
- `←` `→` 键盘切换图片对
- 点击图片全屏查看原始大小
- 顶栏 Pill 按钮控制各视图显隐
- 下栏「全部」按钮一键开关差异图
- 拖拽分割条调整上下栏高度
- 指标颜色分级：绿色=好，黄色=有差异，红色=差异大
- 悬停指标名查看含义说明

## 支持格式

PNG, JPG/JPEG, WebP, BMP, TIFF

## 依赖

- Python 3.10+
- opencv-python
- numpy
- scikit-image

## 文件结构

```
picmp/
├── picmp.py          # 主脚本
├── template.html     # HTML 报告模板
├── config.json       # 配置文件
├── requirements.txt  # Python 依赖
└── run.bat           # Windows 一键运行
```
