"""
動漫角色自動化抽獎 + ComfyUI 自動生成
使用 Nvidia API 設計角色，批次生成多個角色圖片
改寫版：使用 ComfyUI API 替代 Stable Diffusion WebUI
"""
import os
import json
import random
import uuid
import io
import urllib.request
import urllib.parse
from datetime import datetime
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv
import websocket  # pip install websocket-client

# 從 .env 文件載入環境變數
load_dotenv()

# 角色類型（抽獎池）
CHARACTER_TYPES = [
    "清純少女 (innocent young girl, teenage, 15-17 years old)",
    "可愛少女 (cute girl, youthful, 16-18 years old)",
    "成熟女性 (mature woman, adult, 25-30 years old)",
    "活潑少女 (energetic girl, cheerful, 17-19 years old)",
]


class ComfyUIClient:
    """ComfyUI WebSocket 客戶端"""
    
    def __init__(self, server_address="127.0.0.1:8188"):
        """
        初始化 ComfyUI 客戶端
        
        Args:
            server_address: ComfyUI 服務器地址（格式：host:port）
        """
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        
    def queue_prompt(self, prompt):
        """
        提交工作流到 ComfyUI 隊列
        
        Args:
            prompt: 工作流 JSON 對象
            
        Returns:
            prompt_id: 任務 ID
        """
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
        response = urllib.request.urlopen(req)
        return json.loads(response.read())
    
    def get_image(self, filename, subfolder, folder_type):
        """
        從 ComfyUI 下載圖片
        
        Args:
            filename: 圖片文件名
            subfolder: 子文件夾
            folder_type: 文件夾類型
            
        Returns:
            圖片二進制數據
        """
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"http://{self.server_address}/view?{url_values}") as response:
            return response.read()
    
    def get_history(self, prompt_id):
        """
        獲取任務歷史記錄
        
        Args:
            prompt_id: 任務 ID
            
        Returns:
            歷史記錄 JSON
        """
        with urllib.request.urlopen(f"http://{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())
    
    def get_images(self, prompt):
        """
        提交工作流並等待圖片生成完成
        
        Args:
            prompt: 工作流 JSON 對象
            
        Returns:
            output_images: {node_id: [image_data, ...]}
        """
        # 連接 WebSocket
        ws = websocket.WebSocket()
        ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
        
        # 提交工作流
        prompt_response = self.queue_prompt(prompt)
        prompt_id = prompt_response['prompt_id']
        
        # 等待執行完成
        output_images = {}
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break  # 執行完成
            else:
                continue  # 預覽是二進制數據，跳過
        
        # 獲取生成的圖片
        history = self.get_history(prompt_id)[prompt_id]
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            images_output = []
            if 'images' in node_output:
                for image in node_output['images']:
                    image_data = self.get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output
        
        ws.close()
        return output_images


class AutoCharacterGenerator:
    """自動角色生成器（ComfyUI 版本）"""
    
    def __init__(self, comfyui_address="127.0.0.1:8188", output_dir="outputs"):
        """
        初始化
        
        Args:
            comfyui_address: ComfyUI 服務器地址
            output_dir: 輸出圖片目錄
        """
        self.client = ComfyUIClient(comfyui_address)
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
    
    def load_workflow_from_json(self, json_path):
        """從 JSON 載入 ComfyUI 工作流"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
            return workflow
        except Exception as e:
            print(f"❌ 載入工作流 JSON 失敗: {e}")
            return None
    
    def replace_prompt_in_workflow(self, workflow, new_prompt):
        """
        替換工作流中的正面提示詞
        
        Args:
            workflow: 原始工作流 JSON
            new_prompt: 新的提示詞
            
        Returns:
            更新後的工作流
        """
        # 根據 qwen image (1).json，節點 6 是正面提示詞
        if "6" in workflow and "inputs" in workflow["6"]:
            workflow["6"]["inputs"]["text"] = new_prompt
            print(f"   ✅ 已替換節點 6 的正面提示詞")
        else:
            print(f"   ⚠️  警告：未找到節點 6 或其 text 輸入")
        
        # 更新隨機種子（節點 3）
        if "3" in workflow and "inputs" in workflow["3"]:
            workflow["3"]["inputs"]["seed"] = random.randint(1000000000, 9999999999)
            print(f"   ✅ 已更新隨機種子: {workflow['3']['inputs']['seed']}")
        
        return workflow
    
    def check_comfyui_connection(self):
        """檢查 ComfyUI 連接"""
        try:
            response = urllib.request.urlopen(f"http://{self.client.server_address}/system_stats", timeout=5)
            if response.status == 200:
                return True
            return False
        except:
            return False
    
    def generate_image(self, workflow):
        """
        調用 ComfyUI API 生成圖片
        
        Args:
            workflow: 工作流 JSON
            
        Returns:
            output_images: {node_id: [image_data, ...]}
        """
        try:
            output_images = self.client.get_images(workflow)
            return output_images
        except Exception as e:
            print(f"   ❌ 圖片生成失敗: {str(e)}")
            return None
    
    def save_images(self, output_images, character_type):
        """
        保存生成的圖片
        
        Args:
            output_images: {node_id: [image_data, ...]}
            character_type: 角色類型
            
        Returns:
            saved_files: 保存的文件路徑列表
        """
        if not output_images:
            return []
        
        saved_files = []
        
        # 從角色類型提取簡短標籤作為文件名前綴
        type_tag = character_type.split('(')[0].strip()
        
        # 檢查該角色類型已有的文件數量，以便繼續編號
        existing_files = [f for f in os.listdir(self.date_dir) if f.startswith(type_tag) and f.endswith('.png')]
        start_index = len(existing_files) + 1
        
        file_number = start_index
        
        # 遍歷所有節點的輸出
        for node_id, images in output_images.items():
            for image_data in images:
                try:
                    # 打開圖片
                    image = Image.open(io.BytesIO(image_data))
                    
                    # 生成文件名：角色類型 + 序號
                    filename = f"{type_tag}{file_number}.png"
                    filepath = os.path.join(self.date_dir, filename)
                    
                    # 保存圖片
                    image.save(filepath, format='PNG')
                    saved_files.append(filepath)
                    
                    print(f"   ✅ 圖片已保存: {filename}")
                    print(f"      尺寸: {image.size[0]}x{image.size[1]}")
                    
                    file_number += 1
                    
                except Exception as e:
                    print(f"   ❌ 保存圖片失敗: {str(e)}")
        
        return saved_files
    
    def run(self, workflow_json_path="qwen image (1).json", batch_count=1):
        """
        運行完整流程
        
        Args:
            workflow_json_path: ComfyUI 工作流 JSON 文件路徑
            batch_count: 批次生成數量
            
        Returns:
            所有保存的圖片路徑列表
        """
        all_saved_files = []
        
        print("=" * 70)
        print("🎲 動漫角色自動化抽獎 + ComfyUI 生成")
        print("=" * 70)
        print(f"📊 批次模式：將生成 {batch_count} 個角色")
        print("=" * 70)
        print()
        
        # 步驟 1: 檢查 ComfyUI 連接（只檢查一次）
        print("步驟 1: 檢查 ComfyUI 連接")
        print("-" * 70)
        if not self.check_comfyui_connection():
            print(f"❌ 無法連接到 ComfyUI: {self.client.server_address}")
            print("   請確認 ComfyUI 是否正在運行")
            print("   啟動命令: python main.py")
            return []
        print(f"✅ 成功連接到 ComfyUI")
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
            
            # 步驟 4: 載入工作流
            print(f"步驟 4: 載入 ComfyUI 工作流")
            print("-" * 70)
            workflow = self.load_workflow_from_json(workflow_json_path)
            
            if not workflow:
                print(f"❌ 批次 {batch_num} 工作流載入失敗，跳過")
                print()
                continue
            
            print(f"✅ 工作流載入成功")
            print(f"   工作流文件: {workflow_json_path}")
            print(f"   節點數量: {len(workflow)}")
            print()
            
            # 步驟 5: 替換提示詞
            print(f"步驟 5: 替換工作流中的提示詞")
            print("-" * 70)
            workflow = self.replace_prompt_in_workflow(workflow, character_design)
            print(f"✅ 提示詞長度: {len(character_design)} 字符")
            print()
            
            # 步驟 6: 生成圖片
            print(f"步驟 6: 提交到 ComfyUI 生成圖片")
            print("-" * 70)
            print("⏳ 生成中，請稍候...")
            
            output_images = self.generate_image(workflow)
            
            if not output_images:
                print(f"❌ 批次 {batch_num} 圖片生成失敗，跳過")
                print()
                continue
            
            print("✅ 圖片生成完成")
            print()
            
            # 步驟 7: 保存圖片
            print(f"步驟 7: 保存圖片")
            print("-" * 70)
            saved_files = self.save_images(output_images, character_type)
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
    print("🎲 動漫角色自動化批次生成系統（ComfyUI 版）")
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
        comfyui_address="127.0.0.1:8188",
        output_dir="outputs"
    )
    
    # 運行完整流程（batch 模式）
    try:
        saved_files = generator.run(workflow_json_path="qwen image (1).json", batch_count=batch_count)
        
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
