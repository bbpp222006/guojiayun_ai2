import gradio as gr
import dashscope
from dashscope.audio.asr import Transcription
from dashscope.audio.tts import SpeechSynthesizer
from openai import OpenAI
import os
import json
from oss import *
import requests
from config import *
import logging
# 将 ffmpeg 路径添加到环境变量中
ffmpeg_path = r"C:\Program Files\ffmpeg-7.1-essentials_build\bin"
os.environ["PATH"] += os.pathsep + ffmpeg_path

def decode_asr(file_url):
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.1631.0'
    }

    response = requests.get(file_url, headers=header)
    sentence = response.json()["transcripts"][0]["sentences"][0]["text"]
    # print(sentence)
    return sentence

# 用于处理语音到文本
def speech_to_text(audio):
    
    # 上传音频文件到 OSS
    file_url = oss_client.upload_local_file_to_oss(audio)
    print(file_url)
    # 使用 DashScope 语音识别（ASR）模型进行转换
    task_response = dashscope.audio.asr.Transcription.async_call(
        model='paraformer-v2',
        file_urls=[file_url],
        language_hints=['zh', 'en']
    )
    
    while True:
        transcribe_response = dashscope.audio.asr.Transcription.wait(task=task_response.output.task_id)
        
        if transcribe_response.status_code == 200:
            if transcribe_response["output"]['task_status'] == 'SUCCEEDED':
                result_file_url = transcribe_response.output["results"][0]["transcription_url"]
                transcribed_text = decode_asr(result_file_url)
                return transcribed_text
            elif transcribe_response["output"]['task_status'] == 'PENDING':
                time.sleep(0.5)
                logging.info( "waiting")
            elif transcribe_response["output"]['task_status'] == 'FAILED':
                logging.error("Error: Transcription failed")
                return "Error: Transcription failed"
        else:
            logging.error("Error: Transcription failed")
            return "Error: Transcription failed"

# 用于生成文本到语音
def text_to_speech(text):
    # 使用 DashScope 语音合成（TTS）模型进行转换
    result = SpeechSynthesizer.call(model='sambert-zhichu-v1',
                                    text=text,
                                    sample_rate=48000,
                                    format='wav')
    
    if result.get_audio_data() is not None:
        # return result.get_audio_data()
        # 保存为音频文件
        audio_file = "output.wav"
        with open(audio_file, "wb") as f:
            f.write(result.get_audio_data())
        return audio_file
    else:
        return "Error: Text to speech failed"

# 用于大语言模型生成响应
def generate_response(text):
    # 设置 OpenAI API 客户端
    client = OpenAI(api_key=dashscope.api_key, 
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    
    completion = client.chat.completions.create(
        model="qwen-plus",  # 使用大语言模型
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': text}
        ]
    )
    
    response_text = completion.choices[0].message.content
    return response_text


# Gradio Web 应用
def process_audio_and_text(input_audio, input_text):
    transcribed_text = ""
    if input_audio:
        # 1. 将语音转为文本
        transcribed_text+="用户的语音内容："
        transcribed_text += speech_to_text(input_audio)
        transcribed_text+="\n"
    if input_text:
        transcribed_text+="用户的文本内容："
        transcribed_text += input_text
        transcribed_text+="\n"
    else:
        return "No input provided", ""

    logging.info(f"Transcribed text: {transcribed_text}")
    # 2. 用大语言模型生成响应
    response_text = generate_response(transcribed_text)
    
    # 3. 将响应文本转为语音
    audio_output = text_to_speech(response_text)
    oss_client.delete_all_resources()
    
    return audio_output, response_text  # 返回合成后的语音和生成的文本


if __name__ == "__main__":

    oss_client = OSSClient()

    oss_client.delete_all_resources()

    
    # 设置 API Key
    dashscope.api_key = dashscope_api_key  # 替换为你的API Key



    # 创建 Gradio 界面
    with gr.Blocks() as iface:
        # 音频输入
        input_audio = gr.Audio(source="microphone", type="filepath", label="Speak to AI")
        # 文本输入
        input_text = gr.Textbox(label="Or type text here", placeholder="Type your message here...", lines=2)
        # 发送按钮
        send_button = gr.Button("发送")
        
        # 音频输出和文本输出
        output_audio = gr.Audio(label="AI Response Audio")
        output_text = gr.Textbox(label="AI Response Text")

        # 按钮点击后触发的函数
        send_button.click(fn=process_audio_and_text, inputs=[input_audio, input_text], outputs=[output_audio, output_text])

    # 启动 Gradio Web 应用
    iface.launch()