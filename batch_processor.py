"""
批量處理配置文件
支持多個 JSON 工作流的批量生成
"""
import os
import json
from sd_automation import SDAutomation
from typing import List
import time


class BatchProcessor:
    """批量處理器"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:7860", output_dir: str = "batch_outputs"):
        """
        初始化批量處理器
        
        Args:
            base_url: SD WebUI API 地址
            output_dir: 批量輸出目錄
        """
        self.sd = SDAutomation(base_url=base_url, output_dir=output_dir)
    
    def process_folder(self, folder_path: str, pattern: str = "*.json") -> dict:
        """
        處理文件夾中的所有 JSON 配置文件
        
        Args:
            folder_path: 配置文件夾路徑
            pattern: 文件匹配模式
            
        Returns:
            處理結果統計
        """
        import glob
        
        # 查找所有 JSON 文件
        json_files = glob.glob(os.path.join(folder_path, pattern))
        
        if not json_files:
            print(f"⚠️  在 {folder_path} 中沒有找到 JSON 文件")
            return {"total": 0, "success": 0, "failed": 0}
        
        print(f"\n📦 找到 {len(json_files)} 個配置文件")
        print("="*60)
        
        results = {
            "total": len(json_files),
            "success": 0,
            "failed": 0,
            "files": []
        }
        
        for idx, json_file in enumerate(json_files, 1):
            print(f"\n處理 [{idx}/{len(json_files)}]: {os.path.basename(json_file)}")
            print("-"*60)
            
            try:
                saved_files = self.sd.run_from_json(json_file, save_info=True)
                
                if saved_files:
                    results["success"] += 1
                    results["files"].append({
                        "config": json_file,
                        "outputs": saved_files,
                        "status": "success"
                    })
                else:
                    results["failed"] += 1
                    results["files"].append({
                        "config": json_file,
                        "outputs": [],
                        "status": "failed"
                    })
                
                # 避免過於頻繁的請求
                if idx < len(json_files):
                    print("\n⏳ 等待 2 秒後處理下一個...")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ 處理失敗: {str(e)}")
                results["failed"] += 1
                results["files"].append({
                    "config": json_file,
                    "outputs": [],
                    "status": "error",
                    "error": str(e)
                })
        
        # 輸出統計
        print("\n" + "="*60)
        print("📊 批量處理完成")
        print("="*60)
        print(f"總數: {results['total']}")
        print(f"成功: {results['success']} ✅")
        print(f"失敗: {results['failed']} ❌")
        
        return results
    
    def process_with_variations(self, json_path: str, variations: List[dict], 
                               output_prefix: str = "variation") -> list:
        """
        使用一個基礎配置生成多個變體
        
        Args:
            json_path: 基礎配置文件
            variations: 變體參數列表，每個字典包含要修改的參數
            output_prefix: 輸出前綴
            
        Returns:
            所有生成的圖片路徑列表
        """
        print(f"\n🎨 變體生成模式")
        print(f"基礎配置: {json_path}")
        print(f"變體數量: {len(variations)}")
        print("="*60)
        
        # 載入基礎配置
        base_config = self.sd.load_config_from_json(json_path)
        all_files = []
        
        for idx, variation in enumerate(variations, 1):
            print(f"\n生成變體 [{idx}/{len(variations)}]")
            print(f"變體參數: {variation}")
            print("-"*60)
            
            # 創建變體配置
            config = base_config.copy()
            config.update(variation)
            
            # 準備 payload
            payload = self.sd.prepare_payload(config)
            
            # 生成圖片
            response = self.sd.txt2img(payload)
            
            if response:
                # 保存圖片
                prefix = f"{output_prefix}_{idx}"
                saved_files = self.sd.save_images(response, prefix=prefix)
                all_files.extend(saved_files)
                
                if idx < len(variations):
                    time.sleep(1)
        
        print("\n" + "="*60)
        print(f"🎉 變體生成完成！共 {len(all_files)} 張圖片")
        print("="*60)
        
        return all_files


def example_batch_processing():
    """批量處理示例"""
    processor = BatchProcessor(
        base_url="http://127.0.0.1:7860",
        output_dir="batch_outputs"
    )
    
    # 處理整個文件夾
    results = processor.process_folder("configs", pattern="*.json")
    
    print(f"\n處理結果:")
    for item in results["files"]:
        print(f"  {os.path.basename(item['config'])}: {item['status']}")


def example_variations():
    """變體生成示例"""
    processor = BatchProcessor(
        base_url="http://127.0.0.1:7860",
        output_dir="variations"
    )
    
    # 定義變體 - 不同的採樣器
    variations = [
        {"sampler_name": "Euler a", "steps": 20},
        {"sampler_name": "DPM++ 2M", "steps": 25},
        {"sampler_name": "DPM++ SDE", "steps": 25},
        {"sampler_name": "UniPC", "steps": 20},
    ]
    
    # 生成變體
    files = processor.process_with_variations(
        json_path="test.json",
        variations=variations,
        output_prefix="sampler_test"
    )
    
    print(f"\n生成的圖片:")
    for f in files:
        print(f"  - {f}")


def example_seed_variations():
    """種子變體示例 - 生成多個不同種子的圖片"""
    processor = BatchProcessor(
        base_url="http://127.0.0.1:7860",
        output_dir="seed_variations"
    )
    
    # 使用不同的隨機種子
    variations = [
        {"seed": -1},  # 隨機種子
        {"seed": -1},
        {"seed": -1},
        {"seed": -1},
        {"seed": -1},
    ]
    
    files = processor.process_with_variations(
        json_path="test.json",
        variations=variations,
        output_prefix="random_seed"
    )
    
    return files


def example_resolution_variations():
    """解析度變體示例"""
    processor = BatchProcessor(
        base_url="http://127.0.0.1:7860",
        output_dir="resolution_tests"
    )
    
    # 測試不同解析度
    variations = [
        {"width": 512, "height": 512},
        {"width": 768, "height": 512},
        {"width": 512, "height": 768},
        {"width": 1024, "height": 768},
    ]
    
    files = processor.process_with_variations(
        json_path="test.json",
        variations=variations,
        output_prefix="resolution"
    )
    
    return files


if __name__ == "__main__":
    print("選擇執行模式:")
    print("1. 批量處理文件夾")
    print("2. 生成採樣器變體")
    print("3. 生成種子變體 (5張不同的隨機圖)")
    print("4. 生成解析度變體")
    
    choice = input("\n請輸入選項 (1-4): ").strip()
    
    if choice == "1":
        example_batch_processing()
    elif choice == "2":
        example_variations()
    elif choice == "3":
        example_seed_variations()
    elif choice == "4":
        example_resolution_variations()
    else:
        print("無效選項")
