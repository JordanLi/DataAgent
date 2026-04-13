import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_full_prompt():
    client = AsyncOpenAI(api_key=os.getenv('LLM_API_KEY'), base_url=os.getenv('LLM_BASE_URL'))
    
    system_prompt = """你是一个专业的数据分析助手和 MySQL 专家。根据用户的自然语言问题，生成精确的 MySQL SELECT 查询语句。

## 规则
1. 只生成 SELECT 语句
2. 必须添加 LIMIT（默认 100）
3. 只使用下方 Schema 中存在的表和字段

## Schema 信息
表: orders
  - id: int 主键
  - user_id: int
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "上个月订单量最多的商品是哪个"}
    ]
    
    print(f"Sending to {os.getenv('LLM_MODEL')}...")
    try:
        response = await client.chat.completions.create(
            model=os.getenv('LLM_MODEL'),
            messages=messages,
            stream=True,
            timeout=20.0
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                print(content, end='', flush=True)
    except Exception as e:
        print(f"\\nError: {repr(e)}")

asyncio.run(test_full_prompt())