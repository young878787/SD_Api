# 服裝設計助手文檔

## 功能概述

從 Stable Diffusion 的配置 JSON 中提取角色特徵，過濾掉質量增強標籤，然後使用 GitHub Models GPT-4o API 為角色設計完整服裝。

## 使用方法

### 快速開始

1. **查看** [快速開始指南.md](快速開始指南.md)
2. **配置** `.env` 文件（添加 GitHub Token）
3. **執行** `python design_outfit.py` 或 `python filter_prompt_only.py`

### 兩種使用方式

#### 方式 1: 完整功能（使用 GitHub Models API）

使用 GPT-4o 自動設計服裝

```powershell
python design_outfit.py
```

**要求：**
- `.env` 文件中配置 `GITHUB_TOKEN`
- 安裝 `openai` 和 `python-dotenv` 套件

**輸出：**
- 控制台顯示設計結果
- `outfit_design_result.txt` 包含完整結果

#### 方式 2: 僅過濾功能（本地處理）

只過濾 prompt，不調用 API

```powershell
python filter_prompt_only.py
```

**要求：**
- 無需 API Token
- 無需網絡連接

**輸出：**
- `filtered_prompt.txt` 包含過濾結果和詳細分析

## 過濾規則

### 移除的標籤

以下質量增強標籤會被自動移除：

| 類別 | 標籤 |
|------|------|
| LoRA 增強 | `<lora:add_detail:1>`, `<lora:illustrious_masterpieces_v3:0.8>`, `<lora:best_of_ai_styles_noob-vpred-1.0_v2.217-edm2-pass-c:0.5>`, `<lora:noobai_ep11_stabilizer_v0.205_fp16:0.7>`, `<lora:9_NGNLStyle:0.7>` |
| 質量標籤 | `absurdres`, `masterpiece`, `newest`, `best quality` |
| 細節標籤 | `detailed eyes`, `detailed background`, `detailed hands`, `detailed clothes` |
| 完美標籤 | `perfect eyes`, `highly detailed face` |
| 風格標籤 | `perfect lighting`, `anime coloring`, `very aesthetic`, `NGNL Style` |

### 保留的標籤

以下角色特徵會被保留：

- **角色標籤：** 角色名稱、角色 LoRA
- **外觀特徵：** 髮色、髮型、眼睛、體型等
- **服裝描述：** 衣服、配飾等
- **表情姿勢：** 表情、站姿等
- **場景設定：** 背景、環境等

## 文件說明

### Python 腳本

| 文件 | 功能 | 需要 API |
|------|------|---------|
| `design_outfit.py` | 完整功能：過濾 + 設計服裝 | ✓ 是 |
| `filter_prompt_only.py` | 僅過濾功能：提取和分析 | ✗ 否 |

### 配置文件

| 文件 | 用途 |
|------|------|
| `.env` | 存儲 GitHub Token（私密） |
| `.env.example` | 配置文件示例 |

### 數據文件

| 文件 | 內容 |
|------|------|
| `test.json` | 原始 Stable Diffusion 配置 |
| `filtered_prompt.txt` | 過濾後的 prompt + 分析 |
| `outfit_design_result.txt` | AI 設計結果 |

### 文檔文件

| 文件 | 內容 |
|------|------|
| `快速開始指南.md` | 設置和使用說明 |
| `README_outfit_designer.md` | 詳細功能說明 |
| `使用說明.md` | 完整文檔 |

## 配置 .env

### 步驟

1. 複製 `.env.example` 為 `.env`
2. 打開 `.env` 文件
3. 添加您的 GitHub Token：
   ```
   GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
4. 保存文件

### 獲取 GitHub Token

1. 訪問 https://github.com/settings/tokens
2. 點擊 "Generate new token" → "Generate new token (classic)"
3. 設置名稱和權限
4. 複製生成的 Token

## 示例工作流

### 完整工作流

```powershell
# 1. 編輯 .env 文件，添加 GitHub Token

# 2. 執行完整功能
python design_outfit.py

# 輸出：
# 原始 Prompt: [顯示完整 prompt]
# 過濾後的 Prompt: [只顯示角色特徵]
# AI 設計的服裝: [GPT-4o 設計的服裝描述]
# 結果已保存到: outfit_design_result.txt
```

### 僅過濾工作流

```powershell
# 1. 執行過濾功能
python filter_prompt_only.py

# 輸出：
# 原始 Prompt: [顯示完整 prompt]
# 過濾後的 Prompt: [只顯示角色特徵]
# 統計信息: [標籤數量、大小減少等]
# 結果已保存到: filtered_prompt.txt
```

## 輸出示例

### 過濾後的 Prompt

```
<lora:rushia:1.5>, rushia_blue, green hair, short hair, flat chest,
red eyes, pupils, bright_pupils, double bun, teen, (solo:1.3),
blue dress, short dress, wide_sleeves, lace, skull hair ornament,
leg_garter, ring, light_blush, seductive_smile, standing,
fantasy, gradient_background, looking_at_viewer, butterfly, (full_shot:1.1)
```

### AI 設計的服裝

```
elegant gothic dress, black lace bodice, flowing purple skirt,
silver chain accessories, skull motif jewelry, black thigh-high
stockings with lace trim, platform ankle boots, gothic lolita style,
dark fantasy aesthetic, intricate embroidery, layered tulle details,
ribbon bow accents, perfect for a mystical character
```

## 進階用法

### 自定義過濾規則

編輯 `design_outfit.py` 或 `filter_prompt_only.py` 中的 `tags_to_remove` 列表：

```python
tags_to_remove = [
    r'你的_自定義_標籤',
    r'另一個_標籤',
    # ...
]
```

### 自定義設計風格

編輯 `design_outfit.py` 中的 `system_prompt`：

```python
system_prompt = """你是一位專業的服裝設計師。
...
你的自定義指示
...
"""
```

### 使用不同的 JSON 文件

修改 `main()` 函數中的 `json_file` 變量：

```python
json_file = r"path\to\your\config.json"
```

## 故障排除

### 問題：`ModuleNotFoundError: No module named 'openai'`

**解決：** 安裝 openai 套件
```powershell
pip install openai
```

### 問題：`ModuleNotFoundError: No module named 'dotenv'`

**解決：** 安裝 python-dotenv 套件
```powershell
pip install python-dotenv
```

### 問題：`錯誤：未找到 GITHUB_TOKEN`

**解決：**
1. 檢查 `.env` 文件是否存在
2. 檢查 `.env` 中是否有 `GITHUB_TOKEN=your_token`
3. 確保 Token 不為空

### 問題：API 返回錯誤

**檢查清單：**
- Token 是否有效？
- 網絡連接是否正常？
- Token 是否有 API 訪問權限？

## 安全建議

⚠️ **重要提示：**

1. **不要提交 `.env` 文件到版本控制**
   - 使用 `.env.example` 作為模板
   - 將 `.env` 添加到 `.gitignore`

2. **保護您的 Token**
   - 不要在公開地方分享 Token
   - 不要在命令行歷史中暴露 Token
   - 定期檢查和更新 Token

3. **Token 暴露處理**
   - 立即在 GitHub 設置中刪除該 Token
   - 生成新的 Token
   - 更新本地 `.env` 文件

## 許可證和貢獻

詳見相關文檔。

## 聯繫和支持

如有問題，請參考 [快速開始指南.md](快速開始指南.md)。
