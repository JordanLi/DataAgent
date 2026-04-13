import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_llm():
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    # let's try THUDM/glm-4-9b-chat
    models_to_test = ["THUDM/glm-4-9b-chat", "Pro/THUDM/glm-4-9b-chat", "Qwen/Qwen2.5-7B-Instruct", "Pro/zai-org/GLM-4.7"]
    
    print(f"API Key: {api_key[:5]}...{api_key[-5:] if api_key else ''}")
    print(f"Base URL: {base_url}")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    for model in models_to_test:
        print(f"Testing Model: {model}")
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello!"}],
                temperature=0,
                stream=False,
                timeout=10.0
            )
            print("Success:", response.choices[0].message.content[:50])
        except Exception as e:
            print("Error:", repr(e))

asyncio.run(test_llm())
