import json
import re

def extract_and_filter_prompt(json_file_path):
    """從 JSON 文件中提取並過濾 prompt"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    prompt = data.get('prompt', '')
    
    # 要過濾的標籤列表
    tags_to_remove = [
        r'<lora:add_detail:1>',
        r'<lora:illustrious_masterpieces_v3:0\.8>',
        r'<lora:best_of_ai_styles_noob-vpred-1\.0_v2\.217-edm2-pass-c:0\.5>',
        r'<lora:noobai_ep11_stabilizer_v0\.205_fp16:0\.7>',
        r'<lora:9_NGNLStyle:0\.7>',
        r'absurdres',
        r'masterpiece',
        r'newest',
        r'detailed eyes',
        r'detailed background',
        r'perfect eyes',
        r'highly detailed face',
        r'perfect lighting',
        r'anime coloring',
        r'detailed hands',
        r'detailed clothes',
        r'best quality',
        r'very aesthetic',
        r'NGNL Style',
    ]
    
    # 移除標籤
    filtered_prompt = prompt
    for tag in tags_to_remove:
        filtered_prompt = re.sub(tag + r',?\s*', '', filtered_prompt)
    
    # 清理多餘的逗號和空格
    filtered_prompt = re.sub(r',\s*,', ',', filtered_prompt)
    filtered_prompt = re.sub(r'^\s*,\s*', '', filtered_prompt)
    filtered_prompt = re.sub(r',\s*$', '', filtered_prompt)
    filtered_prompt = re.sub(r'\s+', ' ', filtered_prompt).strip()
    
    return prompt, filtered_prompt

def main():
    json_file = r"c:\Users\陳洋\Desktop\stable-diffusion-webui\Api\test.json"
    
    print("=" * 80)
    print("Prompt 過濾器 - 提取角色特徵")
    print("=" * 80)
    print()
    
    # 提取和過濾 prompt
    original_prompt, filtered_prompt = extract_and_filter_prompt(json_file)
    
    print("原始 Prompt:")
    print("-" * 80)
    print(original_prompt)
    print()
    
    print("過濾後的 Prompt (角色特徵):")
    print("-" * 80)
    print(filtered_prompt)
    print()
    
    # 將結果保存到文件
    output_file = r"c:\Users\陳洋\Desktop\stable-diffusion-webui\Api\filtered_prompt.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("原始 Prompt:\n")
        f.write("=" * 80 + "\n")
        f.write(original_prompt + "\n\n")
        f.write("=" * 80 + "\n")
        f.write("過濾後的 Prompt (角色特徵):\n")
        f.write("=" * 80 + "\n")
        f.write(filtered_prompt + "\n\n")
        f.write("=" * 80 + "\n")
        f.write("分析:\n")
        f.write("=" * 80 + "\n")
        
        # 分析角色特徵
        parts = filtered_prompt.split(',')
        f.write("角色特徵標籤數量: " + str(len(parts)) + "\n\n")
        
        # 分類標籤
        character_tags = []
        appearance_tags = []
        clothing_tags = []
        pose_expression_tags = []
        scene_tags = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # 髮型和顏色
            if any(x in part.lower() for x in ['hair', 'bun', 'ponytail', 'twin']):
                appearance_tags.append(part)
            # 眼睛
            elif any(x in part.lower() for x in ['eye', 'pupil']):
                appearance_tags.append(part)
            # 體型
            elif any(x in part.lower() for x in ['chest', 'body', 'teen', 'child', 'adult']):
                appearance_tags.append(part)
            # 服裝
            elif any(x in part.lower() for x in ['dress', 'shirt', 'skirt', 'pants', 'sleeve', 'ornament', 'garter', 'ring', 'lace']):
                clothing_tags.append(part)
            # 表情和姿勢
            elif any(x in part.lower() for x in ['smile', 'blush', 'standing', 'sitting', 'looking']):
                pose_expression_tags.append(part)
            # 場景
            elif any(x in part.lower() for x in ['background', 'fantasy', 'outdoor', 'indoor', 'butterfly']):
                scene_tags.append(part)
            # 角色名稱和 lora
            elif 'lora' in part.lower() or 'rushia' in part.lower():
                character_tags.append(part)
            else:
                character_tags.append(part)
        
        if character_tags:
            f.write("角色標籤:\n  " + "\n  ".join(character_tags) + "\n\n")
        if appearance_tags:
            f.write("外觀特徵:\n  " + "\n  ".join(appearance_tags) + "\n\n")
        if clothing_tags:
            f.write("服裝標籤:\n  " + "\n  ".join(clothing_tags) + "\n\n")
        if pose_expression_tags:
            f.write("表情/姿勢:\n  " + "\n  ".join(pose_expression_tags) + "\n\n")
        if scene_tags:
            f.write("場景標籤:\n  " + "\n  ".join(scene_tags) + "\n\n")
    
    print(f"✓ 結果已保存到: {output_file}")
    print()
    
    # 顯示統計
    print("統計信息:")
    print("-" * 80)
    print(f"原始標籤長度: {len(original_prompt)} 字符")
    print(f"過濾後標籤長度: {len(filtered_prompt)} 字符")
    print(f"減少了: {len(original_prompt) - len(filtered_prompt)} 字符")
    print(f"標籤數量: {len([p for p in filtered_prompt.split(',') if p.strip()])}")
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
