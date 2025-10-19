import asyncio
from solomon_env.config import Settings
from solomon_env.llm_client import LLMClient

async def main():
    cfg = Settings.load()
    print("ENV OK — model:", cfg.openai_model)
    client = LLMClient(cfg)
    resp = await client.chat("Say: Solomon environment connected.")
    text = resp["choices"][0]["message"]["content"].strip()
    print("API OK — reply:\\n", text)

if __name__ == "__main__":
    asyncio.run(main())
