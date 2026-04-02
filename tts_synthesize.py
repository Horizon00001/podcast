import json
import asyncio
import edge_tts
import os
import re
import subprocess

# 配置角色配音
VOICE_MAP = {
    "主持人A": "zh-CN-YunxiNeural",  # 男声
    "主持人B": "zh-CN-XiaoxiaoNeural", # 女声
    "A": "zh-CN-YunxiNeural",          # 简写支持
    "B": "zh-CN-XiaoxiaoNeural"
}

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

def clean_text(text):
    # 去除括号中的情感提示，如 (赞叹地), （语气严肃）
    return re.sub(r'[\(（].*?[\)）]', '', text).strip()

async def synthesize_podcast(json_path, output_dir):
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 读取脚本
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    title = data.get("title", "podcast")
    sections = data.get("sections", [])
    
    print(f"开始合成播客: {title}")
    
    all_dialogues = []
    
    # 提取所有对话并处理音效提示
    for i, section in enumerate(sections):
        # 处理音效提示
        effect = section.get("audio_effect")
        if effect:
            print(f"[音效提示] 类型: {effect.get('effect_type')}, 描述: {effect.get('description')}")
        
        dialogues = section.get("dialogues", [])
        for dialogue in dialogues:
            speaker = dialogue.get("speaker")
            content = dialogue.get("content")
            cleaned_content = clean_text(content)
            voice = VOICE_MAP.get(speaker, DEFAULT_VOICE)
            all_dialogues.append({
                "voice": voice,
                "text": cleaned_content,
                "speaker": speaker
            })

    # 合成音频
    # 注意：为了生成一个完整的音频文件，我们可以将相同声音的连续对话合并，
    # 或者简单地按顺序一个接一个合成并写入同一个文件（edge-tts 支持流式写入）。
    
    output_file = os.path.join(output_dir, "podcast_full.mp3")
    
    print(f"正在生成完整音频: {output_file}")
    
    # 简单实现：逐条合成并追加到文件
    # 注意：edge-tts 的 Communicate 对象可以直接保存到文件。
    # 为了合并，我们可以先生成临时文件再合并，或者使用更高级的流处理。
    # 这里我们采用“为每一条生成独立文件，并打印进度”的策略，因为 edge-tts 不支持直接追加到 mp3。
    
    temp_files = []
    max_retries = 3
    retry_delay = 5

    for idx, d in enumerate(all_dialogues):
        temp_filename = os.path.join(output_dir, f"segment_{idx:03d}.mp3")
        
        # 检查是否已经生成过且文件有效（大于 1KB 认为是有效的）
        if os.path.exists(temp_filename) and os.path.getsize(temp_filename) > 1024:
            print(f"[{idx+1}/{len(all_dialogues)}] 片段已有效存在，跳过: {temp_filename}")
            temp_files.append(temp_filename)
            continue

        print(f"[{idx+1}/{len(all_dialogues)}] 正在合成 {d['speaker']}: {d['text'][:20]}...")
        
        for attempt in range(max_retries):
            try:
                communicate = edge_tts.Communicate(d['text'], d['voice'])
                await communicate.save(temp_filename)
                temp_files.append(temp_filename)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  合成失败 ({e})，正在进行第 {attempt+2} 次尝试 (等待 {retry_delay} 秒)...")
                    await asyncio.sleep(retry_delay)
                else:
                    print(f"  在 {max_retries} 次尝试后依然失败。请检查网络或 TTS 服务状态。")
                    # 如果中间失败了，我们可能不应该继续合并
                    return

    print("\n所有分段合成完成。")
    
    # 使用 ffmpeg 合并音频
    output_full = os.path.join(output_dir, "podcast_full.mp3")
    list_file = os.path.join(output_dir, "file_list.txt")
    
    print(f"正在合并为完整音频: {output_full}...")
    
    with open(list_file, 'w', encoding='utf-8') as f:
        for temp_file in temp_files:
            # ffmpeg concat 要求路径格式
            abs_path = os.path.abspath(temp_file).replace('\\', '/')
            f.write(f"file '{abs_path}'\n")
            
    try:
        # 使用 ffmpeg concat 合并
        subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', 
            '-i', list_file, '-c', 'copy', output_full
        ], check=True, capture_output=True)
        
        print(f"合并成功！完整音频已保存至: {output_full}")
        
        # 清理临时文件
        os.remove(list_file)
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
        
        print(f"清理完成，已删除 {len(temp_files)} 个分段文件。")
        
    except subprocess.CalledProcessError as e:
        print(f"合并失败: {e.stderr.decode('utf-8')}")
    except Exception as e:
        print(f"合并过程中出现错误: {str(e)}")

    print(f"总计处理了 {len(temp_files)} 个音频片段。")

if __name__ == "__main__":
    JSON_PATH = os.path.join("output", "podcast_script.json")
    OUTPUT_DIR = os.path.join("output", "audio")
    
    asyncio.run(synthesize_podcast(JSON_PATH, OUTPUT_DIR))
