"""
Stable Diffusion Prompt 精準編輯器 - Gradio WebUI
基於 prompt_editor.py 的 PromptEditor class，包一層 Gradio 介面
原 CLI 版本 (prompt_editor.py) 保留不動，可繼續獨立使用

啟動方式：
    python prompt_editor_ui.py
    瀏覽器開啟 http://127.0.0.1:7801
"""

import os
import sys
import re
import random
import argparse
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 確保能 import 同目錄的 prompt_editor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr
import warnings
import logging

# 抑制 Windows asyncio proactor 的 ConnectionResetError 噪音
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="asyncio")

from prompt_editor import (
    PromptEditor,
    extract_lora_tags,
    setup_session_log,
)

# ═══════════════════════════════════════════════════════════════
# 全域設定
# ═══════════════════════════════════════════════════════════════

DEFAULT_SD_URL = "http://127.0.0.1:7860"
DEFAULT_UI_HOST = "127.0.0.1"
DEFAULT_UI_PORT = 7801


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        print(f"⚠️  環境變數 {name} 不是有效整數（{raw}），改用預設值 {default}")
        return default


SD_URL = os.getenv("SD_WEBUI_URL", DEFAULT_SD_URL)
UI_HOST = os.getenv("PROMPT_EDITOR_HOST", DEFAULT_UI_HOST)
UI_PORT = _env_int("PROMPT_EDITOR_PORT", DEFAULT_UI_PORT)
AUTO_PORT = _env_bool("PROMPT_EDITOR_AUTO_PORT", True)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
JSON_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.json")
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# 初始化 log（清除舊的，攔截 stdout/stderr）
# 必須在 editor 初始化前呼叫，才能捕捉到 PromptEditor.__init__ 的輸出
_log_path = setup_session_log(LOG_DIR)

# 初始化 PromptEditor（允許在主程式入口依命令列參數重建）
editor = PromptEditor(sd_url=SD_URL, output_dir=OUTPUT_DIR)


def parse_runtime_args() -> argparse.Namespace:
    """解析命令列參數，優先權高於環境變數。"""
    parser = argparse.ArgumentParser(description="Stable Diffusion Prompt 精準編輯器")
    parser.add_argument(
        "--sd-url",
        default=SD_URL,
        help=f"Stable Diffusion WebUI API 位址（預設: {SD_URL}）",
    )
    parser.add_argument(
        "--host",
        default=UI_HOST,
        help=f"Gradio 綁定主機（預設: {UI_HOST}）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=UI_PORT,
        help=f"Gradio 監聽埠（預設: {UI_PORT}）",
    )
    parser.add_argument(
        "--auto-port",
        action="store_true",
        default=AUTO_PORT,
        help="當指定埠被占用時，自動往後尋找可用埠",
    )
    parser.add_argument(
        "--no-auto-port",
        action="store_false",
        dest="auto_port",
        help="關閉自動換埠，埠被占用時直接報錯",
    )
    return parser.parse_args()


def _is_port_available(host: str, port: int) -> bool:
    """檢查指定 host:port 是否可綁定。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def resolve_launch_port(host: str, preferred_port: int, auto_port: bool, max_scan: int = 100) -> int:
    """回傳可用埠；若 auto_port=False 則保留原埠。"""
    if preferred_port <= 0:
        print(f"⚠️  Port 必須是正整數，收到 {preferred_port}，改用預設 {DEFAULT_UI_PORT}")
        preferred_port = DEFAULT_UI_PORT

    if _is_port_available(host, preferred_port):
        return preferred_port

    if not auto_port:
        return preferred_port

    for offset in range(1, max_scan + 1):
        candidate = preferred_port + offset
        if candidate > 65535:
            break
        if _is_port_available(host, candidate):
            print(f"⚠️  Port {preferred_port} 已被占用，自動改用 {candidate}")
            return candidate

    print(f"⚠️  在 {preferred_port} 起始往後掃描 {max_scan} 個埠仍找不到可用埠，將嘗試使用原始埠")
    return preferred_port


# ═══════════════════════════════════════════════════════════════
# 輔助函數
# ═══════════════════════════════════════════════════════════════

def get_diff_text(original: str, modified: str) -> str:
    """
    將 prompt 差異轉成純文字字串（供 Gradio Textbox 顯示，不輸出 ANSI 顏色碼）
    """
    original_tags = [t.strip() for t in original.split(',') if t.strip()]
    modified_tags  = [t.strip() for t in modified.split(',') if t.strip()]

    original_set = set(original_tags)
    modified_set  = set(modified_tags)

    removed = original_set - modified_set
    added   = modified_set - original_set
    kept    = original_set & modified_set

    lines = [
        f"📊 修改差異分析",
        f"   ✅ 保留 {len(kept)} 個　🗑️ 移除 {len(removed)} 個　✨ 新增 {len(added)} 個",
    ]

    if removed:
        lines.append("\n🗑️ 移除的標籤：")
        for tag in sorted(removed):
            lines.append(f"   - {tag}")

    if added:
        lines.append("\n✨ 新增的標籤：")
        for tag in sorted(added):
            lines.append(f"   + {tag}")

    return "\n".join(lines)


def build_lora_badges_html(prompt_text: str) -> str:
    """根據 prompt 中的 LoRA 標籤，回傳彩色 badge HTML"""
    loras = extract_lora_tags(prompt_text)

    if not loras:
        return (
            "<div style='color:#999;font-size:13px;padding:4px 0;'>"
            "（未偵測到 LoRA 標籤）"
            "</div>"
        )

    palette = ["#e74c3c", "#e67e22", "#8e44ad", "#27ae60", "#2980b9", "#c0392b"]
    badges = []
    for i, lora in enumerate(loras):
        m = re.search(r'<lora:([^:>]+)', lora)
        label = m.group(1) if m else lora
        color = palette[i % len(palette)]
        badges.append(
            f'<span style="background:{color};color:white;'
            f'padding:2px 10px;border-radius:12px;font-size:12px;'
            f'margin:2px 4px 2px 0;display:inline-block;">'
            f'🔗 {label}</span>'
        )

    return (
        f"<div style='padding:4px 0;line-height:2;'>"
        f"<b style='font-size:12px;color:#555;'>偵測到 {len(loras)} 個 LoRA：</b><br/>"
        + "".join(badges)
        + "</div>"
    )


def build_sd_status_html(connected: bool, url: str) -> str:
    """回傳 SD 連線狀態的彩色 badge HTML"""
    if connected:
        return (
            f'<div style="text-align:right;">'
            f'<span style="background:#27ae60;color:white;'
            f'padding:4px 12px;border-radius:12px;font-size:13px;">'
            f'✅ SD 已連線｜{url}</span></div>'
        )
    return (
        f'<div style="text-align:right;">'
        f'<span style="background:#c0392b;color:white;'
        f'padding:4px 12px;border-radius:12px;font-size:13px;">'
        f'❌ SD 未連線｜{url}</span></div>'
    )


def extract_prompt_from_txt(txt_path: str) -> str | None:
    """
    從 _save_image_metadata 產生的 .txt 檔案中解析出 Prompt 內容
    格式範例：
        📝 Prompt:
           <actual prompt here>
        （空行）
        🌱 Seed: ...
    """
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 匹配「📝 Prompt:」到下一個空行或下一個 emoji 開頭的行之間的內容
        match = re.search(
            r'📝 Prompt:\n([\s\S]+?)(?:\n\n|\n🌱|\n📐|\n⚙️|\n🎯|\n🔧|\n📌|\n🤖)',
            content
        )
        if match:
            # 去除每行前面的縮排空格
            raw = match.group(1)
            lines = [line.lstrip() for line in raw.splitlines() if line.strip()]
            return ' '.join(lines).strip().rstrip(',')
        return None
    except Exception as e:
        print(f"⚠️  解析 txt 失敗 ({txt_path}): {e}")
        return None


def on_gallery_select(image_paths: list, evt: gr.SelectData) -> tuple:
    """
    Gallery 圖片被點選時，從對應 .txt 找出 prompt 並載入輸入框。

    Returns:
        (prompt_box_update, load_status_update)
    """
    if not image_paths:
        return gr.update(), gr.update(value="⚠️ 尚無圖片路徑資訊")

    idx = evt.index
    if idx >= len(image_paths):
        return gr.update(), gr.update(value=f"⚠️ 索引超出範圍（{idx} / {len(image_paths)}）")

    img_path = image_paths[idx]
    if not img_path or not os.path.isfile(img_path):
        return gr.update(), gr.update(value=f"⚠️ 圖片路徑無效：{img_path}")

    # 對應的 txt 和 img 檔名（e.g. 3.png → 3.txt）
    txt_path = os.path.splitext(img_path)[0] + ".txt"
    img_name = os.path.basename(img_path)
    folder   = os.path.basename(os.path.dirname(img_path))

    if not os.path.isfile(txt_path):
        return (
            gr.update(),
            gr.update(value=f"⚠️ 找不到對應記錄檔：{txt_path}")
        )

    prompt = extract_prompt_from_txt(txt_path)
    if not prompt:
        return (
            gr.update(),
            gr.update(value=f"⚠️ 無法從 {txt_path} 解析 Prompt")
        )

    status_msg = f"✅ 已從 {folder}/{img_name} 載入 Prompt（共 {len(prompt.split(','))} 個標籤）"
    return gr.update(value=prompt), gr.update(value=status_msg)


def history_to_dataframe(history: list) -> list:
    """將 history list of dict 轉換為 Dataframe 用的 list of list"""
    return [
        [r["time"], r["idea"], r["prompt_head"], r["image_count"]]
        for r in history
    ]


# ═══════════════════════════════════════════════════════════════
# Gradio Callback 函數
# ═══════════════════════════════════════════════════════════════

def on_prompt_change(prompt_text: str) -> str:
    """Phase 2：Prompt 輸入框變更時，即時更新 LoRA badge 顯示"""
    return build_lora_badges_html(prompt_text)


def on_refresh_sd_status() -> str:
    """手動重新檢查 SD 連線狀態"""
    connected = editor.check_sd_connection()
    return build_sd_status_html(connected, SD_URL)


def run_edit_and_generate(
    prompt_text: str,
    idea_text: str,
    attempts: int,
    history: list,
    progress=gr.Progress(track_tqdm=False),
):
    """
    Phase 3 + 4 主 callback：並行送出所有嘗試，收到 AI 回覆就立即生圖。

    使用 ThreadPoolExecutor：
      - 所有嘗試同時並行開呼，不互等
      - 每個嘗試 AI 回應就立即開始生圖，不需等其他嘗試完成
      - 以 as_completed 即時更新 Progress 進度
      - 最後按嘗試編號排序一起輸出

    ⚠️ 保留普通函數（非 generator），避免 Gradio 6 Svelte reconcile 崩潰。
    """

    # ── 輸入驗證 ────────────────────────────────────────────────
    if not prompt_text.strip():
        return [], "", "❌ Prompt 不能為空，請先在左側輸入現有 Prompt", history, history_to_dataframe(history), []

    if not idea_text.strip():
        return [], "", "❌ 修改想法不能為空，請描述你想要的修改", history, history_to_dataframe(history), []

    attempts = int(attempts)

    if not editor.check_sd_connection():
        print(f"⚠️  SD WebUI 未連線（{SD_URL}），將只進行 AI 修改，不生圖")

    # ── 並行送出所有嘗試 ──────────────────────────────────────────
    print(f"🚀 並行送出 {attempts} 次嘗試（AI + 生圖同步進行）")
    raw_results: dict = {}
    completed_count = 0

    with ThreadPoolExecutor(max_workers=attempts) as executor:
        future_map = {
            executor.submit(
                editor.run_attempt_pipeline,
                prompt_text, idea_text, i, attempts, JSON_CONFIG
            ): i
            for i in range(1, attempts + 1)
        }
        for future in as_completed(future_map):
            completed_count += 1
            r = future.result()
            raw_results[r["attempt_num"]] = r
            progress(
                completed_count / attempts,
                desc=f"已完成 {completed_count}/{attempts} 次（嘗試 {r['attempt_num']}）"
            )

    # ── 按嘗試編號排序，組裝輸出 ──────────────────────────────────
    images_all: list = []
    diff_parts: list = []
    last_modified_prompt: str = ""
    total_images: int = 0

    for i in range(1, attempts + 1):
        r = raw_results[i]
        header = f"=== 嘗試 {i}/{attempts} ==="

        if not r["modified_prompt"]:
            diff_parts.append(f"{header}\n{r['note'] or '❌ AI 修改失敗，已跳過'}")
            continue

        last_modified_prompt = r["modified_prompt"]
        diff_text = get_diff_text(prompt_text, r["modified_prompt"])
        if r["note"]:
            diff_text += f"\n{r['note']}"
        diff_parts.append(f"{header}\n{diff_text}")

        for path in r["saved_paths"]:
            if os.path.isfile(path):
                images_all.append(path)
                total_images += 1
            else:
                print(f"⚠️  圖片路徑不存在：{path}")

    # ── 更新歷史紀錄 ──────────────────────────────────────────────
    if last_modified_prompt:
        new_record = {
            "time":        datetime.now().strftime("%H:%M:%S"),
            "idea":        idea_text.strip(),
            "prompt_head": last_modified_prompt[:80] + ("..." if len(last_modified_prompt) > 80 else ""),
            "image_count": total_images,
        }
        history = history + [new_record]

    progress(1.0, desc="✅ 完成！")

    return (
        images_all,
        last_modified_prompt,
        "\n\n".join(diff_parts),
        history,
        history_to_dataframe(history),
        images_all,
    )


def build_ui() -> gr.Blocks:
    with gr.Blocks(
        theme=gr.themes.Soft(),
        title="✏️ Prompt 精準編輯器",
        css="""
        /* 固定標題行高度 */
        .title-row { align-items: center !important; }
        /* Gallery 最小高度，讓空白狀態不塌陷 */
        #main-gallery { min-height: 260px; }
        /* Run button 大一點 */
        #run-btn { font-size: 16px !important; padding: 10px !important; }
        /* diff box 等寬字型 */
        #diff-box textarea { font-family: monospace; font-size: 13px; }
        """,
    ) as app:

        # ── State ──────────────────────────────────────────────
        history_state    = gr.State([])   # List[dict]
        image_paths_state = gr.State([])  # 本輪生成圖片的絕對路徑清單

        # ── 標題列 ─────────────────────────────────────────────
        with gr.Row(elem_classes="title-row"):
            gr.Markdown("## ✏️ Stable Diffusion Prompt 精準編輯器")
            sd_status = gr.HTML(
                value=build_sd_status_html(editor.check_sd_connection(), SD_URL),
                label=""
            )
            refresh_sd_btn = gr.Button("🔄 重新檢查連線", size="sm", scale=0)

        gr.Markdown("---")

        # ── 主內容列 ───────────────────────────────────────────
        with gr.Row(equal_height=False):

            # ── 左欄：輸入區 （scale=1） ───────────────────────
            with gr.Column(scale=1, min_width=320):
                gr.Markdown("### 📝 輸入區")

                prompt_box = gr.Textbox(
                    label="現有完整 Prompt（含 LoRA 和質量標籤）",
                    placeholder="貼上你的完整 prompt，包含 <lora:...> 標籤...",
                    lines=10,
                    max_lines=20,
                )

                lora_display = gr.HTML(
                    value="<div style='color:#999;font-size:13px;padding:4px 0;'>（貼入 Prompt 後會自動偵測 LoRA）</div>",
                    label=""
                )

                idea_box = gr.Textbox(
                    label="修改想法",
                    placeholder="例如：換成水手服\n例如：把服裝改為賽博龐克風格\n例如：換成忍者服裝保留其他特徵",
                    lines=3,
                    max_lines=6,
                )

                attempts_slider = gr.Slider(
                    minimum=1,
                    maximum=5,
                    value=1,
                    step=1,
                    label="嘗試次數（每次 AI 給出不同創意詮釋）",
                )

                run_btn = gr.Button(
                    "🎨  AI 修改並生圖",
                    variant="primary",
                    elem_id="run-btn",
                )

                gr.Markdown(
                    "<div style='font-size:12px;color:#888;margin-top:4px;'>"
                    "💡 提示：生圖期間按鈕會禁用，完成後自動解鎖</div>"
                )

            # ── 右欄：輸出區 （scale=2） ───────────────────────
            with gr.Column(scale=2, min_width=480):
                gr.Markdown("### 🖼️ 輸出區")

                gallery = gr.Gallery(
                    label="本輪生成結果（點擊圖片可將 Prompt 載回輸入框）",
                    columns=3,
                    rows=2,
                    object_fit="contain",
                    height=320,
                    elem_id="main-gallery",
                )

                gallery_load_status = gr.Textbox(
                    value="",
                    label="",
                    interactive=False,
                    lines=1,
                    max_lines=1,
                    elem_id="gallery-load-status",
                    show_label=False,
                    placeholder="點擊上方圖片，可自動將該圖的 Prompt 載入左側輸入框",
                )

                out_prompt = gr.Textbox(
                    label="最後一次修改後的 Prompt（唯讀，可全選複製）",
                    lines=4,
                    max_lines=8,
                    interactive=False,
                )

                diff_box = gr.Textbox(
                    label="標籤差異分析",
                    lines=8,
                    max_lines=15,
                    interactive=False,
                    elem_id="diff-box",
                )

        # ── 歷史紀錄 Accordion ────────────────────────────────
        with gr.Accordion("🕐 修改歷史（點擊展開）", open=False):
            history_table = gr.Dataframe(
                headers=["時間", "修改想法", "Prompt 摘要（前 80 字）", "生成圖片數"],
                datatype=["str", "str", "str", "number"],
                interactive=False,
                wrap=True,
            )

        # ═══════════════════════════════════════════════════════
        # 事件綁定
        # ═══════════════════════════════════════════════════════

        # Phase 2：Prompt 輸入後即時偵測 LoRA
        prompt_box.change(
            fn=on_prompt_change,
            inputs=[prompt_box],
            outputs=[lora_display],
        )

        # Phase 5：重新檢查 SD 連線
        refresh_sd_btn.click(
            fn=on_refresh_sd_status,
            inputs=[],
            outputs=[sd_status],
        )

        # Gallery 點擊：載入對應圖片的 Prompt
        gallery.select(
            fn=on_gallery_select,
            inputs=[image_paths_state],
            outputs=[prompt_box, gallery_load_status],
        )

        # Phase 3 + 4：主執行按鈕
        # 執行時禁用按鈕，完成後解鎖
        run_btn.click(
            fn=lambda: gr.update(interactive=False, value="⏳ 執行中，請稍候..."),
            inputs=[],
            outputs=[run_btn],
        ).then(
            fn=run_edit_and_generate,
            inputs=[prompt_box, idea_box, attempts_slider, history_state],
            outputs=[gallery, out_prompt, diff_box, history_state, history_table, image_paths_state],
        ).then(
            fn=lambda: gr.update(interactive=True, value="🎨  AI 修改並生圖"),
            inputs=[],
            outputs=[run_btn],
        ).then(
            fn=on_refresh_sd_status,
            inputs=[],
            outputs=[sd_status],
        )

    return app


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = parse_runtime_args()

    SD_URL = args.sd_url.strip() or DEFAULT_SD_URL
    UI_HOST = args.host.strip() or DEFAULT_UI_HOST
    UI_PORT = resolve_launch_port(UI_HOST, args.port, args.auto_port)

    # 依最新 SD_URL 重建 editor，確保連線檢查與生圖 API 目標一致
    editor = PromptEditor(sd_url=SD_URL, output_dir=OUTPUT_DIR)

    print("=" * 65)
    print("✏️  Stable Diffusion Prompt 精準編輯器 - Gradio WebUI")
    print("=" * 65)
    print(f"📁 輸出資料夾：{editor.session_dir}")
    print(f"🌐 SD WebUI：{SD_URL}")
    print(f"🧭 Gradio 監聽：http://{UI_HOST}:{UI_PORT}")
    print(f"📝 Log 檔案：{_log_path}")
    print(f"🚀 Gradio UI 啟動中，請稍候...")
    print()

    app = build_ui()
    app.queue()  # 啟用 queue，支援 yield 串流 + 並發請求保護
    app.launch(
        server_name=UI_HOST,
        server_port=UI_PORT,
        inbrowser=True,       # 自動開啟瀏覽器
        show_error=True,
        allowed_paths=[OUTPUT_DIR],   # 必須！Gradio 6 預設不允許服務外部目錄
    )
