import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_stream():
    client = AsyncOpenAI(api_key=os.getenv('LLM_API_KEY'), base_url=os.getenv('LLM_BASE_URL'))
    try:
        response = await client.chat.completions.create(
            model=os.getenv('LLM_MODEL'),
            messages=[{'role': 'user', 'content': 'Hello!'}],
            stream=True,
            timeout=10.0
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                print(content, end='', flush=True)
    except Exception as e:
        print(f"Error: {repr(e)}")

asyncio.run(test_stream())
