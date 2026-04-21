from app.services.episode_planner import load_topic_profiles
from app.core.config import settings


class TopicService:
    def list_topics(self) -> list[dict[str, str]]:
        profiles = load_topic_profiles(settings.topics_config_path)
        return [
            {
                "id": profile.id,
                "name": profile.name,
                "description": profile.description,
            }
            for profile in profiles.values()
        ]


topic_service = TopicService()
