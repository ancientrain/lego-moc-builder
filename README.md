# lego-moc-builder

让 AI 自主设计**真的拼得起来**的乐高 MOC。

![cottage](docs/preview-cottage.png)

## 它解决什么问题

直接让大模型输出 LDraw 坐标，结果几乎总是错的：零件悬空、互相重叠、零件号不存在、窗户比墙洞大。
这个工具包把"设计"和"几何正确性"拆开：

```
布局与造型（LLM 决定）  →  网格化放置（Model 强制约束）  →  结构校验（check 判定）  →  渲染（render 回看）
```

模型只需要给出**凸点/板层的整数坐标**和房间划分；能不能拼由确定性代码说了算。

## 特性

- **网格化建模**：凸点级坐标、整数板层，自动处理 LDraw 的零件原点/旋转/包围盒。
- **结构校验**：悬空件（`floating`）、脱地块（`orphans`）、支撑面积（`weak`）。
- **软渲染**：numpy z-buffer + 方向光 + 边缘增强，无 GPU、无 GUI，单张 0.5–10 秒。
- **真实零件库**：直接读 BrickLink Studio 自带的 LDraw 库（含 Studio 的 `UnOfficial` 更新件）。
- **导出**：`.ldr`（Studio / LDView / LeoCAD 可直接打开，含 `0 STEP`）+ `bom.csv`。

## 安装

```bash
pip install numpy pillow
git clone https://github.com/ancientrain/lego-moc-builder.git
cd lego-moc-builder
python3 scripts/index_parts.py        # 建立零件索引（约 1 秒）
```

零件库定位顺序：`$LDRAW_DIR` → `C:\Program Files\Studio 2.0\ldraw`（WSL 下自动映射到 `/mnt/c/...`）
→ `~/lego/lib/usr/share/ldraw` → `/usr/share/ldraw`。

## 使用

```bash
python3 examples/build.py cottage     # 236 件小房子
python3 examples/build.py house       # 花园洋房
python3 examples/build.py villa       # 750 件三层别墅（可分层）
```

输出：`out/<name>/{name}.ldr, bom.csv, preview-iso.png, preview-front.png}`。

自己写设计：

```python
from paths import find_ldraw
from ldrawlib import Library
from model import Model
import check, render

m = Model(Library(find_ldraw()), 20, 14)      # 地块 20×14 凸点
for x in range(0, 20, 4):                      # 一圈 1×4 砖
    m.place("3010", 15, x, 0, 1)
check.print_report(m)                          # floating 必须是 0
render.render(m, "preview.png", az=30, el=28)
open("model.ldr", "w").write(m.to_ldr("demo"))
```

## 示例

| 文件 | 件数 | 内容 |
|---|---|---|
| `examples/cottage.py` | 236 | 白色联排小楼：门窗、平顶、檐口、花池 |
| `examples/house.py` | 295 | 带花园的房子：真实门框/窗框、室内家具、33° 斜顶、围栏 |
| `examples/villa.py` | 750 | 三层别墅：客厅/餐厅/厨房/卫浴/2 卧室/书房/阁楼、车库+汽车+摩托、5 个人仔、可分层的街景式结构 |

## 已知限制

- 只支持绕 Y 轴旋转（0/90/180/270）；斜置、SNOT 侧向连接暂不支持。
- 没有碰撞检测之外的运动学检查（齿轮、铰链）。
- 家具是"示意级"配方，不是官方套装的精细度。
- 不生成 PDF 说明书；`.ldr` 里的 `0 STEP` 可交给 Studio / LPub3D 出图。

## 许可

- 代码：MIT（见 `LICENSE`）。
- 示例模型与文档：CC BY 4.0。
- LDraw 零件库：CC BY 4.0，版权归 LDraw.org 贡献者；LEGO® 是 LEGO Group 的商标，
  本项目与其无关联。
