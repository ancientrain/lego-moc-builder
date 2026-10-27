# 设计模式

把"盖房子"拆成可复用的函数。所有函数只依赖 `Model.place`，坐标一律 `(x, z, level)`。

## 1. 外墙 + 开洞

墙是 1 凸点厚的一圈格子；先算开洞表 `{(x, z): {levels}}`，再逐层铺砖。

```python
def build_run(m, cells, level, colour, horizontal, offset, openings=None):
    seg = [None if (openings and level in openings.get(c, set())) else c for c in cells]
    # 沿 run 贪心铺 1x4 / 1x2 / 1x1，offset 用来错缝
```

- 前后墙沿 x 走向（`rot=0`），左右墙沿 z 走向（`rot=90`）。
- **错缝**：奇数层先放一块 1×2 再放 1×4，避免四角通缝。
- 拐角只归前后墙，左右墙从 `+1` 开始，否则抢格。

## 2. 门

```python
m.place("30179", 70, x, z, 1)                       # 1x4x6 门框，18 板高
for k in range(6):
    m.place("3010", 308, x, z, 1 + 3 * k, overlap=True)   # 4 宽门板（6 块 1x4 砖）
m.place("3070b", 14, x + 3, z, 7, overlap=True)     # 门把手
```

门框 18 板高 ⇒ 层高必须是 6 层砖（18 板），否则门会顶穿楼板。

## 3. 窗

```python
m.place("2377", 15, x, z, level, rot=rot)                    # 2 宽 × 6 板窗框
m.place("4862", 43, x, z, level, rot=rot, overlap=True)      # 玻璃嵌进框
```

- 一个窗占 **2 格 × 6 板**；墙洞必须正好 2 格宽、6 板高。
- 侧墙用 `rot=90`，此时占 1 格宽 × 2 格深 —— 开洞也要按 z 方向挖 2 格。

## 4. 楼板

```python
for k in range(3):
    m.place("3028", GREY, HX + 6 * k, HZ, slab_level, rot=90)   # 6x12 大板
```

三块 6×12 正好铺满 18 凸点，**两端压在承重墙上**。这是让整层楼板成立的关键：
小板拼出来的楼板中间没有凸点咬合，物理上会掉，`check` 也会判 `floating`。

## 5. 屋顶

**33° 双坡（推荐，3 凸点深，2 凸点退台）**

```python
for k in range(steps):
    level = top + 3 * k
    for i in range(0, 12, 4):
        m.place("3037", DARK_RED, HX + i, HZ + k, level)                    # 后坡
        m.place("3037", DARK_RED, HX + i, HZ + HD - 2 - k, level, rot=180)  # 前坡
```

每层退 2 凸点，正好压住下一层 1 个凸点。屋面坡度 ≈ 31°。

**45° 双坡（2 凸点深，只能 1 凸点退台）**：坡度更陡（5 层 ≈ 15 板高），适合小房子。

**山墙**：坡屋顶两端要补阶梯状砖墙，用 `rot=90` 的 1×2 砖逐层填两侧坡面之间的空隙。
山墙本身还能承住屋脊梁。

## 6. 隔墙与门洞

```python
def partition_x(m, x, z0, z1, base, courses, colour, gap=None):
    # gap: {z: set(levels)}，用 doorway(z_from, z_to, base) 生成整层通高的门洞
```

x 走向墙用 `rot=90` 的砖（1 宽 × N 深）；z 走向墙用普通砖。

## 7. 家具配方（示意级，可替换）

| 家具 | 做法 |
|---|---|
| 床 | 2×4 砖 ×2 作床架（3 板）+ 2×4 板床垫 + 1×2 板枕头 + 2×4 板被子 |
| 桌 | 四条 1×1 砖（3 板）+ 2×4 板桌面（放 `level+3`） |
| 椅 | 1×1 板 + 1×1 砖 + 2×2 板座面（放 `level+4`） |
| 沙发 | 2×4 板座 + 1×4 砖靠背（放 `level+1`） |
| 浴缸 | 2×4 板 + 1×4 板内衬 + 透明件水面（`overlap`） |
| 马桶/洗手盆 | 1×2 板 + 1×1 砖，上面再加 1×2 板 |
| 书架 | 竖放 1×2 砖 ×2 + 顶板 |

规律：**腿占 3 板，座面/桌面就放 `level+3`**；椅子多 1 板座面就 `level+4`。
算错一层就是 `floating` 或重叠。

## 8. 人仔

```python
m.place("970", legs, x, z, level, overlap=True)                  # 腿（4 板）
m.place("973", torso, x, z, level, y_off=-32, overlap=True)      # 上身
m.place("3626c", head, x, z, level, y_off=-76, overlap=True)     # 头
m.place("10048", hair_colour, x, z, level, y_off=-100, overlap=True)  # 头发
```

人仔不规则、且要"叠进"墙体空间，所以全部 `overlap=True` + `y_off`。
头发零件不同，`y_off` 需要按渲染结果微调。

## 9. 可分层结构（街景式）

每层 = 楼板 + 墙体 + 家具，直接叠在下一层上：

```python
BASE0 = 1;              SLAB1 = BASE0 + 18;   BASE1 = SLAB1 + 1
SLAB2 = BASE1 + 18;     BASE2 = SLAB2 + 1
```

导出时按层拆文件（`storey-0.ldr` / `storey-1.ldr` / …），或把每层所有零件 `level` 加一个偏移做"爆炸图"。

## 10. 花园

- 草坪：地块板铺绿色；房子/车库区域单独铺米色/深灰，做出"室内地面"。
- 小径：1×2 瓷砖铺在草地上（`level=1`，直接压在草地板上）。
- 树：`3470` 一个零件就是 4×4 的树，最省件。
- 花：`3741a` 花茎（5 板）+ `3742` 花（`overlap` 放在茎顶）。
- 围栏：`33303`（4 宽 × 2 砖高）沿边排一圈。

## 11. SNOT 脸墙（角色/像素画）

竖着的脸 = 一排 `11211`（1×2 砖，两个侧凸点）+ 一排 `3070b`/`98138` 瓷砖。
`place_on_stud` 用的是 LDraw 里的真实凸点（包括侧凸点），不用手算矩阵。

```python
# 脸墙 12 宽 × 7 行，行距 3 板；先铺 11211 墙，再逐格贴脸
hosts = {}
for r in range(7):
    level = 42 + 3 * r
    for i in range(6):
        hosts[(r, i)] = m.place("11211", 14, 8 + 2 * i, 5, level)

for r in range(7):                 # r=0 是脸的最下面一行
    for c in range(12):
        colour = pattern[6 - r][c]  # 图案行从上往下存
        tile = "98138" if colour in (10, 0, 13) else "3070b"
        m.place_on_stud(tile, colour, hosts[(r, c // 2)], stud=c % 2)
```

- 最底一行 11211 下面要有一条 1 格檐口（前一层的砖伸出来 1 格），否则整面墙悬空。
- 侧凸点行距 24 LDU，瓷砖高 20 LDU，行间固定留 4 LDU 缝；这是正常的。
- 眼白/瞳孔用 `98138` 圆瓷砖，脸底用 `3070b` 方瓷砖，远看更圆。
- 脸墙太靠后会藏在肚子后面：把脸墙放在身体最前缘的 z，肚子色块从脸下方开始。

