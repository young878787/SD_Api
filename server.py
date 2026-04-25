import os
import sys

# 強制將標準輸出切換為 UTF-8，避免 Windows 預設的 cp950 導致印出表情符號時報錯
if getattr(sys.stdout, 'encoding', None) and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
if getattr(sys.stderr, 'encoding', None) and sys.stderr.encoding.lower() != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# 確保能 import 同目錄的 prompt_editor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prompt_editor import PromptEditor, setup_session_log

# ═══════════════════════════════════════════════════════════════
# 全域設定
# ═══════════════════════════════════════════════════════════════

DEFAULT_SD_URL = os.getenv("SD_WEBUI_URL", "http://127.0.0.1:7860")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
JSON_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.json")
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# 初始化 log
_log_path = setup_session_log(LOG_DIR)

# 初始化 PromptEditor
editor = PromptEditor(sd_url=DEFAULT_SD_URL, output_dir=OUTPUT_DIR)

app = FastAPI(title="Prompt Editor API")

VITE_PORT = int(os.getenv("VITE_PORT", "8877"))

# 允許 React 前端跨網域存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{VITE_PORT}",
        f"http://127.0.0.1:{VITE_PORT}",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態資料夾，確保前端能讀取生成的圖片 (對應前端的 /outputs/...)
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

class GenerateRequest(BaseModel):
    prompt: str
    idea: str
    attempts: int = 1

@app.get("/api/status")
async def get_status():
    """取得伺服器跟 SD WebUI 的連線狀態"""
    connected = editor.check_sd_connection()
    return {"connected": connected, "sdUrl": DEFAULT_SD_URL}

@app.post("/api/generate")
async def generate(req: Request):
    """
    這個端點接收 POST 請求，回傳 SSE Stream (text/event-stream)。
    這樣可以避免長時間生成任務中斷，且能即時回報進度。
    """
    try:
        body = await req.json()
    except Exception:
        body = {}
        
    prompt_text = body.get("prompt", "")
    idea_text = body.get("idea", "")
    attempts = int(body.get("attempts", 1))
    
    async def event_generator():
        yield f"data: {json.dumps({'type': 'progress', 'completed': 0, 'total': attempts, 'message': '⏳ 等待 AI 回應中...'})}\n\n"
        
        loop = asyncio.get_running_loop()
        executor = ThreadPoolExecutor(max_workers=attempts)
        
        # 準備丟入 Executor 的任務
        # 將原本的 editor.run_attempt_pipeline 非同步化
        futures = []
        for i in range(1, attempts + 1):
            future = loop.run_in_executor(
                executor,
                editor.run_attempt_pipeline,
                prompt_text, idea_text, i, attempts, JSON_CONFIG
            )
            futures.append((i, future))
        
        completed_count = 0
        raw_results = {}
        pending = [f for _, f in futures]
        
        while pending:
            # 每次等待 2 秒（類似 heartbeat）
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED,
                timeout=2.0
            )
            
            for aw in done:
                completed_count += 1
                # 找出對應的 attempt_num
                for attempt_num, f in futures:
                    if f == aw:
                        try:
                            r = aw.result()
                            raw_results[attempt_num] = r
                            yield f"data: {json.dumps({'type': 'progress', 'completed': completed_count, 'total': attempts, 'message': f'✅ 已完成 {completed_count}/{attempts} 次（嘗試 {attempt_num}）'})}\n\n"
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            raw_results[attempt_num] = {"error": str(e), "saved_paths": [], "modified_prompt": "", "attempt_num": attempt_num}
                            yield f"data: {json.dumps({'type': 'progress', 'completed': completed_count, 'total': attempts, 'message': f'⚠️ 嘗試 {attempt_num} 發生錯誤'})}\n\n"
                        break
            
            if pending:
                # 任務還沒完，每 2 秒送出保活訊號
                yield f"data: {json.dumps({'type': 'heartbeat', 'completed': completed_count, 'total': attempts, 'message': f'⏳ AI 生成中...（{completed_count}/{attempts} 已完成）'})}\n\n"
                
        # 任務全部完成，組裝結果
        yield f"data: {json.dumps({'type': 'done', 'results': raw_results})}\n\n"
        executor.shutdown(wait=False)
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    backend_port = int(os.getenv("BACKEND_PORT", "9999"))
    print(f"啟動 FastAPI 伺服器...")
    print(f"Swagger API 文件請見: http://127.0.0.1:{backend_port}/docs")
    uvicorn.run("server:app", host="127.0.0.1", port=backend_port, reload=False)
