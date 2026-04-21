import asyncio

from backend.app.services.tts_service import TTSService


async def synthesize_podcast(json_path, output_dir):
    service = TTSService(output_dir)
    await service.synthesize_podcast(json_path)


if __name__ == "__main__":
    JSON_PATH = "output/podcast_script.json"
    OUTPUT_DIR = "output"

    asyncio.run(synthesize_podcast(JSON_PATH, OUTPUT_DIR))
