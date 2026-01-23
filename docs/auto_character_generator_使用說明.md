# 🎲 自動角色抽獎生成器使用說明

## 📋 功能概述

**auto_character_generator.py** - 全自動動漫角色生成器

整合了兩個程序的功能：
1. **design_outfit.py** - AI 角色設計
2. **sd_automation.py** - Stable Diffusion 自動化

## ✨ 完整工作流程

```
1. 隨機抽取角色類型 (5種)
   ↓
2. GPT-4o 設計完整角色
   ↓
3. 添加質量增強標籤
   ↓
4. 從 test.json 讀取配置
   ↓
5. 替換 prompt（保留其他參數）
   ↓
6. 發送到 Stable Diffusion
   ↓
7. 自動保存生成的圖片
```

## 🚀 快速開始

### 前置要求

1. **Stable Diffusion WebUI** 必須正在運行
   ```bash
   # 默認地址：http://127.0.0.1:7860
   ```

2. **.env 配置**
   ```
   GITHUB_TOKEN=your_token_here
   ```

3. **Python 套件**
   ```bash
   pip install openai python-dotenv requests pillow
   ```

4. **test.json 配置文件**
   - 必須存在於同目錄
   - 包含完整的 SD 參數配置

### 運行方式

```bash
# 運行一次，生成一個隨機角色
python auto_character_generator.py

# 多次運行，生成多個不同角色
python auto_character_generator.py
python auto_character_generator.py
python auto_character_generator.py
```

## 📊 程序特點

### ✅ 自動化功能

| 功能 | 說明 |
|------|------|
| 🎲 隨機抽獎 | 從 5 種角色類型中隨機選擇 |
| 🤖 AI 設計 | GPT-4o 設計完整角色（外貌+服裝+場景） |
| ✨ 質量標籤 | 自動添加 LoRA 和質量增強標籤 |
| 🔄 參數保留 | 完整保留 test.json 中的所有參數 |
| 🎯 提示詞替換 | 只替換 prompt，其他不動 |
| 🎰 隨機種子 | 自動生成 10 位隨機種子 |
| 💾 自動保存 | 圖片自動保存到 outputs/ |
| 🏷️ 智能命名 | 文件名包含角色類型和時間戳 |

### 🎯 保留的參數

從 test.json 完整保留：
- ✅ 圖片尺寸 (width, height)
- ✅ 採樣器設定 (sampler_name, steps, cfg_scale)
- ✅ 批次設定 (batch_size, n_iter)
- ✅ Hires Fix 設定
- ✅ 所有 alwayson_scripts（ADetailer, ControlNet 等）
- ✅ 其他所有參數

### 🔄 替換的內容

僅替換兩個：
- ❌ **prompt** → 使用 AI 生成的新角色
- ❌ **seed** → 自動生成隨機種子

## 📁 輸出文件

### 文件命名格式

```
[角色類型]_[時間戳]_[序號].png
```

**示例：**
```
清純少女_20260123_113438_1.png
可愛少女_20260123_114521_1.png
成熟女性_20260123_113302_1.png
優雅女性_20260123_120015_1.png
活潑少女_20260123_121234_1.png
```

### 輸出位置

所有圖片保存在：
```
outputs/
```

## 🎲 角色類型

| 編號 | 類型 | 英文 | 年齡 |
|------|------|------|------|
| 1 | 清純少女 | innocent young girl | 15-17 |
| 2 | 可愛少女 | cute girl, youthful | 16-18 |
| 3 | 成熟女性 | mature woman, adult | 25-30 |
| 4 | 優雅女性 | elegant woman, sophisticated | 28-35 |
| 5 | 活潑少女 | energetic girl, cheerful | 17-19 |

## 🎨 AI 設計內容

每個角色包含：

1. **基本設定** - 年齡、氣質、風格
2. **髮型** - 顏色、長度、樣式、髮飾
3. **面部** - 眼睛、表情、細節
4. **身材** - 體型、身高
5. **服裝** - 上衣、下裝、外套、材質
6. **配飾** - 項鍊、耳環、手鐲等
7. **鞋子** - 款式、顏色
8. **姿勢** - 站姿、動作
9. **場景** - 背景、氛圍、環境

## 📝 使用示例

### 示例 1：基本使用

```bash
# 1. 確保 SD WebUI 正在運行
# 2. 檢查 .env 文件有 Token
# 3. 運行程序
python auto_character_generator.py

# 輸出：
# ✅ 抽中：可愛少女
# ✅ AI 設計完成
# ✅ 圖片生成完成
# ✅ 保存：可愛少女_20260123_114521_1.png
```

### 示例 2：批量生成

```powershell
# 生成 5 個不同的角色
for ($i=1; $i -le 5; $i++) {
    python auto_character_generator.py
    Start-Sleep -Seconds 5
}
```

### 示例 3：修改 SD 地址

編輯 `auto_character_generator.py`：

```python
generator = AutoCharacterGenerator(
    sd_url="http://192.168.1.100:7860",  # 改這裡
    output_dir="outputs"
)
```

### 示例 4：修改輸出目錄

```python
generator = AutoCharacterGenerator(
    sd_url="http://127.0.0.1:7860",
    output_dir="my_characters"  # 改這裡
)
```

## ⚙️ 自定義設置

### 添加新的角色類型

編輯 `CHARACTER_TYPES` 列表：

```python
CHARACTER_TYPES = [
    "清純少女 (innocent young girl, teenage, 15-17 years old)",
    "可愛少女 (cute girl, youthful, 16-18 years old)",
    "成熟女性 (mature woman, adult, 25-30 years old)",
    "優雅女性 (elegant woman, sophisticated, 28-35 years old)",
    "活潑少女 (energetic girl, cheerful, 17-19 years old)",
    # 添加您的自定義類型
    "知性女性 (intellectual woman, 28-32 years old)",
    "運動少女 (athletic girl, 18-20 years old)",
]
```

### 修改質量標籤

編輯 `QUALITY_TAGS` 常量：

```python
QUALITY_TAGS = "你的自定義標籤,"
```

### 調整 AI 創意度

修改 `temperature` 參數（0.7-1.0）：

```python
temperature=0.9,  # 越高越有創意
```

## 🔧 故障排除

### 問題 1：無法連接到 SD WebUI

**錯誤：**
```
❌ 無法連接到 SD WebUI: http://127.0.0.1:7860
```

**解決：**
1. 確認 SD WebUI 是否正在運行
2. 檢查地址和端口是否正確
3. 檢查防火牆設置

### 問題 2：未找到 GITHUB_TOKEN

**錯誤：**
```
❌ 錯誤：未找到 GITHUB_TOKEN
```

**解決：**
1. 檢查 `.env` 文件是否存在
2. 確認文件中有 `GITHUB_TOKEN=你的token`
3. Token 是否有效

### 問題 3：找不到 test.json

**錯誤：**
```
❌ 載入 JSON 失敗
```

**解決：**
1. 確認 `test.json` 在同目錄
2. 檢查 JSON 格式是否正確
3. 確認文件編碼為 UTF-8

### 問題 4：生成超時

**錯誤：**
```
❌ 請求超時！生成時間過長
```

**解決：**
1. 降低圖片尺寸
2. 減少採樣步數
3. 關閉耗時的插件（ADetailer、ControlNet等）
4. 修改超時時間（編輯代碼中的 `timeout=300`）

## 📊 性能優化

### 加快生成速度

1. **降低圖片尺寸**
   - 在 test.json 中調整 width 和 height

2. **減少採樣步數**
   - 降低 steps（建議 20-30）

3. **關閉不需要的插件**
   - 在 test.json 中禁用 ADetailer、ControlNet 等

4. **使用更快的採樣器**
   - DPM++ 2M Karras
   - Euler a

### 提高圖片質量

1. **增加採樣步數**
   - 提高 steps（建議 40-60）

2. **啟用 Hires Fix**
   - 在 test.json 中設置 `"enable_hr": true`

3. **使用質量更好的採樣器**
   - DPM++ 2M Karras
   - DPM++ SDE Karras

## 💡 進階用法

### 1. 集成到工作流

```python
from auto_character_generator import AutoCharacterGenerator

# 創建生成器
gen = AutoCharacterGenerator()

# 生成多個角色
for i in range(10):
    gen.run()
```

### 2. 自定義後處理

在 `save_images` 方法後添加：

```python
# 添加水印
# 調整顏色
# 應用濾鏡
```

### 3. 保存角色信息

修改代碼保存角色描述：

```python
# 保存角色信息到 JSON
with open('character_info.json', 'w') as f:
    json.dump({
        'type': character_type,
        'design': character_design,
        'seed': config['seed']
    }, f)
```

## 📄 相關文件

- `auto_character_generator.py` - 主程序（新）
- `design_outfit.py` - 原角色設計腳本（已整合）
- `sd_automation.py` - 原 SD 自動化腳本（已整合）
- `test.json` - SD 參數配置
- `.env` - 環境變數配置
- `outputs/` - 輸出目錄

## 🎯 與舊程序的區別

| 功能 | 舊程序 | 新程序 |
|------|--------|--------|
| 角色設計 | design_outfit.py | ✅ 整合 |
| SD 生成 | sd_automation.py | ✅ 整合 |
| 生成 txt | ✅ | ❌ 不生成 |
| 讀取 JSON | 分別處理 | ✅ 統一處理 |
| 替換 prompt | 手動 | ✅ 自動 |
| 保留參數 | 部分 | ✅ 完整保留 |
| 自動化程度 | 需多步 | ✅ 一鍵完成 |

## 📝 總結

**auto_character_generator.py** 是一個完全自動化的解決方案：

✅ 一鍵運行
✅ 隨機抽獎
✅ AI 設計
✅ 自動生成
✅ 智能保存
✅ 無需手動操作

**適用場景：**
- 快速生成大量角色立繪
- 角色設計靈感來源
- 自動化批量生產
- 測試不同風格
- 角色資源庫建立

---

**快速開始：**
```bash
python auto_character_generator.py
```

就這麼簡單！🎉
