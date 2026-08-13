# 程序员做饭指南 · 小程序

基于开源菜谱仓库 [Anduin2017/HowToCook](https://github.com/Anduin2017/HowToCook)（约 360 道菜）实现的微信小程序。

## 四大能力

| 能力 | 云函数 action | 说明 |
| --- | --- | --- |
| 1. 获取所有菜谱（简化版） | `getAll` | 分页 + 关键字/分类筛选，默认精简字段，避免上下文过大 |
| 2. 按分类获取菜谱 | `getByCategory` | 水产 / 早餐 / 荤菜 / 主食 / 素菜 / 汤羹 / 甜点 / 饮品 … 一键查询 |
| 3. 不知道吃什么 | `recommendToday` | 按用餐人数 + 过敏原 + 忌口，直接推荐今日菜单 |
| 4. 一周膳食计划 | `recommendPlan` | 按忌口 + 过敏原 + 人数，规划七天不重样的早/午/晚三餐 |

额外：`getCategories`（分类列表）、`getById`（单菜详情）。

## 目录结构

```
cookbook-miniprogram/
├── project.config.json         # 小程序项目配置（微信开发者工具根目录）
├── server.js                   # 本地测试服务（无需 CloudBase 即可联调 4 个能力）
├── scripts/
│   ├── build-recipes.js        # 解析 HowToCook 仓库 -> data/recipes.json
│   ├── update_images.py        # 一键拉取菜谱封面图（绕开 LFS 额度）并打包
│   └── images-manifest.json    # 图片清单（update_images.py 生成）
├── update_images.bat           # Windows 一键更新图片
├── data/
│   └── recipes.json            # 解析后的结构化菜谱（单源数据）
├── cloudfunctions/
│   └── getRecipes/             # CloudBase 云函数
│       ├── index.js            # 云函数入口（exports.main）
│       ├── logic.js            # 核心逻辑（4 能力 + 过敏原/忌口过滤）
│       ├── package.json
│       └── data/recipes.json   # 云函数内置数据
└── miniprogram/                # 小程序前端
    ├── app.js / app.json / app.wxss
    ├── config.js               # mode: 'cloud' | 'http'
    ├── utils/                  # api.js（统一调用封装）、categories.js、diet.js
    ├── components/recipe-card/ # 可复用菜谱卡片
    └── pages/
        ├── index/              # 首页：搜索 + 两大决策入口 + 分类网格
        ├── recipes/            # 菜谱列表（分类/搜索/分页）
        ├── detail/             # 菜谱详情
        ├── random/             # 不知道吃什么
        └── plan/               # 一周膳食计划
```

## 本地联调（最快验证）

```bash
# 1. 启动本地服务（默认 http://localhost:3000）
node server.js

# 2. 小程序端：把 miniprogram/config.js 的 mode 改为 'http'
#    （微信开发者工具需勾选「不校验合法域名、web-view、TLS 等」）
#    小程序即可直接调用本地服务，无需部署云端
```

接口示例（POST `/api`，body 即云函数 event）：

```json
{ "action": "recommendPlan", "people": 2, "allergens": ["鸡蛋","虾蟹甲壳类"], "dislikes": ["香菜"] }
```

## 部署到 CloudBase（生产）

1. **准备数据**：若菜谱需更新，重新解析并同步到云函数目录
   ```bash
   node scripts/build-recipes.js
   cp data/recipes.json cloudfunctions/getRecipes/data/recipes.json
   ```
2. **上传云函数**：在微信开发者工具中，右键 `cloudfunctions/getRecipes` → 上传并部署（云端安装依赖）。
3. **配置环境**：
   - 打开 `miniprogram/config.js`，将 `mode` 改为 `'cloud'`；
   - 填入你的 CloudBase `envId`。
4. **打开小程序**：用微信开发者工具「导入项目」，目录选择本仓库根目录（`project.config.json` 所在处）。测试可用 `touristappid`，正式发布请替换为你自己的 AppID。

## 更新菜谱图片（一键脚本）

HowToCook 仓库的 Git LFS 额度已超额，`git clone` / `git lfs pull` 拉不到真实图片（只会得到 130 字节的 LFS 指针）。本脚本改用「`github.com` raw 直链」通道（不查 LFS 额度）拉取封面图，压缩后打包进小程序主包。

```bash
# Windows 一键（双击 update_images.bat，或拖入本地 dishes 目录）
update_images.bat "D:\你的仓库\HowToCook\dishes"

# 或手动：
python scripts/update_images.py "D:\你的仓库\HowToCook\dishes"
```

脚本会：扫描本地 markdown → 用 raw 直链下载每道菜的封面 → 自动装 Pillow 压缩（超 1.85MB 自动再压一轮）→ 写入 `miniprogram/assets/recipes/<分类>/<菜名>/cover.jpg` → 生成 `scripts/images-manifest.json` → 自动重算 `recipes.json`。

> 不传 dishes 路径时脚本会自动探测 `D:\tmp\111\HowToCook\dishes`、`D:\tmp\HowToCook\HowToCook-master\dishes` 等常见位置。
> 微信主包限 2MB，当前方案只取每道菜一张头图（约 1.4MB）；若需完整步骤图，请改用「云存储托管」方案。

## 过敏原与忌口

- **过敏原**：前端提供 9 项常见过敏原多选（鸡蛋 / 牛奶 / 花生 / 坚果 / 大豆 / 小麦麸质 / 鱼 / 虾蟹甲壳类 / 贝类），后端按食材关键词在菜谱文本中匹配并剔除。
- **忌口**：自由文本，逗号分隔（如 `香菜, 葱, 姜`），同样按关键词过滤。

> 关键词匹配为启发式规则，覆盖常见表述；如需更精确，可在 `cloudfunctions/getRecipes/logic.js` 的 `ALLERGEN_KEYWORDS` 中扩充。

## 主题风格

蜡笔小新风格：饱和蜡笔色 + 暖棕粗描边 + 贴纸投影，主题色在 `miniprogram/app.wxss` 的 CSS 变量中集中管理，便于整体换肤。
