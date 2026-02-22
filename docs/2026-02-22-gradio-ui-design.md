# Gradio WebUI 設計計劃書
> 建立日期：2026-02-22  
> 目標檔案：`prompt_editor_ui.py`  
> 對應重構：基於現有 `prompt_editor.py` 的 `PromptEditor` class，**原 CLI 版本保留不動**

---

## 1. 背景與動機

### 現有 CLI 痛點

| 痛點 | 具體表現 |
|------|----------|
| 輸入體驗差 | terminal 貼入多行 prompt 容易亂行，需按兩次 Enter 才能確認 |
| 看不到生成圖 | 生完只顯示路徑，要手動開檔案總管找圖 |
| 無法對比嘗試結果 | 多次嘗試的圖分散在資料夾，難以一眼比較 |
| 無歷史紀錄 | 每次執行結束後修改過程消失，無法回溯或 undo |

### 為什麼選 Gradio

1. **生態吻合**：SD WebUI 本身即是 Gradio 架構，`7860` 與 `7861` 並排開在瀏覽器，體驗一致
2. **內建 Gallery**：`gr.Gallery` 原生支援圖片顯示與並排比較，不需要自己排版
3. **改造成本低**：現有 `PromptEditor` class 完全不動，只需包一層 Gradio callback
4. **跨主題美觀**：`gr.themes.Soft()` 開箱即用，不需要寫 CSS

---

## 2. 整體架構

```
prompt_editor_ui.py          ← 新建（Gradio 前端 + callback 層）
      │
      ▼  import 並實例化
prompt_editor.py             ← 保留原檔不動
      ├── PromptEditor class
      │     ├── edit_prompt_with_ai()
      │     ├── generate_image()
      │     ├── save_images()
      │     └── check_sd_connection()
      └── EDITOR_SYSTEM_PROMPT
```

**設計原則**：`prompt_editor_ui.py` 只負責 UI 呈現與使用者互動，所有 AI 呼叫、SD 生成、LoRA 保護邏輯均維持在 `PromptEditor` 中。

---

## 3. 版面設計

### 3.1 整體佈局

```
┌─────────────────────────────────────────────────────────────────┐
│  ✏️ Stable Diffusion Prompt 精準編輯器           [SD 連線狀態]   │
├────────────────────────────┬────────────────────────────────────┤
│  📝 左欄：輸入區（1/3）      │  🖼️ 右欄：輸出區（2/3）             │
│                            │                                    │
│  [現有 Prompt ___________] │  ┌──────────────────────────────┐ │
│  [                       ] │  │   Gallery（本輪生成結果）      │ │
│  [  10 行文字框           ] │  │   ┌──┐ ┌──┐ ┌──┐            │ │
│  [_____________________ ] │  │   │ 1│ │ 2│ │ 3│            │ │
│                            │  │   └──┘ └──┘ └──┘            │ │
│  LoRA 偵測結果（badges）    │  └──────────────────────────────┘ │
│  🔴 <lora:Rem:1>           │                                    │
│  🟡 <lora:add_detail:1>    │  修改後 Prompt（唯讀 + 可複製）      │
│                            │  [_____________________________]   │
│  [修改想法 _____________]  │                                    │
│  [  3 行文字框           ]  │  標籤差異分析                       │
│  [_____________________ ] │  ✅ 保留 24  🗑️ 移除 5  ✨ 新增 8   │
│                            │  [詳細 diff 文字區]                 │
│  嘗試次數  [1 ──●── 5]      │                                    │
│                            │                                    │
│  [  🎨 AI 修改並生圖  ]     │                                    │
│                            │                                    │
├────────────────────────────┴────────────────────────────────────┤
│  ▼ 🕐 修改歷史（Accordion，預設收合）                             │
│  時間       │ 修改想法     │ Prompt 摘要（前 80 字）│ 圖片數       │
│  10:32:14  │ 換成水手服   │ <lora:Rem:1> sailor.. │  3          │
│  10:45:02  │ 換成忍者裝   │ <lora:Rem:1> kunoic.. │  2          │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 元件清單

| 元件 ID | 類型 | 說明 |
|---------|------|------|
| `prompt_box` | `gr.Textbox(lines=10)` | 現有 Prompt 輸入，支援直接貼上多行 |
| `lora_display` | `gr.HTML` | 動態顯示偵測到的 LoRA badge（偵測發生在 prompt 輸入後） |
| `idea_box` | `gr.Textbox(lines=3)` | 修改想法輸入 |
| `attempts_slider` | `gr.Slider(1, 5, step=1)` | 嘗試次數，預設 1 |
| `run_btn` | `gr.Button(variant="primary")` | 執行按鈕 |
| `sd_status` | `gr.HTML` | 右上角 SD 連線狀態 badge |
| `gallery` | `gr.Gallery(columns=3)` | 本輪所有嘗試的生成結果 |
| `out_prompt` | `gr.Textbox` | 最後一次修改後的完整 Prompt（唯讀） |
| `diff_box` | `gr.Textbox` | 標籤差異分析文字輸出 |
| `history_table` | `gr.Dataframe` | 歷史紀錄表（時間、想法、摘要、圖片數） |
| `history_accordion`| `gr.Accordion` | 包住 history_table，預設收合 |

---

## 4. 資料流

### 4.1 主執行流程

```
使用者點擊「AI 修改並生圖」
    │
    ▼
run_edit_and_generate(prompt_box, idea_box, attempts_slider)
    │
    ├── 呼叫 editor.check_sd_connection()
    │
    ├── for attempt in range(1, attempts + 1):
    │     │
    │     ├── editor.edit_prompt_with_ai(prompt, idea, attempt, total)
    │     │     └── 回傳 (modified_prompt, ai_metadata)
    │     │
    │     ├── 若 SD 可用：editor.generate_image(payload)
    │     │     └── 回傳 response
    │     │
    │     ├── editor.save_images(response, metadata)
    │     │     └── 儲存圖片 + .txt 到 session_dir
    │     │
    │     └── 收集圖片路徑到 images_list
    │
    ├── yield 進度更新（使用 gr.Progress 或即時 yield 圖片列表）
    │
    └── 回傳 (images_list, out_prompt, diff_text, new_history_row)
```

### 4.2 LoRA 即時偵測流程（輸入框 change 事件）

```
使用者在 prompt_box 輸入/貼上 prompt
    │
    ▼
on_prompt_change(prompt_text)
    │
    ├── extract_lora_tags(prompt_text)
    │
    └── 回傳 HTML badge 字串給 lora_display
```

---

## 5. Gradio State 設計

```python
# session 級別的狀態（每次頁面刷新重置）
history_state = gr.State([])   # List[dict]，儲存所有輪次記錄
editor_state  = gr.State(None) # PromptEditor 實例，在首次觸發時初始化
```

每輪記錄的結構：

```python
{
    "time":        "10:32:14",
    "idea":        "換成水手服",
    "prompt_head": "<lora:Rem:1> sailor uniform...",  # 前 80 字
    "image_count": 3
}
```

---

## 6. SD 未連線時的降級處理

| 情況 | 行為 |
|------|------|
| SD 未連線 | `sd_status` 顯示紅色 badge；執行後 gallery 空白，但仍顯示修改後 prompt 與 diff |
| AI 所有提供商失敗 | 在 `diff_box` 顯示錯誤訊息，gallery 空白 |
| 部分嘗試失敗 | 成功的圖片照常顯示，失敗的嘗試在 diff_box 記錄說明 |

---

## 7. .env 需要的環境變數（與現有相同，無新增）

```env
# AI 提供商（至少設定一個）
GEMINI_API_KEY=
GEMINI_BASE_URL=
GEMINI_MODEL_NAME=
GEMINI_BACKUP_MODELS=
GEMINI_API_TIMEOUT=60

NVIDIA_API_KEY=
NVIDIA_BASE_URL=
NVIDIA_MODEL_NAME=
NVIDIA_BACKUP_MODELS=
NVIDIA_API_TIMEOUT=60

# Stable Diffusion WebUI
SD_WEBUI_URL=http://127.0.0.1:7860   # 可選，預設此值
```

新增一個可選變數：`SD_WEBUI_URL`，讓使用者不必修改程式碼即可指定 SD 位址。

---

## 8. 啟動方式

```powershell
# 安裝依賴（僅需新增 gradio）
pip install gradio

# 啟動 Gradio UI
python prompt_editor_ui.py
# 瀏覽器開啟 http://127.0.0.1:7861
```

---

## 9. 檔案結構變更（最小侵入）

```
Api/
├── prompt_editor.py          ← ✅ 保留不動（CLI 版仍可用）
├── prompt_editor_ui.py       ← 🆕 新建（Gradio WebUI）
├── .env                      ← 無需修改
├── test.json                 ← 無需修改
└── docs/
    └── 2026-02-22-gradio-ui-design.md  ← 本計劃書
```

---

## 10. 實作步驟拆解

### Phase 1：骨架（可先跑起來看版面）
- [x] 建立 `prompt_editor_ui.py`
- [x] 引入 `PromptEditor`，在 Gradio 啟動時初始化 `editor` 實例
- [x] 排好 `gr.Blocks` 三區（左欄輸入 / 右欄輸出 / 底部歷史）
- [x] 放好所有元件（先不接 callback）
- [x] 確認 `app.launch(port=7861)` 能正常開啟

### Phase 2：LoRA 即時偵測
- [x] 實作 `on_prompt_change()` 函數
- [x] 用正規表達式偵測 LoRA，回傳 HTML badge
- [x] 綁定到 `prompt_box.change` 事件

### Phase 3：主 callback 串接
- [x] 實作 `run_edit_and_generate()` 函數
- [x] 串接 `edit_prompt_with_ai()` + `generate_image()` + `save_images()`
- [x] 將圖片路徑列表送入 `gallery`
- [x] 將 `show_prompt_diff()` 的輸出轉成字串送入 `diff_box`
- [x] 處理 SD 未連線時的降級

### Phase 4：歷史紀錄
- [x] 用 `gr.State` 維護 `history_state`
- [x] 每輪結束後 append 紀錄並更新 `history_table`
- [x] 確認 Accordion 收合/展開正常

### Phase 5：細節打磨
- [x] SD 連線狀態 badge（綠/紅 HTML）
- [x] `run_btn` 執行中禁用（避免重複點擊）
- [x] 整體主題確認（`gr.themes.Soft()`）
- [x] 測試貼入有換行符的 prompt 是否正常處理

---

## 11. 技術風險與解法

| 風險 | 解法 |
|------|------|
| Gradio callback 阻塞 UI（生圖很慢） | 使用 `gr.Button` 搭配 `queue=True` + `yield` 分段回傳，讓 Gallery 逐張顯示 |
| `PromptEditor` 每次 callback 都重新初始化（建立新 session 資料夾） | 用 `gr.State` 快取 `editor` 實例，確保一次頁面載入只初始化一次 |
| Gradio `Gallery` 顯示本地路徑圖片 | 直接傳入 PIL Image 物件列表，不依賴路徑，避免路徑權限問題 |
| `show_prompt_diff()` 輸出有顏色 ANSI 碼 | 重包一個 `get_diff_text()` 函數，回傳純文字字串給 Gradio 顯示 |
