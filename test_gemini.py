import asyncio
from livekit.plugins import openai as oai
from backend.config import settings
from livekit.agents.llm import ChatContext

llm = oai.LLM(model='gemini-1.5-flash', api_key=settings.GEMINI_API_KEY, base_url='https://generativelanguage.googleapis.com/v1beta/openai/')

async def main():
    ctx = ChatContext().append(text='hello', role='user')
    stream = llm.chat(chat_ctx=ctx)
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end='')

asyncio.run(main())
