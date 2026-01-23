"""
Stable Diffusion WebUI 自動化腳本
支持從 JSON 讀取完整配置並自動生成圖片
"""
import requests
import json
import base64
import io
import random
from PIL import Image
from datetime import datetime
import os
from typing import Dict, Any, Optional


class SDAutomation:
    """Stable Diffusion 自動化類"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:7860", output_dir: str = "outputs"):
        """
        初始化自動化工具
        
        Args:
            base_url: SD WebUI 的 API 地址
            output_dir: 輸出圖片的目錄
        """
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        
        # 確保輸出目錄存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"✅ 已創建輸出目錄: {output_dir}")
    
    def load_config_from_json(self, json_path: str) -> Dict[str, Any]:
        """
        從 JSON 文件讀取配置
        
        Args:
            json_path: JSON 配置文件路徑
            
        Returns:
            配置字典
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ 成功載入配置: {json_path}")
            return config
        except FileNotFoundError:
            print(f"❌ 找不到配置文件: {json_path}")
            raise
        except json.JSONDecodeError as e:
            print(f"❌ JSON 格式錯誤: {e}")
            raise
    
    def prepare_payload(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        準備 API payload
        將 JSON 配置轉換為 SD WebUI API 格式
        
        Args:
            config: 從 JSON 讀取的配置
            
        Returns:
            準備好的 payload
        """
        # 基本參數映射
        payload = {
            # 提示詞相關
            "prompt": config.get("prompt", ""),
            "negative_prompt": config.get("negative_prompt", ""),
            
            # 圖片尺寸
            "width": config.get("width", 512),
            "height": config.get("height", 512),
            
            # 採樣參數
            "steps": config.get("steps", 20),
            "sampler_name": config.get("sampler_name", "Euler a"),
            "scheduler": config.get("scheduler", "Automatic"),
            "cfg_scale": config.get("cfg_scale", 7),
            
            # 批次設定
            "batch_size": config.get("batch_size", 1),
            "n_iter": config.get("n_iter", 1),
            
            # 種子 - 自動生成10位數隨機種子
            "seed": random.randint(1000000000, 9999999999),
            "subseed": config.get("subseed", -1),
            "subseed_strength": config.get("subseed_strength", 0),
            "seed_resize_from_h": config.get("seed_resize_from_h", -1),
            "seed_resize_from_w": config.get("seed_resize_from_w", -1),
            "seed_enable_extras": config.get("seed_enable_extras", True),
            
            # Hires Fix
            "enable_hr": config.get("enable_hr", False),
            "denoising_strength": config.get("denoising_strength", 0.7),
            "hr_scale": config.get("hr_scale", 2),
            "hr_upscaler": config.get("hr_upscaler", "Latent"),
            "hr_second_pass_steps": config.get("hr_second_pass_steps", 0),
            "hr_resize_x": config.get("hr_resize_x", 0),
            "hr_resize_y": config.get("hr_resize_y", 0),
            "hr_scheduler": config.get("hr_scheduler", "Automatic"),
            "hr_prompt": config.get("hr_prompt", ""),
            "hr_negative_prompt": config.get("hr_negative_prompt", ""),
            
            # 其他設定
            "styles": config.get("styles", []),
            "restore_faces": config.get("restore_faces", False),
            "tiling": config.get("tiling", False),
            "do_not_save_samples": config.get("do_not_save_samples", False),
            "do_not_save_grid": config.get("do_not_save_grid", False),
            
            # S 參數 (用於高級採樣控制)
            "s_min_uncond": config.get("s_min_uncond", 0),
            "s_churn": config.get("s_churn", 0),
            "s_tmax": config.get("s_tmax"),
            "s_tmin": config.get("s_tmin", 0),
            "s_noise": config.get("s_noise", 1),
            
            # 覆蓋設定
            "override_settings": config.get("override_settings", {}),
            "override_settings_restore_afterwards": config.get(
                "override_settings_restore_afterwards", True
            ),
            
            # 腳本相關
            "script_name": config.get("script_name"),
            "script_args": config.get("script_args", []),
            
            # 額外網絡
            "disable_extra_networks": config.get("disable_extra_networks", False),
            
            # 註解
            "comments": config.get("comments", {}),
        }
        
        # 添加 alwayson_scripts (所有插件配置)
        if "alwayson_scripts" in config:
            payload["alwayson_scripts"] = config["alwayson_scripts"]
        
        return payload
    
    def txt2img(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        調用 txt2img API 生成圖片
        
        Args:
            payload: API payload
            
        Returns:
            API 響應，失敗返回 None
        """
        api_url = f"{self.base_url}/sdapi/v1/txt2img"
        
        print(f"\n🚀 開始生成圖片...")
        print(f"   尺寸: {payload['width']}x{payload['height']}")
        print(f"   採樣: {payload['sampler_name']} ({payload['steps']} steps)")
        print(f"   提示詞: {payload['prompt'][:100]}...")
        
        try:
            response = requests.post(api_url, json=payload, timeout=300)
            
            if response.status_code == 200:
                print("✅ API 請求成功")
                return response.json()
            else:
                print(f"❌ API 請求失敗 (狀態碼: {response.status_code})")
                print(f"   錯誤信息: {response.text[:500]}")
                return None
                
        except requests.exceptions.Timeout:
            print("❌ 請求超時！生成時間過長")
            return None
        except requests.exceptions.ConnectionError:
            print(f"❌ 無法連接到 SD WebUI: {self.base_url}")
            print("   請確認 SD WebUI 是否正在運行")
            return None
        except Exception as e:
            print(f"❌ 發生錯誤: {str(e)}")
            return None
    
    def save_images(self, response: Dict[str, Any], prefix: str = "output") -> list:
        """
        保存生成的圖片
        
        Args:
            response: API 響應
            prefix: 文件名前綴
            
        Returns:
            保存的文件路徑列表
        """
        if not response or 'images' not in response:
            print("❌ 響應中沒有圖片數據")
            return []
        
        saved_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for idx, img_data in enumerate(response['images']):
            try:
                # 解碼 base64 圖片
                # 注意：有些 API 返回的是 "data:image/png;base64,xxxxx" 格式
                if ',' in img_data:
                    img_data = img_data.split(',', 1)[1]
                
                image_bytes = base64.b64decode(img_data)
                image = Image.open(io.BytesIO(image_bytes))
                
                # 生成文件名
                filename = f"{prefix}_{timestamp}_{idx+1}.png"
                filepath = os.path.join(self.output_dir, filename)
                
                # 保存圖片
                image.save(filepath, format='PNG')
                saved_files.append(filepath)
                
                print(f"✅ 圖片已保存: {filepath}")
                print(f"   尺寸: {image.size[0]}x{image.size[1]}")
                
            except Exception as e:
                print(f"❌ 保存第 {idx+1} 張圖片失敗: {str(e)}")
        
        return saved_files
    
    def check_connection(self) -> bool:
        """
        檢查 SD WebUI 連接
        
        Returns:
            是否連接成功
        """
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/sd-models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                print(f"✅ 成功連接到 SD WebUI")
                print(f"   可用模型數量: {len(models)}")
                return True
            else:
                print(f"⚠️  連接異常 (狀態碼: {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ 無法連接到 SD WebUI: {self.base_url}")
            print(f"   錯誤: {str(e)}")
            return False
    
    def run_from_json(self, json_path: str) -> list:
        """
        從 JSON 配置運行完整流程
        
        Args:
            json_path: JSON 配置文件路徑
            
        Returns:
            保存的圖片路徑列表
        """
        print("="*60)
        print("🎨 Stable Diffusion 自動化生成")
        print("="*60)
        
        # 1. 檢查連接
        if not self.check_connection():
            return []
        
        # 2. 載入配置
        config = self.load_config_from_json(json_path)
        
        # 3. 準備 payload (自動生成隨機種子)
        payload = self.prepare_payload(config)
        print(f"   使用隨機種子: {payload['seed']}")
        
        # 4. 生成圖片
        response = self.txt2img(payload)
        
        if not response:
            return []
        
        # 5. 保存圖片
        saved_files = self.save_images(response)
        
        print("\n" + "="*60)
        print(f"🎉 完成！共生成 {len(saved_files)} 張圖片")
        print("="*60)
        
        return saved_files


def main():
    """主函數 - 使用示例"""
    
    # 創建自動化實例
    sd = SDAutomation(
        base_url="http://127.0.0.1:7860",
        output_dir="outputs"
    )
    
    # 從 JSON 運行
    json_path = "test.json"  # 你的配置文件路徑
    
    try:
        saved_files = sd.run_from_json(json_path)
        
        if saved_files:
            print(f"\n✨ 成功生成圖片:")
            for file in saved_files:
                print(f"   - {file}")
        else:
            print("\n⚠️  沒有生成任何圖片")
            
    except KeyboardInterrupt:
        print("\n⚠️  用戶中斷")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
