# 奶蛙 · Milk Frog（1485 件）

奶蛙是 2025–2026 年中文互联网从“大笑奶龙”梗图里分化出的黄色蛙形迷因：
圆眼、眼白泛绿、小瞳孔、梨形身体、奶油色大肚皮、深棕色手脚，标志动作是
闭眼张嘴、露牙、双手捧肚狂笑。它不是亚马逊牛奶蛙，也没有官方设定。

参考资料：

- 奶蛙百科：<https://neta.art/app/milk-frog-wiki>
- Petdex 奶蛙 3D 精灵：<https://petdex.dev/pets/nailong-7>
- 奶蛙头像库：<https://works.cohub.live/w/157e937b-95da-4c17-add4-f916e37c3574/milk-frog-avatar-library/8e51277b6ee6/content/index.html>

## 造型决定

- **体块**：28×26 凸点地块、66 板高（约 21 cm）。底部 7 层用板铺出圆底，
  上面用 3 板高的砖层逐层收分；每层都是下一层的子集，所以不需要斜撑/悬挑。
- **脸**：12×7 的 SNOT 脸墙。42 块 `11211`（1×2 带两个侧凸点）竖着叠 7 行，
  再在侧凸点上贴 84 块 1×1 瓷砖。绿眼用 `98138` 圆瓷砖拼，瞳孔 2×2 黑，
  嘴是 6×2 深红 + 2×1 白牙，脸颊两片粉圆瓷砖。
- **肚皮**：奶油色（78 Light Flesh）只染身体最前 1–2 格，形成一个 16 板高的
  椭圆；手脚用深棕（86 / 308）色块，不额外加凸出零件，避免悬空。
- **底座**：28×26 荷叶，2 层板，前左切一个 V 形缺口；5 朵粉色小花。

## 校验

```
parts=1485 unique=17 colours=10 top_level=66
floating=0 weak=0 orphans=0 snot=84 links=2008
missing=none bad colour=none
```

- `floating=0`：没有悬空件。
- `orphans=0`：所有零件通过凸点/底面连接链回到地面。
- `snot=84`：84 块竖贴瓷砖；`snot_unsupported` 为 0。
- `validate_ldr.py`：1485 个放置、123 个 STEP、无缺件、无色号错误。

## 文件

- 设计脚本：`examples/milkfrog.py`
- 模型：`out/milkfrog/milkfrog.ldr`
- 零件表：`out/milkfrog/bom.csv`
- 预览：`docs/preview-milkfrog.png`（正面：`out/milkfrog/preview-front.png`）

## 简化

- 眼睛是像素/马赛克风格，不是参考图里的半球凸眼；这样能用 SNOT 脸墙一次做准。
- 身体是实心砖雕，内部没有空腔；1485 件里约 2/3 是 2×4 / 1×4 砖，拼装偏重。
- 没有做张嘴的红色口腔深度、舌头和牙齿分件；远看是“大笑”，近看是色块。
