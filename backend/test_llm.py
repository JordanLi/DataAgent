import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_llm():
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")

    print(f"API Key: {api_key[:5]}...{api_key[-5:] if api_key else ''}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello!"}],
            temperature=0,
            stream=False,
            timeout=10.0
        )
        print("Success:", response.choices[0].message.content)
    except Exception as e:
        print("Error:", repr(e))

asyncio.run(test_llm())