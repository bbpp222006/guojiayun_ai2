import requests
import json
import openai
import asyncio
from load_data import load_data
import time 
import numpy as np  

BASE_URL = "http://192.10.50.139:11434/v1"
API_KEY = "aaa"
MODEL_NAME = "qwen2.5:3b"
TRY_TIME = 3

# 异步分类函数
async def classify_news(data, category_list):
    model = openai.AsyncOpenAI(
                    api_key=API_KEY,
                    base_url=BASE_URL,
                )
    
    try_time = 0
    temp_str = f"新闻标题：{data['title']}，关键词：{data['keywords']}，请根据关键词进行新闻分类"
    
    while True:
        response = await model.chat.completions.create(model=MODEL_NAME, messages=[{
            "role": "system", "content": f"""
                你是一个专业的新闻分类器，能够快速精简的从提供的文本中提取出新闻分类。
                分类的结果必须是以下列表中的一个：{category_list}。
                注意，你必须调用提供的函数进行信息提取，将提取的信息填入函数的参数中。
                直接返回提取的结果，不要回复多余的内容。
                """},
            {"role": "user", "content": f"""
                请根据以下材料，提取新闻分类：
                {temp_str}
                """},
            ], tool_choice="required", tools=[{
                "type": "function",
                "function": {
                    "name": "classification",
                    "description": "根据给定的新闻标题和关键词，进行新闻分类",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "新闻分类",
                            },
                        },
                        "required": ["category"],
                    },
                },
            }])

        tool_call = response.choices[0].message.tool_calls
        
        if tool_call:
            arguments = json.loads(tool_call[0].function.arguments)
            category = arguments["category"]
            if category not in category_list:
                print(f"分类结果不在列表中，返回内容：{category}，当前尝试次数：{try_time}")
                try_time += 1
            else:
                result = {
                    "news_id": data["news_id"],
                    "category": category,
                }
                # 保存到文件
                with open("result.json", "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                print(f"新闻ID: {result['news_id']}, 分类: {result['category']}")
                return result
        else:
            content = response.choices[0].message.content
            print(f"未进行工具调用，返回内容：{content}，当前尝试次数：{try_time}")
            try_time += 1
        if try_time >= TRY_TIME:
            # 随机选择一个分类作为默认分类
            category = np.random.choice(category_list)
            print(f"尝试次数过多，跳过该条数据，随机分类为：{category}")
            return {
                "news_id": data["news_id"],
                "category": category,
            }
    

# 限制并发数，控制最多同时运行的任务数量
async def classify_with_semaphore(semaphore, data, category_list):
    async with semaphore:
        return await classify_news(data, category_list)

async def main():
    # 加载数据
    test_data, category_list = load_data()

    # 设置并发任务的最大数量（比如最多同时运行 50 个任务）
    semaphore = asyncio.Semaphore(50)

    # 使用有限并发控制任务执行
    tasks = [classify_with_semaphore(semaphore, data, category_list) for data in test_data]

    # 执行任务
    results = await asyncio.gather(*tasks)

    print("分类完成！")

if __name__ == "__main__":
    start_time = time.time()
    loop = asyncio.get_event_loop()

    loop.run_until_complete(main())
    # loop.close()
    end_time = time.time()
    print(f"程序运行时间：{end_time - start_time}秒")

