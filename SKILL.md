---
name: lego-moc-builder
description: 用代码生成可拼装的乐高 MOC（LDraw）：网格化建模 + 悬空/连通校验 + 软渲染预览 + 导出 .ldr/零件表。
whenToUse: 需要让模型自主设计乐高模型（房子/别墅/载具/场景）、生成 LDraw 文件、验证"真的拼得起来"、或批量产出乐高图纸与零件清单时。
---

# lego-moc-builder

把"设计乐高"拆成三层：**LLM 出布局与造型 → 确定性几何内核负责放置与校验 → 渲染回看迭代**。
不要让模型直接吐三维坐标：它会写出悬空、重叠、错位的零件。让模型写**分层平面布局 + 网格坐标**，
由本 skill 的 `Model` 强制约束，再由 `check` 判定能不能拼。

## 0. 前提

- 一份本地 LDraw 零件库（含 `parts/`）：
  - BrickLink Studio 自带：`C:\Program Files\Studio 2.0\ldraw`（首选，颜色即在售色）
  - Ubuntu：`sudo apt install ldraw-parts`（`/usr/share/ldraw`）
  - 官方：<https://library.ldraw.org> 的 `complete.zip`
  - 用 `LDRAW_DIR` 环境变量覆盖自动探测
- Python 3.10+，`numpy`、`Pillow`（`pip install numpy pillow`）

## 1. 快速开始

```bash
python3 scripts/index_parts.py                    # 生成 cache/parts.json + colors.json
python3 scripts/search.py "^Door 1 x 4 x 6"       # 查真实零件号（空格已归一化）
python3 scripts/part_info.py 30179 2377 3028      # 看尺寸/包围盒（凸点、板数）
python3 examples/build.py cottage                 # 建模 + 校验 + .ldr + BOM + 预览
```

产出在 `out/<design>/`：`*.ldr`、`bom.csv`、`preview-iso.png`、`preview-front.png`。

## 2. 坐标系（唯一正确的记法）

- `x, z` 单位是**凸点**，`level` 单位是**板**（1 plate = 8 LDU = 1/3 砖高）。
- 世界 `-Y` 向上；`level` 是零件**底面**所在板层，板层 `0` 是地面。
- 零件在 `PALETTE` 里声明 `(宽, 深, 高, 类型)`；`model.place(code, colour, x, z, level, rot)` 只接受整数格。
- 旋转只支持 `0 / 90 / 180 / 270`（绕 Y 轴）。斜屋顶、墙沿 z 走向都靠它。

## 3. 五条硬规则（违反就会产出"看着对、拼不起来"）

1. **每块都必须压在下面的格子上**。`check.report()` 的 `floating` 必须为 0；
   `orphans` 必须为 0（所有零件通过支撑链连到地面）。
2. **楼板要用大板**。18 凸点的跨度用 3 块 `3028`（6×12）横跨、两端压墙；
   用 2×4 小板拼，中间的板没有凸点咬合，物理上会掉。
3. **斜面要算咬合**。45° 斜面（`3037/3039`，2 凸点深）必须 1 凸点退台才咬得住；
   要 2 凸点退台就用 33° 斜面（`3297/3298`，3 凸点深），正好压住 1 凸点。
4. **窗框是 2 凸点宽**（`2377`），墙洞必须正好挖 2 格、6 板高；一次只放一樘，
   放两樘会重叠（这是最容易犯的错）。
5. **隔墙交叉点要错开 1 格**。`partition_x(x, …)` 与 `partition_z(z, …)` 在拐角会抢同一格，
   用起点 `+1` 避开。

## 4. 核心 API

```python
from paths import find_ldraw
from ldrawlib import Library
from model import Model, PALETTE, build_order
import check, render

lib = Library(find_ldraw())          # 索引 parts / p / UnOfficial/parts
m = Model(lib, 28, 20)               # 地块 28×20 凸点

m.place("3020", 15, x, z, level)                  # 2×4 板，白色
m.place("2377", 15, x, z, level, rot=90)          # 窗框，沿 z 墙
m.place("4862", 43, x, z, level, overlap=True)    # 玻璃嵌进框：不占格、不参与碰撞
m.place("3004", 70, x, z, level, rot=90)          # 1×2 砖沿 z
m.place("970", 0, x, z, level, overlap=True, y_off=0)   # 人仔腿（不规则件用 y_off 叠）

check.print_report(m)                # parts / floating / orphans / BOM 摘要
render.render(m, "preview.png", size=(1100, 850), az=30, el=28)
m.to_ldr("My MOC")                   # LDraw 文本，每 12 件插一个 0 STEP
```

- `overlap=True`：给"嵌进去"的零件（玻璃、人仔、车轮）用，不占格、跳过碰撞。
- `y_off`：偏离网格的垂直偏移（LDU），人仔用 `0 / -32 / -76 / -100`。
- `build_order()`：底层优先、同层结构件先于玻璃/门板，导出时自动用。
- `window(m, x, z, level, rot)` / `partition_x/z` / `fill_rect` 见 `examples/` 里的复用写法。

## 5. 工作流

1. **定布局**：先说清地块尺寸、每层房间划分、门窗位置（用凸点坐标）。
2. **查零件**：`search.py` 找真实零件号，`part_info.py` 确认尺寸（别猜零件号）。
3. **建壳**：地面 → 外墙（挖洞）→ 楼板 → 隔墙 → 门窗。
4. **校验**：`python3 examples/build.py <design>`；先修 `floating/orphans`，再看渲染。
5. **看渲染改设计**：`preview-iso.png` 判断比例/轮廓，必要时换视角再渲染。
6. **交付**：`.ldr` + `bom.csv` + 预览图；模型大时按层拆成多个 `.ldr`。

## 6. 踩过的坑（省你几小时）

| 现象 | 原因 | 解法 |
|---|---|---|
| 渲染出现"零件穿透/屋顶漏光" | 用画家算法排序 | 换成 z-buffer（本 skill 的 `render.py` 已是） |
| 楼顶一大片零件消失 | LDraw 各零件绕序不一致，背面剔除误杀 | **关闭背面剔除**，只靠 z-buffer |
| 窗框互相重叠 | 2 凸点宽的框按每格放了一次 | 一个 2 格洞只放一樘 |
| 隔墙拐角重叠 | x 墙与 z 墙抢拐角格 | 起点 +1 |
| 家具浮空 | 桌腿 3 板高、桌面放在 `level+3` 却没对齐 | 腿占 `level…level+3`，桌面放 `level+3`；先算再放 |
| 车库/屋檐悬空 | 门洞上方直接放横梁 | 横梁要么搭在两侧墙上，要么让屋顶板跨过去 |
| 零件库缺件 | 只索引了 `parts/` | Studio 的更新件在 `UnOfficial/parts`，两个都要扫 |
| 大模型渲染慢 | 30 万三角面 | 渲染分辨率降到 1100×850、`supersample=2`；只渲关键 2–4 个视角 |

## 7. 参考

- 设计模式（墙/门窗/屋顶/楼板/家具/人仔的复用写法）：`docs/design-patterns.md`
- LDraw 几何与渲染细节：`docs/gotchas.md`
- 三个完整示例：`examples/cottage.py`（236 件）、`examples/house.py`（花园洋房）、`examples/villa.py`（750 件三层别墅，可分层拆分）
- LDraw 文件格式：<https://www.ldraw.org/article/218.html>
