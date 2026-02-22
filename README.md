# 🎨 動漫角色自動化抽獎設計助手與 Prompt 編輯器 - Stable Diffusion AI

這個專案是一套專為 Stable Diffusion 設計的自動化工具集，結合了高效能 AI 模型（Nvidia API / Gemini 3）與強大的提示詞（Prompt）處理能力。無論是從零啟動的「自動抽獎設計」，還是對現有提示詞進行「外科手術式精準修改」，都能輕鬆完成。

---

## 🎲 核心組件

### 1. 🖥️ Gradio WebUI 提示詞編輯器 (`prompt_editor_ui.py`)
為了解決傳統編輯 Prompt 的痛點，我們開發了直觀的 Web 介面。
- **互動式編輯**：輸入現有 Prompt 與修改想法，AI 自動進行精準替換。
- **LoRA 即時偵測**：自動識別並以彩色標籤顯示 Prompt 中的 LoRA，確保核心特徵不被誤刪。
- **內建生成畫廊**：直接在瀏覽器預覽 Stable Diffusion 生成結果，無需頻繁切換資料夾。
- **修改差異分析**：清楚顯示每個標籤（Tags）的新增、移除與保留狀態。

### 2. 🎰 全自動角色抽獎生成器 (`auto_character_generator.py`)
一鍵完成從「點子」到「美圖」的所有步驟。
- **隨機抽獎系統**：從多種角色類型（清純、成熟、活潑等）中隨機抽取主題。
- **AI 角色設計**：由 qwen3-next-80b-a3b-instruct 或 Gemini 3 設計完整的外貌、服裝、配件與場景氛圍。
- **批量生圖**：支援一次設置生成 1-20 個不同角色，適合大批量尋找靈感。
- **自動化存檔**：按日期分類保存圖片、Prompt 紀錄與 AI 設計日誌。

### 3. 🧪 提示詞過濾工具 (`filter_prompt_only.py`)
- **零成本本地處理**：無需 API Key，快速提取角色特徵。
- **標籤分類**：依據服裝、姿勢、背景等類別對 Raw Prompt 進行結構化分析。

---

## ⚡ 技術亮點

### 🛡️ 多模型備用機制 (Multi-Model Fallback)
為了確保 AI 設計過程不因網路或伺服器超時而中斷，系統實作了智慧型備用機制：
- **超時門檻**：設定 30-120 秒超時自動判定。
- **自動切換**：主模型（如 Llama-3.3）失敗或超時時，自動嘗試備用清單中的模型（如 Qwen3, Nemotron, GPT-OSS 等）。
- **重試邏輯**：每個模型獨立重試，直到成功或清單用罄。

### 🚀 Nvidia / Gemini 雙引擎支援
- **Nvidia API**：提供極速且高品質的大型語言模型支援。
- **Gemini 3 Flash**：做為強而有力的備援，具備出色的上下文理解能力。

---

## 🚀 快速開始

### 1. 配置環境變數

複製 `.env.example` 並更名為 `.env`，填入您的 API Key：

```dotenv
# Nvidia API
NVIDIA_API_KEY=your_nvidia_api_key_here

# Gemini API (可選備用)
GEMINI_API_KEY=your_gemini_api_key_here

# Stable Diffusion WebUI 地址
SD_WEBUI_URL=http://127.0.0.1:7860
```

---

## 📁 項目結構

```
Api/
├── prompt_editor_ui.py           # Gradio Web 介面入口
├── auto_character_generator.py    # 批量自動生成腳本
├── prompt_editor.py              # AI 提示詞修改核心邏輯
├── filter_prompt_only.py         # 本地提示詞過濾工具
├── test.json                     # Stable Diffusion 生成參數設定
├── .env                          # 您的 API Key 與設定 (請勿上傳)
├── docs/                         # 詳細更新說明與設計日誌
└── outputs/                      # 生成結果存放處 (按日期自動分類)
```

---

## 🛠️ 建議工作流

1. **大批量探索**：執行 `auto_character_generator.py` 進行大批量隨機設計，直到看到心儀的角色原型。
2. **精準調優**：將心儀角色的 Prompt 放入 `prompt_editor_ui.py`。
3. **AI 二次修改**：與 AI 對話（例如：「換成哥德蘿莉風格」、「加上眼鏡」），即時生成對比圖片。

---

## 📋 注意事項

- ⚠️ **API 安全**：請務必將 `.env` 加入 `.ignore`，不要分享您的 Key。
- 🔧 **SD 配置**：如果是遠端 SD WebUI，請確保 `SD_WEBUI_URL` 正確且防火牆已開啟。
- 📦 **棄用說明**：原 GitHub Models API 配置已由 Nvidia API 取代。

---

## 📝 授權與貢獻
本專案採用 MIT 授權。歡迎提交 Issue 或 Pull Request 分享您的標籤配置或改進建議！












