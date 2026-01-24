# 🎯 程式使用指南 - ComfyUI 版本

## 📝 程式分析

### 原版程式（auto_character_generator.py）

**使用的 API**: Stable Diffusion WebUI API

**工作流程**:
1. 隨機抽取角色類型
2. 使用 Nvidia API (GPT) 設計角色描述
3. 組合質量標籤 + 角色描述 = 完整 prompt
4. 發送到 SD WebUI API (`/sdapi/v1/txt2img`)
5. 接收 base64 編碼的圖片
6. 解碼並保存

**配置文件**: `test.json`
```json
{
  "prompt": "...",
  "negative_prompt": "...",
  "steps": 20,
  "sampler_name": "Euler a",
  "width": 512,
  "height": 768,
  ...
}
```

### 新版程式（auto_character_generator_comfyui.py）

**使用的 API**: ComfyUI WebSocket + HTTP API

**工作流程**:
1. 隨機抽取角色類型（相同）
2. 使用 Nvidia API (GPT) 設計角色描述（相同）
3. 載入 ComfyUI 工作流 JSON
4. 替換節點 6 的正面提示詞
5. 通過 WebSocket 提交並監聽執行狀態
6. 從 `/history` 和 `/view` 端點獲取圖片
7. 保存圖片

**配置文件**: `qwen image (1).json` - ComfyUI 工作流

## 🔄 關鍵變更點

### 1. API 客戶端

**原版**:
```python
def generate_image(self, payload):
    api_url = f"{self.sd_url}/sdapi/v1/txt2img"
    response = requests.post(api_url, json=payload, timeout=300)
    return response.json()
```

**新版**:
```python
class ComfyUIClient:
    def get_images(self, prompt):
        # 1. 連接 WebSocket
        ws = websocket.WebSocket()
        ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
        
        # 2. 提交工作流
        prompt_id = self.queue_prompt(prompt)['prompt_id']
        
        # 3. 監聽執行狀態
        while True:
            out = ws.recv()
            message = json.loads(out)
            if message['type'] == 'executing' and message['data']['node'] is None:
                break  # 完成
        
        # 4. 獲取圖片
        history = self.get_history(prompt_id)
        # ... 下載圖片
```

### 2. 工作流配置

**原版** - 簡單配置:
```python
config = {
    "prompt": full_prompt,
    "negative_prompt": "bad quality...",
    "steps": 20,
    "width": 512,
    "height": 768,
    ...
}
```

**新版** - 節點式工作流:
```python
workflow = {
    "3": {  # KSampler
        "inputs": {"seed": 123, "steps": 12, ...}
    },
    "6": {  # CLIPTextEncode (正面提示詞)
        "inputs": {"text": character_description, ...}
    },
    "7": {  # CLIPTextEncode (負面提示詞)
        "inputs": {"text": "bad quality...", ...}
    },
    ...
}

# 只需要替換節點 6 的 text
workflow["6"]["inputs"]["text"] = new_prompt
```

### 3. 提示詞處理

**原版**:
```python
QUALITY_TAGS = "<lora:...>,masterpiece,..."
complete_prompt = QUALITY_TAGS + character_design
```

**新版**:
```python
# 質量標籤已經在工作流中通過 LoRA 和其他節點配置
# 只需要純角色描述
workflow["6"]["inputs"]["text"] = character_design
```

## 📋 qwen image (1).json 工作流分析

### 關鍵節點結構

```json
{
  "37": {
    "class_type": "UNETLoader",
    "inputs": {
      "unet_name": "qwen_image_fp8_e4m3fn.safetensors"
    }
  },
  "38": {
    "class_type": "CLIPLoader",
    "inputs": {
      "clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors"
    }
  },
  "76": {
    "class_type": "LoraLoaderModelOnly",
    "inputs": {
      "lora_name": "Qwen-Image-Lightning-4steps-V2.0.safetensors"
    }
  },
  "6": {  // ⭐ 這是我們要修改的節點
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "原始提示詞...",  // 替換這裡
      "clip": ["38", 0]
    }
  },
  "3": {  // ⭐ 自動更新隨機種子
    "class_type": "KSampler",
    "inputs": {
      "seed": 278079777675,  // 替換這裡
      "steps": 12,
      ...
    }
  },
  "60": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "qwen/2026-01-23/test"
    }
  }
}
```

### 節點關係圖

```
37 (UNETLoader) ─┐
                  ├─> 78 (LoRA) -> 76 (LoRA) -> 66 (ModelSampling) -> 3 (KSampler)
                  │
38 (CLIPLoader) ──┼─> 6 (正面提示詞) ─────────────────────────┘
                  │
                  └─> 7 (負面提示詞) ─────────────────────────┘
                  
3 (KSampler) -> 8 (VAEDecode) -> 60 (SaveImage)
```

## 🚀 使用步驟

### 1. 環境準備

```bash
# 安裝依賴
pip install websocket-client openai python-dotenv pillow requests

# 確保 .env 文件配置正確
cat .env
# NVIDIA_API_KEY=your_key
# NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
# NVIDIA_MODEL_NAME=meta/llama-3.1-405b-instruct
```

### 2. 啟動 ComfyUI

```bash
cd /data/RushiaMode/ComfyUI
python main.py

# 預期輸出:
# To see the GUI go to: http://127.0.0.1:8188
```

### 3. 測試連接

```bash
cd Api
python test_comfyui.py
```

預期輸出:
```
🧪 ComfyUI 版本測試套件

==================================================================
🔌 測試 ComfyUI 連接
==================================================================
✅ ComfyUI 連接成功！

==================================================================
📄 測試工作流載入
==================================================================
✅ 工作流載入成功
✅ 找到節點 6 (正面提示詞)
✅ 找到節點 3 (KSampler)

==================================================================
🔄 測試提示詞替換
==================================================================
✅ 提示詞替換成功

🎉 所有測試通過！可以開始使用程式了。
```

### 4. 運行主程式

```bash
python auto_character_generator_comfyui.py
```

輸入示例:
```
請輸入要生成的角色數量（1-20）: 3
```

### 5. 查看結果

```bash
ls outputs/2026-01-23/
# 清純少女1.png
# 清純少女2.png
# 可愛少女1.png
```

## 🎨 自定義工作流

如果你想使用其他工作流，需要修改以下內容：

### 1. 確定正面提示詞節點

在 ComfyUI 界面中：
1. 找到 "CLIPTextEncode" 節點（通常標記為 "正面提示詞" 或 "Positive"）
2. 查看該節點的 ID（通常在節點標題或右鍵菜單中）

### 2. 修改代碼

```python
def replace_prompt_in_workflow(self, workflow, new_prompt):
    # 修改這裡的節點 ID
    NODE_ID = "6"  # 改成你的節點 ID
    
    if NODE_ID in workflow and "inputs" in workflow[NODE_ID]:
        workflow[NODE_ID]["inputs"]["text"] = new_prompt
```

### 3. 導出工作流

在 ComfyUI 界面:
1. 設計好你的工作流
2. 點擊 "Save (API Format)"
3. 保存為 JSON 文件
4. 將文件放到 `Api/` 目錄下

### 4. 使用新工作流

```python
generator.run(workflow_json_path="your_workflow.json", batch_count=5)
```

## 🔍 常見問題

### Q1: 連接失敗
```
❌ 無法連接到 ComfyUI
```

**解決方案**:
- 確認 ComfyUI 正在運行
- 檢查端口是否為 8188
- 嘗試在瀏覽器訪問 http://127.0.0.1:8188

### Q2: 工作流執行失敗

**可能原因**:
1. 缺少必要的模型文件（qwen_image_fp8_e4m3fn.safetensors）
2. 缺少 LoRA 文件
3. 工作流節點配置錯誤

**解決方案**:
- 查看 ComfyUI 控制台的錯誤信息
- 確認所有模型文件都已下載
- 在 ComfyUI 界面手動測試工作流

### Q3: 生成的圖片為空

**可能原因**:
- SaveImage 節點配置問題
- 輸出目錄權限問題

**解決方案**:
- 檢查 ComfyUI 的輸出目錄設置
- 確認程式有寫入權限

## 📊 性能對比

| 特性 | SD WebUI | ComfyUI |
|------|----------|---------|
| 設置複雜度 | ⭐ 簡單 | ⭐⭐⭐ 中等 |
| 靈活性 | ⭐⭐ 中等 | ⭐⭐⭐⭐⭐ 極高 |
| 模型支持 | SD 1.5/SDXL | 任意模型 |
| 節點組合 | ❌ 不支持 | ✅ 支持 |
| LoRA 堆疊 | 有限 | 無限 |
| 實時監控 | ❌ 無 | ✅ WebSocket |
| 社區工作流 | 有限 | 豐富 |

## 🎯 總結

新版程式完全適配 ComfyUI API，支持：

✅ 保持所有原有功能（隨機抽獎、AI 設計、批次生成）  
✅ 使用 qwen_image 工作流  
✅ 實時監控生成進度  
✅ 靈活配置工作流  
✅ 支持更多模型和 LoRA  

唯一的變化是底層 API，用戶體驗完全一致！
