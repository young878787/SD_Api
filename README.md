# 動漫角色自動化抽獎設計助手 - Stable Diffusion AI

使用 GitHub Models GPT-4o 自動抽獎設計全新的動漫角色，包括完整的外貌、服裝、配飾等所有細節！

## 🎲 核心功能

### 🎯 隨機抽獎系統
- 從 5 種角色類型中隨機抽取
- 清純少女、可愛少女、成熟女性、優雅女性、活潑少女
- 每次運行都會獲得不同的驚喜角色！

### 🎨 AI 完整角色設計
- **外貌特徵**：髮色、髮型、眼睛顏色、身材等
- **完整服裝**：上衣、下裝、外套、鞋子等所有細節
- **配飾設計**：項鍊、耳環、手鐲、髮飾等
- **場景氛圍**：背景、姿勢、表情、整體風格

### ⚡ 自動化流程
1. 🎲 隨機抽取角色類型
2. 🤖 AI 設計完整角色（所有細節）
3. ✨ 自動添加質量增強標籤
4. 💾 保存到 docs/ 資料夾（帶時間戳）
5. ✅ 生成可直接使用的 Stable Diffusion Prompt

## 🚀 快速開始

### 1. 配置 .env 文件

```powershell
# 複製 .env.example 為 .env
Copy-Item .env.example .env

# 編輯 .env 文件，添加您的 GitHub Token
# GITHUB_TOKEN=ghp_your_token_here
```

### 2. 安裝依賴

```powershell
pip install openai python-dotenv
```

### 3. 執行腳本

```powershell
# 完整功能：過濾 + AI 設計服裝
python design_outfit.py

# 或僅過濾功能
python filter_prompt_only.py
```

## 📋 功能

### 完整功能腳本 (`design_outfit.py`)

- ✅ 從 `test.json` 提取 prompt 欄位
- ✅ 過濾掉 19+ 個質量增強標籤
- ✅ 保留角色特徵信息
- ✅ 使用 GPT-4o 自動設計服裝
- ✅ 生成 Stable Diffusion 格式的完整 prompt
- ✅ 保存結果到 `outfit_design_result.txt`

### 僅過濾功能 (`filter_prompt_only.py`)

- ✅ 本地處理，無需 API
- ✅ 提取並分析 prompt
- ✅ 按類別分類標籤
- ✅ 生成詳細分析報告
- ✅ 保存結果到 `filtered_prompt.txt`

## 📁 項目結構

```
Api/
├── .env                          # 配置文件（包含 Token）
├── .env.example                  # 配置示例
├── .gitignore                    # Git 忽略配置
├── design_outfit.py              # 完整功能腳本
├── filter_prompt_only.py         # 過濾功能腳本
├── test.json                     # Stable Diffusion 配置
├── docs/                         # 文檔
│   ├── 快速開始指南.md           # 開始使用
│   ├── README_outfit_designer.md # 詳細功能說明
│   └── 使用說明.md               # 高級用法
├── filtered_prompt.txt           # 過濾結果（運行後生成）
└── outfit_design_result.txt      # AI 設計結果（運行後生成）
```

## 📖 文檔

- **[快速開始指南](docs/快速開始指南.md)** - 5 分鐘快速上手
- **[詳細說明](docs/README_outfit_designer.md)** - 完整功能介紹
- **[使用說明](docs/使用說明.md)** - 進階功能和開發指南

## 🔐 安全

- ⚠️ **不要提交** `.env` 文件到 Git
- ✅ 使用 `.env.example` 作為模板分享
- ✅ `.env` 已添加到 `.gitignore`
- ✅ Token 由 `python-dotenv` 安全加載

## 📊 工作流

```
test.json
   ↓
[提取 prompt]
   ↓
[過濾質量標籤]
   ↓
[保留角色特徵]
   ↓
filtered_prompt.txt
   ↓
[GPT-4o API]
   ↓
[設計服裝]
   ↓
outfit_design_result.txt
```

## 🎨 示例

### 輸入（原始 Prompt）

```
<lora:add_detail:1>,<lora:illustrious_masterpieces_v3:0.8>,absurdres,
masterpiece,detailed eyes,perfect eyes,highly detailed face,best quality,
<lora:rushia:1.5>,rushia_blue,green hair,short hair,red eyes,blue dress,
short dress,wide_sleeves,lace,skull hair ornament,leg_garter,ring,
light_blush,seductive_smile,standing,fantasy,gradient_background
```

### 過濾後（角色特徵）

```
<lora:rushia:1.5>,rushia_blue,green hair,short hair,red eyes,
blue dress,short dress,wide_sleeves,lace,skull hair ornament,
leg_garter,ring,light_blush,seductive_smile,standing,
fantasy,gradient_background
```

### AI 設計的服裝

```
elegant gothic lolita dress, black lace bodice with silver embroidery,
flowing layered purple skirt, multiple ruffled tiers, wide bell sleeves
with lace trim, black and white apron overlay with decorative details,
black thigh-high stockings with lace pattern, platform black boots,
silver chain accessories, cross necklace, gothic jewelry set,
skull hair clips, ribbon bow details, dramatic gothic aesthetic
```

## 💻 要求

- Python 3.7+
- GitHub Token（可从 https://github.com/settings/tokens 获取）
- 网络连接（仅 API 模式需要）

## 🛠️ 安装

### 1. 获取 Token

访问 https://github.com/settings/tokens:
- 点击 "Generate new token" → "Generate new token (classic)"
- 生成并复制 Token

### 2. 配置

```powershell
# 编辑 .env 文件
GITHUB_TOKEN=ghp_your_token_here
```

### 3. 安装包

```powershell
pip install openai python-dotenv
```

## 🎯 使用方法

### 方法 1：自动设计服装（需要 Token）

```powershell
python design_outfit.py
```

### 方法 2：仅过滤（无需 Token）

```powershell
python filter_prompt_only.py
```

## ❓ 常见问题

**Q: 为什么要使用 .env？**
A: 安全存储敏感信息，不会暴露在命令历史中

**Q: Token 暴露了怎么办？**
A: 在 GitHub 设置中删除该 Token，生成新的

**Q: 支持其他 AI 模型吗？**
A: 可以修改代码集成其他 API

**Q: 可以离线使用吗？**
A: 可以，使用 `filter_prompt_only.py` 不需要网络

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**快速链接：**
- [快速开始](docs/快速開始指南.md)
- [完整文档](docs/使用說明.md)
- [GitHub Token 获取](https://github.com/settings/tokens)
