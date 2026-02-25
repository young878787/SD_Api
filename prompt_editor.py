"""
Stable Diffusion Prompt 精準編輯器
使用者輸入現有完整 Prompt + 修改想法
AI 外科手術式精準替換對應標籤，保留 LoRA、質量、背景等其餘內容不動
"""
import os
import re
import sys
import json
import random
import threading
import requests
import base64
import io
import time
from datetime import datetime
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════
# Session Log 工具
# ═══════════════════════════════════════════════════════════════

_log_file_handle = None  # 模組級別，保存當前 log 檔句柄
_log_setup_pid = None    # 已初始化的 PID，防止多執行緒/多次 import 重複寫入


class _TeeStream:
    """將 write 同時輸出到兩個 stream（終端 + log 檔）"""

    def __init__(self, primary, secondary):
        self._primary = primary
        self._secondary = secondary

    def write(self, data):
        self._primary.write(data)
        try:
            self._secondary.write(data)
            self._secondary.flush()
        except Exception:
            pass

    def flush(self):
        self._primary.flush()
        try:
            self._secondary.flush()
        except Exception:
            pass

    def isatty(self):
        return False

    def fileno(self):
        # Gradio 有時會呼叫 fileno，回傳原始終端的 fd
        return self._primary.fileno()


def setup_session_log(log_dir: str) -> str:
    """
    初始化本次 session 的 log 檔案（每次啟動清除舊內容）。

    同時攔截 sys.stdout / sys.stderr，讓所有 print 輸出也寫入 log。
    對已攔截過的 stream 是 no-op，避免重複套疊。

    Args:
        log_dir: log 資料夾路徑（會自動建立）

    Returns:
        log 檔的絕對路徑
    """
    global _log_file_handle, _log_setup_pid

    current_pid = os.getpid()

    # ── 防止重複初始化 ────────────────────────────────────────
    # Gradio 啟動時會多執行緒同時 import 模組，若不加 guard
    # 每個執行緒都會呼叫此函式，造成 log header 重複寫入 N 次。
    # 同一 PID 只初始化一次即可（不同 PID 是不同程序，各自獨立）。
    if _log_setup_pid == current_pid:
        return os.path.join(log_dir, "session.log")

    _log_setup_pid = current_pid

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "session.log")

    # 'w' 模式自動清除舊 log（每次啟動新的）
    _log_file_handle = open(log_path, 'w', encoding='utf-8', buffering=1)

    header = (
        "=" * 80 + "\n"
        f"SESSION STARTED : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Python          : {sys.version.split()[0]}\n"
        f"PID             : {current_pid}\n"
        "=" * 80 + "\n\n"
    )
    _log_file_handle.write(header)
    _log_file_handle.flush()

    # 攔截 stdout / stderr（尚未攔截才套）
    if not isinstance(sys.stdout, _TeeStream):
        sys.stdout = _TeeStream(sys.__stdout__, _log_file_handle)
    if not isinstance(sys.stderr, _TeeStream):
        sys.stderr = _TeeStream(sys.__stderr__, _log_file_handle)

    return log_path


def _log_detail(section: str, content: str):
    """
    將結構化詳細資訊僅寫入 log 檔（不輸出到終端）。
    用於記錄 AI 的完整輸入 / 輸出，避免終端過度雜亂。
    """
    global _log_file_handle
    if _log_file_handle is None:
        return
    try:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:12]
        _log_file_handle.write(f"\n[{ts}] >>> {section}\n")
        _log_file_handle.write(content)
        if not content.endswith("\n"):
            _log_file_handle.write("\n")
        _log_file_handle.flush()
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# AI 精準編輯的 System Prompt
# ═══════════════════════════════════════════════════════════════
EDITOR_SYSTEM_PROMPT = """你是一位專業的 Stable Diffusion Prompt 精準編輯助手，同時具備豐富的動漫服裝與場景設計知識。

你的任務是根據使用者的「修改想法」，對現有 prompt 進行精準修改，並在修改範圍內發揮創意，補充生動的細節標籤。

═══ 絕對保護規則（除非用戶明確說要修改，否則原封不動保留）═══
1. LoRA 標籤：所有 <lora:名稱:權重> 格式的標籤，一個都不能少、不能改
2. 質量增強標籤：masterpiece, absurdres, best quality, very aesthetic, newest, highres, ultra detailed, 8k 等
3. 技術畫質標籤：detailed eyes, detailed background, perfect lighting, perfect eyes, highly detailed face, detailed hands, detailed clothes, anime coloring 等
4. 風格標籤：NGNL Style 及其他 xxxStyle 格式的標籤
5. 角色基本外貌：髮色、眼睛顏色、瞳孔特徵（除非用戶說要換）
6. 角色名稱標籤（如 rushia_blue 等固有角色標籤，除非用戶說要改角色）
7. 背景/場景描述（除非用戶說要換背景/場景）
8. 姿勢/動作 standing,sitting,knee up,等動作提示詞修改（除非用戶說要換姿勢）

═══ 創意細節擴展規則（這是你的核心能力）═══
當用戶給出簡短的服裝或風格名稱時，你必須主動擴展成豐富的細節標籤，例如：

「水手服」→ sailor uniform, white sailor collar, navy blue pleated skirt, red ribbon bow tie, white short sleeve blouse, sailor hat, white thigh-high socks, clean pressed fabric
「女僕裝」→ maid dress, white apron, black dress, frilled apron, lace trim, white headband, puffed sleeves, black mary jane shoes
「忍者服」→ kunoichi outfit, dark navy shinobi shozoku, black fingerless gloves, thigh wrap bandages, kunai holster, split-toe tabi boots, purple sash belt
「護士服」→ nurse uniform, white nurse dress, nurse cap with red cross, white thigh-high stockings, short white skirt, stethoscope, button-up front
「巫女服」→ miko outfit, white haori, red hakama, white tabi socks, zori sandals, red ribbon hair tie, ceremonial style
「賽博龐克」→ cyberpunk bodysuit, neon circuit patterns, holographic visor, chrome shoulder pads, glowing blue accents, tactical belt pouches, cybernetic arm detail
「魔法少女」→ magical girl dress, frilled skirt, star wand accessory, color-matched thigh ribbons, magical rune embroidery, sparkle effects, pastel colored
「騎士鎧甲」→ fantasy plate armor, pauldrons, breastplate, gauntlets, metal greaves, flowing cape, heraldic emblem, polished silver

規則：
- 即使用戶只說一個詞，也要輸出 6~12 個精準的細節服裝標籤
- 依據原 prompt 的角色氣質（清純/活潑/成熟）自動調整服裝的細節和顏色
- 可以加入材質描述（lace, satin, cotton, leather 等）讓畫面更精緻

═══ 修改類別識別表（根據用戶想法判斷要改哪類）═══
用戶說：換裝 / 服裝 / 衣服 / outfit / 穿上 / 換成XXX服 / 穿XXX
  → 精準替換所有服裝標籤（shirt, dress, skirt, pants, jacket, coat, uniform, outfit, costume, top, blouse, sweater, hoodie, kimono, armor, apron, bikini, swimsuit, lingerie, ribbon, bow, tie 等）
  → 同時更新鞋子和配件以搭配新服裝風格

用戶說：身材 / 胸部 / 豐滿 / 纖細 / 體型 / 調整體態
  → 修改：slim, curvy, petite, large breasts, small breasts, flat chest, medium breasts, hourglass figure, athletic body 等身材標籤

用戶說：換髮型 / 髮色 / 頭髮 / 換成XXX髮
  → 修改：hair color, hairstyle, ponytail, twin tails, braid, hair length, hair accessory 等，同時擴展細節

用戶說：鞋子 / 短襪 / 長靴 / 高跟
  → 修改：shoes, boots, heels, socks, stockings, footwear 等鞋襪標籤

用戶說：配件 / 項鍊 / 耳環 / 戒指 / 眼鏡 / 帽子
  → 修改對應配飾標籤，並擴展具體款式細節

用戶說：換背景 / 場景 / 環境
  → 修改 background, outdoors, indoors, scenery 等相關標籤，擴展氛圍描述

用戶說：換姿勢 / 動作 / 坐 / 站 / 躺
  → 修改 pose, sitting, standing, lying, looking at viewer 等姿勢標籤

用戶說：表情 / 笑 / 哭 / 生氣 / 害羞
  → 修改 smile, crying, angry, blush 等表情及情緒標籤

用戶說：加 lora / 換 lora / 移除 lora
  → 允許修改 LoRA 標籤（此為唯一允許動 lora 的情況）

用戶說：換風格 / 賽博龐克 / 奇幻 / 和風 / 蒸汽龐克 / 哥德
  → 修改場景、服裝、配件的風格描述，但保留所有 LoRA 和質量標籤不變

═══ 精準替換操作規範 ═══
1. 找到與修改類別對應的舊標籤群，整組替換成新設計的標籤
2. 新標籤必須用英文、逗號分隔，風格與原標籤一致
3. 修改範圍內要盡量豐富，不在修改範圍內的標籤一律不動
4. 替換後的標籤語意精確、符合 Stable Diffusion booru 標籤慣例
5. 保持原有的 prompt 整體結構順序（LoRA → 質量 → 角色 → 服裝 → 配件 → 場景）

═══ 輸出格式（非常重要）═══
你可以在內部進行任何思考和分析，但最終輸出必須嚴格遵守以下格式：

[FINAL_PROMPT]
修改後的完整 prompt（逗號分隔的標籤，無任何說明文字）
[/FINAL_PROMPT]

規則：
- [FINAL_PROMPT] 和 [/FINAL_PROMPT] 是必填標記，不可省略
- 標記之間只放純英文逗號分隔的標籤，不能有任何中文說明
- 標記外的任何文字（思考過程、解釋說明）都會被自動忽略
- 範例：[FINAL_PROMPT]\n<lora:name:1>, masterpiece, sailor uniform, ...\n[/FINAL_PROMPT]"""


# ═══════════════════════════════════════════════════════════════
# 工具函數
# ═══════════════════════════════════════════════════════════════

def extract_lora_tags(prompt: str) -> list:
    """提取 prompt 中所有 LoRA 標籤"""
    return re.findall(r'<lora:[^>]+>', prompt)


def validate_lora_preservation(original_prompt: str, modified_prompt: str) -> tuple[bool, list]:
    """
    驗證修改後的 prompt 是否保留了所有原始 LoRA 標籤
    回傳 (是否全部保留, 缺失的lora列表)
    """
    original_loras = extract_lora_tags(original_prompt)
    missing_loras = [lora for lora in original_loras if lora not in modified_prompt]
    return len(missing_loras) == 0, missing_loras


def restore_missing_loras(modified_prompt: str, missing_loras: list) -> str:
    """將遺失的 LoRA 標籤插回 prompt 開頭"""
    if not missing_loras:
        return modified_prompt
    lora_prefix = ','.join(missing_loras) + ','
    return lora_prefix + modified_prompt


def strip_thinking_blocks(text: str) -> str:
    """
    移除思考型模型輸出的推理區塊，讓後續只剩下真正的 prompt。

    支援格式：
      - <think>...</think>      （Step / DeepSeek-R1 / Qwen3-thinking 等）
      - <thinking>...</thinking> （部分模型使用此格式）

    對非思考型模型（如 qwen3-next-instruct）此函式是 no-op（無副作用）。
    即使思考區塊橫跨多行也能正確清除。
    """
    # 非貪婪匹配，防止多個區塊被合併處理
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'<thinking>[\s\S]*?</thinking>', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def extract_prompt_from_markers(text: str) -> str | None:
    """
    從模型輸出中提取 [FINAL_PROMPT]...[/FINAL_PROMPT] 之間的內容。

    這是主要的輸出解析方式，適用於所有模型（含思考型）：
      - 思考型模型（step-3.5-flash 等）可在標記外自由思考，
        標記內只放最終 prompt，不受推理過程干擾。
      - 指令型模型（qwen3-next 等）通常直接輸出標記包住的 prompt。
      - 任何標記以外的思考/說明文字都會被自動忽略。

    Returns:
        提取並清理後的 prompt 字串，若找不到標記則回傳 None。
    """
    match = re.search(
        r'\[FINAL_PROMPT\]([\s\S]*?)\[/FINAL_PROMPT\]',
        text,
        flags=re.IGNORECASE
    )
    if not match:
        return None

    content = match.group(1).strip()
    # 移除 markdown code block（部分模型會加）
    content = re.sub(r'^```[^\n]*\n', '', content)
    content = re.sub(r'\n```$', '', content)
    return content.strip() or None


def _smart_extract_prompt(text: str) -> str | None:
    """
    最後一層 fallback：從模型輸出中找出最後一個「像 prompt 的段落」。

    適用情境：模型忽略或忘記加 [FINAL_PROMPT] 標記，但仍在輸出結尾
    附上了構造好的 prompt（通常以 <lora: 開頭，全英文逗號分隔）。

    判斷標準：
    1. 段落中含有 <lora:> 標籤（prompt 的特徵）
    2. 中文字元比例 < 10%（排除分析段落）
    3. 逗號數量 >= 5（SD prompt 必然有大量逗號）

    Returns:
        最後一個符合條件的段落，若無則回傳 None。
    """
    # 用空行切分段落
    paragraphs = re.split(r'\n{2,}', text.strip())

    for para in reversed(paragraphs):
        para = para.strip()
        if not para:
            continue
        # 必須含有 LoRA 標籤
        if '<lora:' not in para:
            continue
        # 中文字比例不能超過 10%
        cn_chars = len(re.findall(r'[\u4e00-\u9fff]', para))
        if cn_chars > max(len(para) * 0.10, 5):
            continue
        # 逗號數量要夠多（SD prompt 特徵）
        if para.count(',') < 5:
            continue
        return para

    return None


def show_prompt_diff(original: str, modified: str):
    """顯示 prompt 的差異對比"""
    original_tags = [t.strip() for t in original.split(',') if t.strip()]
    modified_tags = [t.strip() for t in modified.split(',') if t.strip()]

    original_set = set(original_tags)
    modified_set = set(modified_tags)

    removed = original_set - modified_set
    added = modified_set - original_set
    kept = original_set & modified_set

    print(f"\n📊 修改差異分析：")
    print(f"   保留標籤：{len(kept)} 個")
    print(f"   移除標籤：{len(removed)} 個")
    print(f"   新增標籤：{len(added)} 個")

    if removed:
        print(f"\n🗑️  移除的標籤：")
        for tag in sorted(removed):
            print(f"   - {tag}")

    if added:
        print(f"\n✨ 新增的標籤：")
        for tag in sorted(added):
            print(f"   + {tag}")


def get_multiline_input(prompt_text: str) -> str:
    """
    取得多行輸入（支援貼上多行 prompt）
    輸入空白行表示結束
    """
    print(prompt_text)
    print("（可直接貼上多行 prompt，輸入完後按兩次 Enter 確認）")
    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                lines.append(line)
        except EOFError:
            break

    # 合併多行，移除多餘空白
    full_text = ' '.join(lines).strip()
    # 清理逗號前後空格
    full_text = re.sub(r'\s*,\s*', ', ', full_text)
    return full_text


# ═══════════════════════════════════════════════════════════════
# 核心 AI 編輯類別
# ═══════════════════════════════════════════════════════════════

class PromptEditor:
    """Stable Diffusion Prompt 精準編輯器"""

    def __init__(self, sd_url="http://127.0.0.1:7860", output_dir="outputs"):
        self.sd_url = sd_url.rstrip('/')
        self.output_dir = output_dir

        # 日期資料夾：outputs/2026-02-21/
        today = datetime.now().strftime("%Y-%m-%d")
        self.date_dir = os.path.join(output_dir, today)
        os.makedirs(self.date_dir, exist_ok=True)

        # 本次 session 資料夾：edit1, edit2, ... 依現有資料夾數量遞增
        existing = sorted(
            [d for d in os.listdir(self.date_dir)
             if os.path.isdir(os.path.join(self.date_dir, d))
             and d.startswith("edit") and d[4:].isdigit()],
            key=lambda x: int(x[4:])
        )
        next_num = int(existing[-1][4:]) + 1 if existing else 1
        self.session_dir = os.path.join(self.date_dir, f"edit{next_num}")
        os.makedirs(self.session_dir)
        print(f"📁 本次圖片資料夾：{self.session_dir}")

        # 本 session 的圖片流水號（lock 保護多執行緒並行安全）
        self.image_counter = 0
        self._counter_lock = threading.Lock()

        # provider list 快取（避免每次 AI 呼叫重建 OpenAI client）
        self._providers_cache: list | None = None

        # 啟動時顯示已啟用的 AI 提供商（有 Key 才算啟用）
        active = self._build_provider_list()
        if active:
            unique_labels = list(dict.fromkeys(p[3].split(" ")[0] for p in active))
            print(f"🤖 AI 提供商：{' → '.join(unique_labels)}（共 {len(active)} 個模型）")
        else:
            print("⚠️  警告：未找到任何可用 AI 提供商，請確認 .env 設定")

    # ── 提供商靜態設定表 ─────────────────────────────────────────
    # key        : AI_PROVIDERS 中使用的識別名稱
    # key_env    : API Key 的環境變數名
    # base_env   : Base URL 的環境變數名
    # default_base: 若 base_env 未設定時的預設值（None 代表必填）
    # model_env  : 主模型的環境變數名
    # backup_env : 備用模型清單的環境變數名（逗號或分號分隔）
    # timeout_env: Timeout 的環境變數名
    # label      : 顯示用的提供商名稱
    _PROVIDER_CONFIGS: dict = {
        "nvidia_api": {
            "key_env":      "NVIDIA_API_KEY",
            "base_env":     "NVIDIA_BASE_URL",
            "default_base": None,                # Base URL 為必填
            "model_env":    "NVIDIA_MODEL_NAME",
            "backup_env":   "NVIDIA_BACKUP_MODELS",
            "timeout_env":  "NVIDIA_API_TIMEOUT",
            "label":        "Nvidia",
        },
        "open_router": {
            "key_env":      "OPENROUTER_API_KEY",
            "base_env":     "OPENROUTER_BASE_URL",
            "default_base": "https://openrouter.ai/api/v1",
            "model_env":    "OPENROUTER_MODEL_NAME",
            "backup_env":   "OPENROUTER_BACKUP_MODELS",
            "timeout_env":  "OPENROUTER_API_TIMEOUT",
            "label":        "OpenRouter",
        },
        "gemini": {
            "key_env":      "GEMINI_API_KEY",
            "base_env":     "GEMINI_BASE_URL",
            "default_base": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "model_env":    "GEMINI_MODEL_NAME",
            "backup_env":   "GEMINI_BACKUP_MODELS",
            "timeout_env":  "GEMINI_API_TIMEOUT",
            "label":        "Gemini",
        },
    }

    def _build_provider_list(self) -> list:
        """
        建立 AI provider 清單，格式為 [(client, timeout, model_name, label), ...]

        優先順序由 .env 的 AI_PROVIDERS 決定（逗號分隔的識別名稱），
        可用值：nvidia_api, open_router, gemini
        僅啟用有填入 API Key 的提供商，其餘自動跳過。

        每個提供商都支援：
          - 主模型（*_MODEL_NAME）
          - 備用模型清單（*_BACKUP_MODELS，逗號或分號分隔）
          → 主模型失敗時依序嘗試備用模型，再切換下一個提供商

        思考型模型的 <think>...</think> 區塊會被 strip_thinking_blocks() 自動清除。
        """
        if self._providers_cache is not None:
            return self._providers_cache

        # 讀取啟用清單，預設全開（向後相容）
        enabled_str = os.getenv("AI_PROVIDERS", "nvidia_api,open_router,gemini").strip()
        enabled_list = [p.strip().lower() for p in
                        enabled_str.replace(';', ',').split(',') if p.strip()]

        providers = []
        timeout_default = 60

        for provider_id in enabled_list:
            cfg = self._PROVIDER_CONFIGS.get(provider_id)
            if cfg is None:
                print(f"   ⚠️  AI_PROVIDERS 包含未知提供商：'{provider_id}'，已跳過")
                continue

            api_key = os.getenv(cfg["key_env"], "").strip()
            if not api_key:
                continue  # Key 未填，靜默跳過

            base_url = os.getenv(cfg["base_env"], cfg["default_base"] or "").strip()
            if not base_url:
                print(f"   ⚠️  {cfg['label']} 未設定 {cfg['base_env']}，已跳過")
                continue

            timeout = int(os.getenv(cfg["timeout_env"], str(timeout_default)))

            client = OpenAI(
                base_url=base_url,
                api_key=api_key,
                timeout=timeout,
            )

            primary_model = os.getenv(cfg["model_env"], "").strip()
            backup_str    = os.getenv(cfg["backup_env"], "").strip()

            models = [primary_model] if primary_model else []
            if backup_str:
                models += [m.strip() for m in
                           backup_str.replace(';', ',').split(',') if m.strip()]

            for i, model_name in enumerate(models):
                label = (f"{cfg['label']} 主模型" if i == 0
                         else f"{cfg['label']} 備用 {i}")
                providers.append((client, timeout, model_name, label))

        self._providers_cache = providers
        return providers

    def edit_prompt_with_ai(self, original_prompt: str, user_idea: str,
                             attempt_num: int = 1, total_attempts: int = 1) -> tuple[str | None, dict | None]:
        """
        使用 AI 根據使用者想法精準修改 prompt

        Args:
            original_prompt: 原始完整 prompt（含 LoRA 和質量標籤）
            user_idea: 使用者的修改想法描述
            attempt_num: 當前嘗試編號（用於產生不同創意變化）
            total_attempts: 總嘗試次數

        Returns:
            (修改後的完整 prompt, AI metadata 字典)
            失敗回傳 (None, None)
        """
        providers = self._build_provider_list()
        if not providers:
            print("❌ 沒有可用的 AI 提供商。請檢查：")
            print("   1. .env 的 AI_PROVIDERS 是否包含至少一個提供商（nvidia_api / open_router / gemini）")
            print("   2. 對應的 API Key 是否已填入（如 NVIDIA_API_KEY / OPENROUTER_API_KEY / GEMINI_API_KEY）")
            return None, None

        # 提取原始 LoRA 標籤，作為驗證基準
        original_loras = extract_lora_tags(original_prompt)

        # 多次嘗試時，用不同的創意方向提示讓輸出有所差異
        VARIATION_HINTS = [
            "",  # 第1次：無額外提示，最忠實詮釋
            "請在符合想法的前提下，在顏色搭配和材質細節上發揮獨特創意，給出與一般設計不同的風格。",
            "請在符合想法的前提下，加強配件和細節層次感，想像這套服裝在精品動漫中的精緻呈現方式。",
            "請在符合想法的前提下，融入一些對比色或特殊材質（如皮革、蕾絲、金屬裝飾），讓設計更有個性。",
            "請在符合想法的前提下，考慮季節感和場合感，設計出有完整故事性的服裝搭配。",
        ]
        variation_hint = VARIATION_HINTS[min(attempt_num - 1, len(VARIATION_HINTS) - 1)]

        lora_reminder = ""
        if original_loras:
            lora_reminder = f"\n\n【必須完整保留在輸出中的 LoRA 標籤，一個都不能缺少】\n" + \
                          "\n".join(f"  - {lora}" for lora in original_loras)

        variation_line = f"\n\n【本次創意方向提示】\n{variation_hint}" if variation_hint else ""

        user_message = f"""【現有 Prompt】
{original_prompt}
{lora_reminder}

【修改想法】
{user_idea}{variation_line}

請根據修改想法，精準修改以上 prompt，只改動與想法相關的標籤，其餘全部保留。
輸出格式必須如下，不能省略標記：
[FINAL_PROMPT]
修改後的完整 prompt（純英文逗號分隔標籤，無任何說明）
[/FINAL_PROMPT]"""

        if attempt_num == 1:
            print(f"   🔍 識別到 {len(original_loras)} 個 LoRA 標籤需保護")
            print(f"   🤖 可用提供商: {len(providers)} 個（"
                  + ", ".join(p[3] for p in providers) + ")")

        # 溫度隨嘗試次數逐漸提高，增加創意多樣性
        temperature = round(0.7 + (attempt_num - 1) * 0.08, 2)
        temperature = min(temperature, 0.95)

        ai_metadata = {
            "model": None,
            "temperature": temperature,
            "provider": None,
            "timestamp": datetime.now().isoformat()
        }

        for client, timeout, model_name, provider_label in providers:
            start_time = time.time()
            try:
                print(f"   ⏳ [{attempt_num}/{total_attempts}] {provider_label}: {model_name}（溫度 {temperature}）")

                # ── Log：AI 呼叫前，記錄完整輸入 ─────────────────
                _log_detail(
                    f"AI_INPUT [嘗試 {attempt_num}/{total_attempts}]",
                    f"  Provider    : {provider_label}\n"
                    f"  Model       : {model_name}\n"
                    f"  Temperature : {temperature} | top_p: 0.92 | max_tokens: 30000\n"
                    + "─" * 64 + " User Message\n"
                    + user_message + "\n"
                    + "─" * 64 + "\n"
                )

                response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": EDITOR_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=temperature,
                    top_p=0.92,
                    max_tokens=30000,
                    model=model_name
                )
                elapsed = time.time() - start_time

                message = response.choices[0].message

                # content 可能為 None（思考型模型如 Gemini 3 Flash 有時僅返回 reasoning）
                # 依序嘗試：content → reasoning_content（若有）
                raw_content = message.content
                if raw_content is None:
                    # 嘗試取得思考模型的 reasoning_content
                    raw_content = getattr(message, "reasoning_content", None)
                if not raw_content:
                    raise ValueError(f"模型回傳空內容（content=None）")

                result = raw_content.strip()

                # ── 三層解析，依序嘗試 ────────────────────────────────
                thinking_removed = 0
                extract_method = ""

                # 層級 1：[FINAL_PROMPT] 標記（最佳，所有模型通用）
                extracted = extract_prompt_from_markers(result)
                if extracted:
                    chars_ignored = len(result) - len(extracted)
                    if chars_ignored > 20:
                        print(f"   🎯 標記提取成功，已忽略 {chars_ignored} 字元的推理內容")
                    result = extracted
                    extract_method = "[FINAL_PROMPT] marker"
                else:
                    # 層級 2：<think> 標籤（部分思考模型使用此格式）
                    before_strip = len(result)
                    result_stripped = strip_thinking_blocks(result)
                    thinking_removed = before_strip - len(result_stripped)
                    if thinking_removed > 0:
                        result = result_stripped
                        print(f"   🧠 偵測到 <think> 區塊，已移除 {thinking_removed} 字元")
                        extract_method = "<think> strip"

                    # 層級 3：智慧 fallback - 找最後一個符合 SD prompt 特徵的段落
                    # 適用於 step-3.5-flash 這類「將分析混入 content、標記又被忽略」的模型
                    if not extract_method:
                        smart = _smart_extract_prompt(result)
                        if smart:
                            chars_ignored = len(result) - len(smart)
                            print(f"   🔍 智慧 fallback 成功，已忽略 {chars_ignored} 字元的分析內容")
                            result = smart
                            extract_method = "smart fallback"

                    if not extract_method:
                        # 最後手段：只去除 markdown code block
                        result = re.sub(r'^```[^\n]*\n', '', result)
                        result = re.sub(r'\n```$', '', result)
                        result = result.strip()
                        extract_method = "raw (no marker found)"
                        print(f"   ⚠️  未找到任何可用的標記，使用原始輸出")

                if not result:
                    raise ValueError("模型回傳結果為空字串")

                print(f"   ✅ AI 回應成功！耗時: {elapsed:.2f} 秒")

                # ── LoRA 保護驗證 ──────────────────────────────
                all_preserved, missing = validate_lora_preservation(original_prompt, result)
                if not all_preserved:
                    print(f"   ⚠️  {len(missing)} 個 LoRA 遺失，自動補回...")
                    result = restore_missing_loras(result, missing)
                else:
                    print(f"   ✅ LoRA 標籤完整保留")

                # 記錄 AI metadata
                ai_metadata["model"] = model_name
                ai_metadata["provider"] = provider_label

                # ── Log：AI 呼叫成功，記錄完整輸出 ───────────────
                _log_detail(
                    f"AI_OUTPUT [嘗試 {attempt_num}/{total_attempts}]",
                    f"  Provider        : {provider_label}\n"
                    f"  Model           : {model_name}\n"
                    f"  Elapsed         : {elapsed:.2f}s\n"
                    f"  Raw length      : {len(raw_content)} chars\n"
                    f"  Extraction      : {extract_method}\n"
                    f"  LoRA missing    : {len(missing) if not all_preserved else 0} 個（已自動補回）\n"
                    + "─" * 64 + " Final Prompt\n"
                    + result + "\n"
                    + "─" * 64 + "\n"
                )

                return result, ai_metadata
            except Exception as e:
                elapsed = time.time() - start_time
                err = str(e)
                if "timeout" in err.lower() or elapsed >= timeout:
                    print(f"   ⏱️  超時！({elapsed:.2f} 秒)")
                else:
                    print(f"   ❌ 錯誤: {err}")
                print(f"   🔄 切換到下一個提供商...")
                # ── Log：AI 呼叫失敗 ──────────────────────────────
                _log_detail(
                    f"AI_ERROR [嘗試 {attempt_num}/{total_attempts}]",
                    f"  Provider : {provider_label}\n"
                    f"  Model    : {model_name}\n"
                    f"  Elapsed  : {elapsed:.2f}s\n"
                    f"  Error    : {err}\n"
                )

        print(f"   ❌ 所有提供商都失敗了")
        return None, None

    # ───────────────────────────────────────────────────────────
    # SD WebUI 生成相關
    # ───────────────────────────────────────────────────────────

    def run_attempt_pipeline(
        self,
        original_prompt: str,
        user_idea: str,
        attempt_num: int,
        total_attempts: int,
        json_config_path: str,
    ) -> dict:
        """
        單次嘗試的完整流程（thread-safe）：AI 修改 → 立即 SD 生圖

        設計為可被 ThreadPoolExecutor 並行呼叫，各嘗試彼此獨立。
        AI 回復一就立即開始生圖，不等其他層張。

        Returns:
            dict 包含：
              attempt_num     : int
              modified_prompt : str | None    (為 None 表示 AI 失敗)
              ai_metadata     : dict | None
              saved_paths     : list[str]     (已存圖片檔路徑)
              sd_config       : dict | None   (用於日志/差異計算)
              note            : str           (附加註解，如 SD 未連線、生圖失敗)
        """
        result: dict = {
            "attempt_num":      attempt_num,
            "modified_prompt":  None,
            "ai_metadata":      None,
            "saved_paths":      [],
            "sd_config":        None,
            "note":             "",
        }

        # ── Step 1：AI 修改 ──────────────────────────────
        modified_prompt, ai_metadata = self.edit_prompt_with_ai(
            original_prompt, user_idea, attempt_num, total_attempts
        )
        if not modified_prompt:
            result["note"] = "❌ AI 修改失敗"
            return result

        result["modified_prompt"] = modified_prompt
        result["ai_metadata"]     = ai_metadata

        # ── Step 2：SD 生圖 ──────────────────────────────
        if not self.check_sd_connection():
            result["note"] = "⚠️  SD 未連線，已略過生圖。可手動複製 Prompt 使用。"
            return result

        config = self.load_json_config(json_config_path)
        if not config:
            result["note"] = "❌ 無法載入 JSON 配置"
            return result

        config["prompt"] = modified_prompt
        config["seed"]   = random.randint(1000000000, 9999999999)
        result["sd_config"] = config

        gen_result = self.generate_image(config)
        if gen_result and "images" in gen_result:
            metadata = self._build_complete_metadata(modified_prompt, config, ai_metadata)
            result["saved_paths"] = self.save_images(gen_result, metadata)
        else:
            result["note"] = "❌ SD 生圖失敗（AI prompt 已取得，可手動複製使用）"

        return result

    def _build_complete_metadata(self, modified_prompt: str, config: dict,
                                  ai_metadata: dict | None) -> dict:
        """從 AI 結果和 SD config 組裝圖片存檔用的 metadata 字典"""
        return {
            "prompt":       modified_prompt,
            "seed":         config.get("seed", 0),
            "width":        config.get("width", 512),
            "height":       config.get("height", 512),
            "steps":        config.get("steps", 28),
            "sampler_name": config.get("sampler_name", "DPM++ 2M"),
            "cfg_scale":    config.get("cfg_scale", 7.0),
            "ai_model":     ai_metadata.get("model",       "Unknown") if ai_metadata else None,
            "ai_provider":  ai_metadata.get("provider",    "Unknown") if ai_metadata else None,
            "temperature":  ai_metadata.get("temperature",     0.7)   if ai_metadata else None,
            "ai_timestamp": ai_metadata.get("timestamp",       "")    if ai_metadata else "",
        }

    def check_sd_connection(self) -> bool:
        """檢查 SD WebUI 連線"""
        try:
            r = requests.get(f"{self.sd_url}/sdapi/v1/sd-models", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def load_json_config(self, json_path: str) -> dict | None:
        """載入 SD 生成參數 JSON"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 載入 JSON 失敗: {e}")
            return None

    def generate_image(self, payload: dict) -> dict | None:
        """呼叫 SD WebUI API 生成圖片"""
        try:
            r = requests.post(f"{self.sd_url}/sdapi/v1/txt2img", json=payload, timeout=300)
            if r.status_code == 200:
                return r.json()
            print(f"   ❌ 請求失敗 (狀態碼: {r.status_code})")
            return None
        except requests.exceptions.Timeout:
            print("   ❌ 請求超時")
        except requests.exceptions.ConnectionError:
            print(f"   ❌ 無法連接 SD WebUI: {self.sd_url}")
        except Exception as e:
            print(f"   ❌ 發生錯誤: {e}")
        return None

    def save_images(self, response: dict, metadata: dict = None) -> list:
        """
        保存生成的圖片到本次 session 資料夾，檔名用純流水號
        同時生成配套的 .txt 檔案記錄所有生成參數
        
        Args:
            response: SD API 回傳的 response
            metadata: 包含 prompt, seed, 生成參數, AI信息的字典
                    {
                        "prompt": "...",
                        "seed": 12345,
                        "width": 512,
                        "height": 512,
                        "steps": 28,
                        "sampler_name": "DPM++ 2M",
                        "cfg_scale": 7,
                        "ai_model": "gemini-3-flash-preview",
                        "ai_provider": "Gemini 主模型",
                        "temperature": 0.7,
                        "ai_timestamp": "2026-02-22T10:30:45.123456"
                    }
        """
        if not response or 'images' not in response:
            return []

        saved = []
        for img_data in response['images']:
            try:
                if ',' in img_data:
                    img_data = img_data.split(',', 1)[1]
                image = Image.open(io.BytesIO(base64.b64decode(img_data)))
                # 多執行緒並行時保護計數器的原子性
                with self._counter_lock:
                    self.image_counter += 1
                    local_counter = self.image_counter
                filename = f"{local_counter}.png"
                filepath = os.path.join(self.session_dir, filename)
                image.save(filepath, format='PNG')
                saved.append(filepath)
                print(f"   ✅ 已保存: {filepath}  ({image.size[0]}x{image.size[1]})")

                # ── 同步保存參數記錄到 .txt ──────────────────
                if metadata:
                    txt_filename = f"{local_counter}.txt"
                    txt_filepath = os.path.join(self.session_dir, txt_filename)
                    self._save_image_metadata(txt_filepath, metadata, filename)

            except Exception as e:
                print(f"   ❌ 保存圖片失敗: {e}")

        return saved

    def _save_image_metadata(self, txt_filepath: str, metadata: dict, image_filename: str):
        """
        保存圖片生成參數到 .txt 檔案
        """
        try:
            lines = []
            lines.append("=" * 80)
            lines.append(f"Stable Diffusion 圖片生成參數記錄")
            lines.append("=" * 80)
            lines.append("")
            lines.append(f"📁 圖片檔名: {image_filename}")
            lines.append(f"⏰ 生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")

            # ── 生成參數 ────────────────────────────────────
            lines.append("🎨 Stable Diffusion 生成參數")
            lines.append("-" * 80)
            if "prompt" in metadata:
                lines.append(f"📝 Prompt:")
                lines.append(f"   {metadata['prompt']}")
                lines.append("")
            if "seed" in metadata:
                lines.append(f"🌱 Seed: {metadata['seed']}")
            if "width" in metadata and "height" in metadata:
                lines.append(f"📐 分辨率: {metadata['width']}x{metadata['height']}")
            if "steps" in metadata:
                lines.append(f"⚙️  步數 (Steps): {metadata['steps']}")
            if "sampler_name" in metadata:
                lines.append(f"🎯 採樣器 (Sampler): {metadata['sampler_name']}")
            if "cfg_scale" in metadata:
                lines.append(f"🔧 CFG Scale: {metadata['cfg_scale']}")
            
            # 加入其他可能的 SD 參數
            other_sd_params = ["scheduler", "model", "vae", "positive_prompt", "negative_prompt"]
            for param in other_sd_params:
                if param in metadata and metadata[param]:
                    lines.append(f"📌 {param}: {metadata[param]}")
            
            lines.append("")

            # ── AI 修改信息 ────────────────────────────────
            lines.append("🤖 AI 提示詞修改信息")
            lines.append("-" * 80)
            if "ai_model" in metadata and metadata["ai_model"]:
                lines.append(f"模型: {metadata['ai_model']}")
            if "ai_provider" in metadata and metadata["ai_provider"]:
                lines.append(f"提供商: {metadata['ai_provider']}")
            if "temperature" in metadata:
                lines.append(f"溫度 (Temperature): {metadata['temperature']}")
            if "ai_timestamp" in metadata and metadata["ai_timestamp"]:
                lines.append(f"AI 處理時間: {metadata['ai_timestamp']}")
            
            lines.append("")
            lines.append("=" * 80)

            # 寫入文件
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))

            print(f"   💾 已保存參數記錄: {txt_filepath}")

        except Exception as e:
            print(f"   ❌ 保存參數記錄失敗: {e}")


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("✏️  Stable Diffusion Prompt 精準編輯器")
    print("   輸入現有 Prompt + 你的想法 → AI 精準修改，多次嘗試生成")
    print("=" * 70)
    print()

    editor = PromptEditor(
        sd_url="http://127.0.0.1:7860",
        output_dir="outputs"
    )

    # ── 步驟 1：輸入原始 Prompt（僅一次）──────────────────────
    print("步驟 1：輸入你現有的完整 Prompt（含 LoRA 和質量標籤）")
    print("-" * 70)
    current_prompt = get_multiline_input("")

    if not current_prompt:
        print("❌ Prompt 不能為空")
        return

    loras = extract_lora_tags(current_prompt)
    tag_count = len([t for t in current_prompt.split(',') if t.strip()])
    print(f"\n✅ 已接收 Prompt")
    print(f"   └─ 總標籤數：{tag_count} 個")
    print(f"   └─ LoRA 標籤：{len(loras)} 個 → {', '.join(loras) if loras else '無'}")
    print()

    # ── 檢查 SD 連接（一次，之後不再重複）────────────────────
    sd_available = editor.check_sd_connection()
    if sd_available:
        print(f"✅ SD WebUI 連接正常：{editor.sd_url}")
    else:
        print(f"⚠️  無法連接 SD WebUI（{editor.sd_url}）")
        print("   AI 修改功能仍可使用，但無法自動生成圖片")
    print()

    round_count = 0

    # ══════════════════════════════════════════════════════════
    # 主循環：步驟 2 → 3 → 4(嘗試) → 步驟 5 → 回步驟 2
    # ══════════════════════════════════════════════════════════
    while True:
        round_count += 1
        print("=" * 70)
        print(f"✏️  第 {round_count} 輪修改")
        print("=" * 70)

        # ── 步驟 2：輸入修改想法 ───────────────────────────────
        print("\n步驟 2：描述你的修改想法")
        print("   範例：幫我換成水手服")
        print("   範例：把服裝改為賽博龐克風格")
        print("   範例：把身材調整為更豐滿的曲線")
        print("   範例：換成忍者服裝保留其他特徵")
        print("   （輸入 'q' 退出，'show' 查看目前 prompt）")
        print()

        try:
            idea = input("🖊️  修改想法：").strip()
        except KeyboardInterrupt:
            print("\n⚠️  使用者中斷")
            break

        if idea.lower() == 'q':
            print("\n👋 已退出編輯器")
            break

        if idea.lower() == 'show':
            print("\n📋 目前的 Prompt：")
            print("-" * 70)
            print(current_prompt)
            print("-" * 70)
            print()
            round_count -= 1  # show 不算一輪
            continue

        if not idea:
            print("❌ 修改想法不能為空，請重新輸入")
            round_count -= 1
            continue

        # ── 步驟 3：輸入嘗試次數 ───────────────────────────────
        print()
        print("步驟 3：設定嘗試次數")
        print("   每次嘗試 AI 會基於相同想法給出不同的創意詮釋")
        print("   並各自生成一張圖片")
        print()

        while True:
            try:
                attempts_input = input("🔢  嘗試次數（1-5，直接 Enter 預設 1）：").strip()
                if attempts_input == "":
                    attempts = 1
                    break
                attempts = int(attempts_input)
                if 1 <= attempts <= 5:
                    break
                print("   ❌ 請輸入 1 到 5 之間的數字")
            except ValueError:
                print("   ❌ 請輸入有效的數字")
            except KeyboardInterrupt:
                print("\n⚠️  使用者中斷")
                return

        print(f"\n   ✅ 將進行 {attempts} 次嘗試")

        # ── 步驟 4 + 5：依嘗試次數循環 AI 修改 + SD 生成 ──────
        print()
        print("-" * 70)

        for attempt in range(1, attempts + 1):
            print()
            print(f"▶  嘗試 {attempt}/{attempts}")
            print("-" * 70)

            # AI 修改
            modified_prompt, ai_metadata = editor.edit_prompt_with_ai(
                current_prompt, idea,
                attempt_num=attempt,
                total_attempts=attempts
            )

            if not modified_prompt:
                print(f"   ❌ 嘗試 {attempt} AI 修改失敗，跳過")
                continue

            # 顯示本次 prompt 摘要（前100字）
            print(f"   📝 Prompt 摘要: {modified_prompt[:100]}...")

            # 步驟 5：SD 生成
            print()
            print(f"   步驟 5：發送至 Stable Diffusion 生成圖片")

            if not sd_available:
                # 嘗試重新連接
                sd_available = editor.check_sd_connection()

            if not sd_available:
                print(f"   ❌ SD WebUI 未連接，跳過生成")
                print(f"   💡 可手動複製以下 Prompt 使用：")
                print(f"   {modified_prompt}")
                continue

            config = editor.load_json_config("test.json")
            if not config:
                print("   ❌ 無法載入 test.json 配置")
                continue

            config['prompt'] = modified_prompt
            config['seed'] = random.randint(1000000000, 9999999999)

            print(f"   ⚙️  {config['width']}x{config['height']} | "
                  f"{config['sampler_name']} | {config['steps']} steps | "
                  f"seed: {config['seed']}")
            print("   ⏳ 生成中...")

            gen_result = editor.generate_image(config)
            if gen_result:
                complete_metadata = editor._build_complete_metadata(
                    modified_prompt, config, ai_metadata
                )
                saved = editor.save_images(gen_result, complete_metadata)
                print(f"   ✅ 嘗試 {attempt} 完成，生成 {len(saved)} 張圖片")
            else:
                print(f"   ❌ 嘗試 {attempt} 生成失敗")

        print()
        print(f"✅ 第 {round_count} 輪完成，共嘗試 {attempts} 次")
        print()
        # 自動回到步驟 2，不更新 current_prompt（保持原始 prompt 不變）
        # 這樣每輪都基於同一基底進行不同方向的修改

    # ── 退出時顯示目前 Prompt ───────────────────────────────────
    print()
    print("=" * 70)
    print("📋 目前 Prompt（可直接複製使用）：")
    print("=" * 70)
    print(current_prompt)
    print("=" * 70)
    print()
    print("✨ 感謝使用 Prompt 精準編輯器！")


if __name__ == "__main__":
    main()
