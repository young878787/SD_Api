import os
import random
import datetime
from openai import OpenAI
from dotenv import load_dotenv

# 從 .env 文件載入環境變數
load_dotenv()

# 強化提示詞（固定前綴）
QUALITY_TAGS = "<lora:add_detail:1>,<lora:illustrious_masterpieces_v3:0.8>,<lora:best_of_ai_styles_noob-vpred-1.0_v2.217-edm2-pass-c:0.5>,<lora:noobai_ep11_stabilizer_v0.205_fp16:0.7>,<lora:9_NGNLStyle:0.7>,absurdres,masterpiece,newest,detailed eyes,detailed background,perfect eyes,highly detailed face,perfect lighting,anime coloring,detailed hands,detailed clothes,best quality,very aesthetic,NGNL Style,"

# 角色類型（抽獎池）
CHARACTER_TYPES = [
    "清純少女 (innocent young girl, teenage, 15-17 years old)",
    "可愛少女 (cute girl, youthful, 16-18 years old)",
    "成熟女性 (mature woman, adult, 25-30 years old)",
    "優雅女性 (elegant woman, sophisticated, 28-35 years old)",
    "活潑少女 (energetic girl, cheerful, 17-19 years old)",
]

def random_character_type():
    """隨機抽取角色類型"""
    return random.choice(CHARACTER_TYPES)

def design_complete_character_with_gpt4o(character_type):
    """使用 GitHub Models API (GPT-4o) 設計完整的角色"""
    
    # 從 .env 文件獲取 GitHub Token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("錯誤：未找到 GITHUB_TOKEN")
        print("請確保：")
        print("  1. 創建 .env 文件")
        print("  2. 添加 GITHUB_TOKEN=你的token")
        print("  3. 查看 docs/快速開始指南.md 了解詳情")
        return None
    
    endpoint = "https://models.inference.ai.azure.com"
    model_name = "gpt-4o"
    
    # 創建 OpenAI 客戶端
    client = OpenAI(
        base_url=endpoint,
        api_key=token,
    )
    
    # 構建提示詞
    system_prompt = """你是一位專業的動漫角色設計師。你需要創造一個全新的、完整的動漫角色。

要求：
1. 設計一個完整的原創角色（不要參考現有角色）
2. 包括所有細節：外貌、髮型、眼睛、身材、服裝、配飾等
3. 描述要詳細且具有個性
4. 使用 Stable Diffusion 風格的標籤格式輸出
5. 用英文輸出，使用逗號分隔的標籤格式
6. 要有創意且美觀，符合動漫美學
7. 不要包含任何質量增強標籤（如 masterpiece, best quality 等）
8. 不要包含任何 lora 標籤
9. 只輸出角色描述標籤，不要有其他說明文字"""

    user_prompt = f"""請設計一個全新的動漫角色，角色類型：{character_type}

請包括以下所有元素（用英文標籤，逗號分隔）：

1. 基本設定：
   - 年齡段和氣質
   - 整體風格（如：可愛、優雅、帥氣等）

2. 髮型特徵：
   - 髮色（具體顏色）
   - 髮型（長短、樣式）
   - 特殊髮飾或髮型細節

3. 面部特徵：
   - 眼睛顏色
   - 眼睛形狀特點
   - 瞳孔細節
   - 表情

4. 身材特徵：
   - 體型描述
   - 身高感覺

5. 服裝設計（完整套裝）：
   - 上衣款式、顏色、材質、細節
   - 下裝款式、顏色、材質、細節
   - 外套或其他層次（如果有）

6. 配飾：
   - 首飾（項鍊、耳環、手鐲等）
   - 其他裝飾品
   - 髮飾

7. 鞋子：
   - 鞋子款式、顏色

8. 姿勢和氛圍：
   - 站姿或動作
   - 表情
   - 整體氛圍

9. 場景設定：
   - 背景氛圍
   - 環境元素

請直接輸出標籤，格式如：hair_color, hairstyle, eye_color, body_type, clothing_item, accessory, pose, background,...

不要有任何額外的說明或標題，只要標籤列表。"""

    try:
        print("正在使用 GitHub Models GPT-4o 設計角色...")
        print(f"模型: {model_name}")
        print(f"角色類型: {character_type}")
        print("-" * 60)
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.9,  # 提高創意度
            top_p=0.95,
            max_tokens=1500,
            model=model_name
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"API 調用錯誤: {e}")
        return None


def main():
    print("=" * 70)
    print("🎲 動漫角色自動化抽獎設計助手 - 使用 GitHub Models GPT-4o")
    print("=" * 70)
    print()
    
    # 步驟 1: 隨機抽取角色類型
    print("步驟 1: 隨機抽取角色類型（抽獎中...）")
    print("-" * 70)
    character_type = random_character_type()
    print(f"🎯 抽中角色類型: {character_type}")
    print()
    
    # 步驟 2: 使用 GPT-4o 設計完整角色
    print("步驟 2: AI 設計完整角色")
    print("-" * 70)
    character_design = design_complete_character_with_gpt4o(character_type)
    
    if character_design:
        # 清理 AI 輸出（移除可能的多餘空白和換行）
        character_design = character_design.strip()
        
        print("✅ AI 設計的角色描述:")
        print(character_design)
        print()
        
        # 步驟 3: 組合完整的 Prompt
        print("步驟 3: 組合完整 Prompt")
        print("-" * 70)
        complete_prompt = QUALITY_TAGS + character_design
        
        print("📋 完整的 Stable Diffusion Prompt:")
        print(complete_prompt)
        print()
        
        # 步驟 4: 保存到 docs 資料夾
        print("步驟 4: 保存結果")
        print("-" * 70)
        
        # 生成帶時間戳的文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"docs/character_design_{timestamp}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("🎲 動漫角色自動化抽獎設計結果\n")
            f.write("=" * 70 + "\n")
            f.write(f"生成時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"角色類型: {character_type}\n")
            f.write("=" * 70 + "\n\n")
            
            f.write("【角色描述】\n")
            f.write("-" * 70 + "\n")
            f.write(character_design + "\n\n")
            
            f.write("【質量增強標籤】\n")
            f.write("-" * 70 + "\n")
            f.write(QUALITY_TAGS + "\n\n")
            
            f.write("【完整 Prompt（可直接用於 Stable Diffusion）】\n")
            f.write("=" * 70 + "\n")
            f.write(complete_prompt + "\n\n")
            
            f.write("=" * 70 + "\n")
            f.write("使用說明：\n")
            f.write("1. 複製【完整 Prompt】到 Stable Diffusion 的 prompt 欄位\n")
            f.write("2. 設置合適的參數（採樣器、步數等）\n")
            f.write("3. 生成圖片\n")
            f.write("=" * 70 + "\n")
        
        print(f"✅ 結果已保存到: {output_file}")
        print()
        
        # 顯示統計
        print("📊 統計信息:")
        print("-" * 70)
        print(f"角色描述長度: {len(character_design)} 字符")
        print(f"質量標籤長度: {len(QUALITY_TAGS)} 字符")
        print(f"完整 Prompt 長度: {len(complete_prompt)} 字符")
        print(f"標籤數量: {len(complete_prompt.split(','))} 個")
    else:
        print("❌ 角色設計失敗")
    
    print()
    print("=" * 70)
    print("💡 提示：再次運行腳本可以抽取新的角色類型並設計新角色！")
    print("=" * 70)

if __name__ == "__main__":
    main()
