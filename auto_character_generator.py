"""
動漫角色自動化抽獎 + Stable Diffusion 自動生成
使用 Nvidia API 設計角色，批次生成多個角色圖片
"""
import os
import json
import random
import requests
import base64
import io
from datetime import datetime
from PIL import Image
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
    "活潑少女 (energetic girl, cheerful, 17-19 years old)",
]


class AutoCharacterGenerator:
    """自動角色生成器"""
    
    def __init__(self, sd_url="http://127.0.0.1:7860", output_dir="outputs"):
        """
        初始化
        
        Args:
            sd_url: Stable Diffusion WebUI API 地址
            output_dir: 輸出圖片目錄
        """
        self.sd_url = sd_url.rstrip('/')
        self.output_dir = output_dir
        
        # 創建日期資料夾
        today = datetime.now().strftime("%Y-%m-%d")
        self.date_dir = os.path.join(output_dir, today)
        
        # 確保日期資料夾存在
        if not os.path.exists(self.date_dir):
            os.makedirs(self.date_dir)
            print(f"📁 創建日期資料夾: {self.date_dir}")
    
    def random_character_type(self):
        """隨機抽取角色類型"""
        return random.choice(CHARACTER_TYPES)
    
    def design_character_with_ai(self, character_type):
        """使用 Nvidia API 設計完整角色"""
        
        # 從 .env 讀取 Nvidia API 配置
        api_key = os.getenv("NVIDIA_API_KEY")
        base_url = os.getenv("NVIDIA_BASE_URL")
        model_name = os.getenv("NVIDIA_MODEL_NAME")
        
        if not api_key:
            print("❌ 錯誤：未找到 NVIDIA_API_KEY")
            print("   請在 .env 文件中添加 NVIDIA_API_KEY")
            return None
        
        if not base_url:
            print("❌ 錯誤：未找到 NVIDIA_BASE_URL")
            print("   請在 .env 文件中添加 NVIDIA_BASE_URL")
            return None
            
        if not model_name:
            print("❌ 錯誤：未找到 NVIDIA_MODEL_NAME")
            print("   請在 .env 文件中添加 NVIDIA_MODEL_NAME")
            return None
        
        # 創建 OpenAI 客戶端（Nvidia API 兼容 OpenAI 接口）
        client = OpenAI(base_url=base_url, api_key=api_key)
        
        system_prompt = """你是一位專業的動漫角色設計師。需要創造一個全新的、完整的動漫角色。

要求：
1. 設計一個完整的原創角色
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

1. 基本設定：年齡段和氣質、整體風格
2. 髮型特徵：髮色、髮型、髮飾
3. 面部特徵：眼睛顏色、形狀、瞳孔細節、表情
4. 身材特徵：體型、身高
5. 服裝設計：上衣、下裝、外套、材質、細節
6. 配飾：首飾、裝飾品
7. 鞋子：款式、顏色
8. 姿勢和氛圍：站姿、坐姿、動作、表情
9. 場景設定：背景、環境

請直接輸出標籤，格式如：hair_color, hairstyle, eye_color, body_type, clothing_item, accessory, pose, background,...

不要有任何額外的說明或標題，只要標籤列表。"""

        try:
            print(f"   正在使用 Nvidia API ({model_name}) 設計角色...")
            
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,
                top_p=0.95,
                max_tokens=1500,
                model=model_name
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"   ❌ API 調用錯誤: {e}")
            return None
    
    def load_config_from_json(self, json_path):
        """從 JSON 載入配置"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"❌ 載入 JSON 失敗: {e}")
            return None
    
    def replace_prompt(self, config, new_prompt):
        """
        替換配置中的 prompt，保留其他所有參數
        
        Args:
            config: 原始配置
            new_prompt: 新的完整 prompt（含質量標籤）
            
        Returns:
            更新後的配置
        """
        config['prompt'] = new_prompt
        
        # 自動生成新的隨機種子
        config['seed'] = random.randint(1000000000, 9999999999)
        
        return config
    
    def check_sd_connection(self):
        """檢查 SD WebUI 連接"""
        try:
            response = requests.get(f"{self.sd_url}/sdapi/v1/sd-models", timeout=5)
            if response.status_code == 200:
                return True
            return False
        except:
            return False
    
    def generate_image(self, payload):
        """調用 SD WebUI API 生成圖片"""
        api_url = f"{self.sd_url}/sdapi/v1/txt2img"
        
        try:
            response = requests.post(api_url, json=payload, timeout=300)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"   ❌ API 請求失敗 (狀態碼: {response.status_code})")
                return None
                
        except requests.exceptions.Timeout:
            print("   ❌ 請求超時！生成時間過長")
            return None
        except requests.exceptions.ConnectionError:
            print(f"   ❌ 無法連接到 SD WebUI: {self.sd_url}")
            return None
        except Exception as e:
            print(f"   ❌ 發生錯誤: {str(e)}")
            return None
    
    def save_images(self, response, character_type):
        """保存生成的圖片"""
        if not response or 'images' not in response:
            return []
        
        saved_files = []
        
        # 從角色類型提取簡短標籤作為文件名前綴
        type_tag = character_type.split('(')[0].strip()
        
        # 檢查該角色類型已有的文件數量，以便繼續編號
        existing_files = [f for f in os.listdir(self.date_dir) if f.startswith(type_tag) and f.endswith('.png')]
        start_index = len(existing_files) + 1
        
        for idx, img_data in enumerate(response['images']):
            try:
                # 解碼 base64
                if ',' in img_data:
                    img_data = img_data.split(',', 1)[1]
                
                image_bytes = base64.b64decode(img_data)
                image = Image.open(io.BytesIO(image_bytes))
                
                # 生成文件名：角色類型 + 序號
                file_number = start_index + idx
                filename = f"{type_tag}{file_number}.png"
                filepath = os.path.join(self.date_dir, filename)
                
                # 保存圖片
                image.save(filepath, format='PNG')
                saved_files.append(filepath)
                
                print(f"   ✅ 圖片已保存: {filename}")
                print(f"      尺寸: {image.size[0]}x{image.size[1]}")
                
            except Exception as e:
                print(f"   ❌ 保存第 {idx+1} 張圖片失敗: {str(e)}")
        
        return saved_files
    
    def run(self, json_path="test.json", batch_count=1):
        """
        運行完整流程
        
        Args:
            json_path: JSON 配置文件路徑
            batch_count: 批次生成數量
            
        Returns:
            所有保存的圖片路徑列表
        """
        all_saved_files = []
        
        print("=" * 70)
        print("🎲 動漫角色自動化抽獎 + Stable Diffusion 生成")
        print("=" * 70)
        print(f"📊 批次模式：將生成 {batch_count} 個角色")
        print("=" * 70)
        print()
        
        # 步驟 1: 檢查 SD WebUI 連接（只檢查一次）
        print("步驟 1: 檢查 Stable Diffusion WebUI 連接")
        print("-" * 70)
        if not self.check_sd_connection():
            print(f"❌ 無法連接到 SD WebUI: {self.sd_url}")
            print("   請確認 SD WebUI 是否正在運行")
            return []
        print(f"✅ 成功連接到 SD WebUI")
        print()
        
        # 批次循環
        for batch_num in range(1, batch_count + 1):
            print("=" * 70)
            print(f"🎯 批次 {batch_num}/{batch_count}")
            print("=" * 70)
            print()
            
            # 步驟 2: 隨機抽取角色類型
            print(f"步驟 2: 隨機抽取角色類型（抽獎中...）")
            print("-" * 70)
            character_type = self.random_character_type()
            print(f"🎯 抽中角色類型: {character_type}")
            print()
            
            # 步驟 3: AI 設計角色
            print(f"步驟 3: AI 設計完整角色")
            print("-" * 70)
            character_design = self.design_character_with_ai(character_type)
            
            if not character_design:
                print(f"❌ 批次 {batch_num} 角色設計失敗，跳過")
                print()
                continue
            
            print(f"✅ AI 設計的角色描述:")
            print(f"   {character_design[:100]}...")
            print()
            
            # 步驟 4: 組合完整 Prompt
            print(f"步驟 4: 組合完整 Prompt")
            print("-" * 70)
            complete_prompt = QUALITY_TAGS + character_design
            print(f"✅ 完整 Prompt 長度: {len(complete_prompt)} 字符")
            print(f"   標籤數量: {len(complete_prompt.split(','))} 個")
            print()
            
            # 步驟 5: 載入 JSON 配置
            print(f"步驟 5: 載入配置並替換提示詞")
            print("-" * 70)
            config = self.load_config_from_json(json_path)
            
            if not config:
                print(f"❌ 批次 {batch_num} 配置載入失敗，跳過")
                print()
                continue
            
            # 替換 prompt，保留其他所有參數
            config = self.replace_prompt(config, complete_prompt)
            
            print(f"✅ 配置載入成功")
            print(f"   尺寸: {config['width']}x{config['height']}")
            print(f"   採樣: {config['sampler_name']} ({config['steps']} steps)")
            print(f"   隨機種子: {config['seed']}")
            print()
            
            # 步驟 6: 生成圖片
            print(f"步驟 6: 發送到 Stable Diffusion 生成圖片")
            print("-" * 70)
            print("⏳ 生成中，請稍候...")
            
            response = self.generate_image(config)
            
            if not response:
                print(f"❌ 批次 {batch_num} 圖片生成失敗，跳過")
                print()
                continue
            
            print("✅ 圖片生成完成")
            print()
            
            # 步驟 7: 保存圖片
            print(f"步驟 7: 保存圖片")
            print("-" * 70)
            saved_files = self.save_images(response, character_type)
            all_saved_files.extend(saved_files)
            
            print()
            print(f"✅ 批次 {batch_num} 完成！生成 {len(saved_files)} 張圖片")
            print()
            
            # 如果不是最後一個批次，顯示進度
            if batch_num < batch_count:
                print(f"⏭️  準備下一個批次... ({batch_num}/{batch_count} 完成)")
                print()
        
        # 總結
        print()
        print("=" * 70)
        print(f"🎉 全部完成！共生成 {len(all_saved_files)} 張圖片")
        print("=" * 70)
        print()
        
        # 顯示所有生成的圖片
        if all_saved_files:
            print("✨ 所有生成的圖片:")
            for idx, file in enumerate(all_saved_files, 1):
                print(f"   {idx}. {file}")
            print()
            print("💡 提示：再次運行可以生成更多角色圖片！")
        
        return all_saved_files


def main():
    """主函數"""
    
    print("=" * 70)
    print("🎲 動漫角色自動化批次生成系統")
    print("=" * 70)
    print()
    
    # 詢問用戶要生成幾個角色
    while True:
        try:
            batch_count = input("請輸入要生成的角色數量（1-20）: ").strip()
            batch_count = int(batch_count)
            
            if 1 <= batch_count <= 20:
                break
            else:
                print("❌ 請輸入 1 到 20 之間的數字")
        except ValueError:
            print("❌ 請輸入有效的數字")
        except KeyboardInterrupt:
            print("\n⚠️  用戶取消")
            return
    
    print()
    print(f"✅ 將生成 {batch_count} 個角色")
    print()
    
    # 創建生成器實例
    generator = AutoCharacterGenerator(
        sd_url="http://127.0.0.1:7860",
        output_dir="outputs"
    )
    
    # 運行完整流程（batch 模式）
    try:
        saved_files = generator.run(json_path="test.json", batch_count=batch_count)
        
        if not saved_files:
            print("\n⚠️  沒有生成任何圖片")
        else:
            print(f"\n🎊 成功完成！共生成 {len(saved_files)} 張圖片")
            
    except KeyboardInterrupt:
        print("\n⚠️  用戶中斷")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
