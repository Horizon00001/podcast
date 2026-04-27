from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    username: str
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Invalid email")
        return value


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomRSSSource(BaseModel):
    id: str
    name: str
    url: str
    category: str = "general"
    enabled: bool = True


class SubscriptionPreferences(BaseModel):
    categories: list[str] = []
    rss_sources: list[str] = []
    custom_rss: list[CustomRSSSource] = []
    frequency: Literal["manual", "daily", "weekly"] = "manual"


class GenerationPreferences(BaseModel):
    topic: str = "daily-news"
    max_items: int = 4
    use_subscriptions: bool = True
    script_provider: str = "pydantic_ai"
    script_llm_model: str = "openai:deepseek-v4-flash"
    script_llm_base_url: str = ""


class PlaybackSettings(BaseModel):
    voice: Literal["male", "female"] = "female"
    language: Literal["zh", "en"] = "zh"
    auto_cover: bool = False
    console_mode: Literal["compact", "verbose"] = "compact"
    tts_provider: Literal["dashscope", "edge"] = "dashscope"
    tts_model: str = "cosyvoice-v2"
    tts_male_provider: Literal["dashscope", "edge"] = "dashscope"
    tts_male_model: str = "cosyvoice-v2"
    tts_male_voice: str = "loongdavid_v2"
    tts_female_provider: Literal["dashscope", "edge"] = "dashscope"
    tts_female_model: str = "cosyvoice-v2"
    tts_female_voice: str = "longanwen"


class ModelConfig(BaseModel):
    provider: str = ""
    model: str = ""
    base_url: str = ""
    api_key: str = ""


class ModelsPreferences(BaseModel):
    script: ModelConfig = ModelConfig()
    speech: ModelConfig = ModelConfig()
    embedding: ModelConfig = ModelConfig()


class UserPreferences(BaseModel):
    subscription: SubscriptionPreferences = SubscriptionPreferences()
    generation: GenerationPreferences = GenerationPreferences()
    settings: PlaybackSettings = PlaybackSettings()
    models: ModelsPreferences = ModelsPreferences()
