# ComfyUI 版本改寫說明

## 📋 改寫內容總結

### 主要變更

1. **API 架構改變**
   - **原版**：使用 Stable Diffusion WebUI 的 HTTP POST API (`/sdapi/v1/txt2img`)
   - **新版**：使用 ComfyUI 的 WebSocket + HTTP API

2. **工作流處理**
   - **原版**：使用簡單的 JSON 配置（`test.json`），包含 prompt、steps、sampler 等參數
   - **新版**：使用 ComfyUI 節點式工作流（`qwen image (1).json`），通過替換節點 6 的 text 輸入來更新正面提示詞

3. **圖片獲取方式**
   - **原版**：從 API 響應直接獲取 base64 編碼的圖片
   - **新版**：通過 WebSocket 監聽執行狀態，完成後從 `/history` 端點獲取圖片信息，再從 `/view` 端點下載圖片

## 🔧 關鍵技術實現

### ComfyUIClient 類

```python
class ComfyUIClient:
    """ComfyUI WebSocket 客戶端"""
    
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())  # 每個客戶端有唯一 ID
```

#### 主要方法：

1. **queue_prompt()** - 提交工作流到隊列
   ```python
   POST http://127.0.0.1:8188/prompt
   Body: {"prompt": workflow_json, "client_id": client_id}
   ```

2. **get_images()** - WebSocket 監聽 + 圖片下載
   - 連接 WebSocket：`ws://127.0.0.1:8188/ws?clientId={client_id}`
   - 監聽 `executing` 消息，等待 `node=None` 表示完成
   - 從 `/history/{prompt_id}` 獲取輸出信息
   - 從 `/view?filename=...&subfolder=...&type=...` 下載圖片

3. **get_image()** - 下載單張圖片
4. **get_history()** - 獲取任務歷史

### AutoCharacterGenerator 類改動

#### 新增/修改的方法：

1. **load_workflow_from_json()** - 載入 ComfyUI 工作流
   ```python
   # 替代原來的 load_config_from_json()
   workflow = load_workflow_from_json("qwen image (1).json")
   ```

2. **replace_prompt_in_workflow()** - 替換工作流中的提示詞
   ```python
   # 節點 6 是 CLIPTextEncode (正面提示詞)
   workflow["6"]["inputs"]["text"] = new_prompt
   
   # 節點 3 是 KSampler (隨機種子)
   workflow["3"]["inputs"]["seed"] = random.randint(...)
   ```

3. **generate_image()** - 調用 ComfyUI API
   ```python
   # 使用 client.get_images() 替代原來的 requests.post()
   output_images = self.client.get_images(workflow)
   ```

4. **save_images()** - 保存圖片（邏輯保持不變）

## 📁 工作流結構分析

### qwen image (1).json 關鍵節點

```json
{
  "3": {  // KSampler - 採樣器
    "inputs": {
      "seed": 278079777675,
      "steps": 12,
      "cfg": 1,
      "sampler_name": "dpmpp_2m_sde_gpu",
      ...
    }
  },
  "6": {  // CLIPTextEncode - 正面提示詞 ⭐ 需要替換
    "inputs": {
      "text": "...",  // 這裡是要替換的提示詞
      "clip": ["38", 0]
    }
  },
  "7": {  // CLIPTextEncode - 負面提示詞（不需修改）
    "inputs": {
      "text": "EasyNegative,...",
      ...
    }
  },
  "60": {  // SaveImage - 保存圖片
    "inputs": {
      "filename_prefix": "qwen/2026-01-23/test",
      ...
    }
  }
}
```

## 🔄 API 流程對比

### 原版 (SD WebUI)
```
1. POST /sdapi/v1/txt2img
   ↓
2. 同步等待生成完成
   ↓
3. 響應返回 base64 圖片
   ↓
4. 解碼並保存
```

### 新版 (ComfyUI)
```
1. POST /prompt (提交工作流)
   ↓ 獲得 prompt_id
2. WebSocket 監聽執行狀態
   ↓ message['type'] == 'executing'
3. 檢測 data['node'] == None (完成)
   ↓
4. GET /history/{prompt_id}
   ↓ 獲取輸出節點信息
5. GET /view?filename=... (下載圖片)
   ↓
6. 保存圖片
```

## 🚀 使用方法

### 1. 確保依賴已安裝

```bash
pip install websocket-client openai python-dotenv pillow
```

### 2. 確保 ComfyUI 正在運行

```bash
cd /data/RushiaMode/ComfyUI
python main.py
# 默認運行在 http://127.0.0.1:8188
```

### 3. 運行新程式

```bash
cd Api
python auto_character_generator_comfyui.py
```

### 4. 輸入要生成的角色數量

```
請輸入要生成的角色數量（1-20）: 3
```

## ⚙️ 配置文件

### .env 文件（與原版相同）

```env
NVIDIA_API_KEY=your_key_here
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL_NAME=meta/llama-3.1-405b-instruct
```

### qwen image (1).json（工作流配置）

- 所有參數（steps, cfg, sampler, model, lora 等）都保留原樣
- 只替換節點 6 的 `text` 輸入
- 自動生成新的隨機種子

## 🎯 功能保持一致

### 保留的功能
- ✅ 隨機抽取角色類型
- ✅ AI 設計角色（Nvidia API）
- ✅ 批次生成
- ✅ 按日期分類保存
- ✅ 自動編號
- ✅ 詳細的進度顯示

### 改進的地方
- ✅ 支持 ComfyUI 的完整工作流
- ✅ 可以使用 qwen_image 等特殊模型
- ✅ WebSocket 實時監控執行狀態
- ✅ 更靈活的工作流配置

## 🔍 調試技巧

### 查看 ComfyUI 日志

```bash
# 在 ComfyUI 控制台可以看到工作流執行情況
# 如果出錯會顯示詳細的錯誤信息
```

### 測試連接

```python
import urllib.request
response = urllib.request.urlopen("http://127.0.0.1:8188/system_stats")
print(response.read())
```

### 手動測試工作流

```bash
# 使用 ComfyUI 的官方示例腳本
cd /data/RushiaMode/ComfyUI/script_examples
python websockets_api_example.py
```

## 📝 注意事項

1. **工作流 JSON 路徑**：確保 `qwen image (1).json` 在 Api 目錄下
2. **ComfyUI 端口**：默認是 8188，如果修改過需要相應調整
3. **節點 ID**：如果工作流結構不同，需要修改 `replace_prompt_in_workflow()` 中的節點 ID
4. **輸出目錄**：圖片保存在 `outputs/YYYY-MM-DD/` 下

## 🆚 兩個版本對比

| 特性 | 原版 (SD WebUI) | 新版 (ComfyUI) |
|------|----------------|----------------|
| API 類型 | HTTP POST | WebSocket + HTTP |
| 配置格式 | 簡單 JSON | 節點式工作流 |
| 模型支持 | SD 1.5/SDXL | 任意 ComfyUI 模型 |
| 靈活性 | 低 | 高 |
| 複雜度 | 簡單 | 中等 |
| 實時監控 | 無 | 有 (WebSocket) |

## 🎉 總結

新版本完全適配 ComfyUI API，支持使用 qwen_image 工作流生成圖片。所有核心功能保持不變，只是底層 API 從 SD WebUI 切換到了 ComfyUI。
