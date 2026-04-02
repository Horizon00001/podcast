from app.schemas.recommendation import RecommendationItem, RecommendationResponse


class RecommendationService:
    def hot_recommendations(self, user_id: int) -> RecommendationResponse:
        return RecommendationResponse(
            user_id=user_id,
            strategy="hot",
            items=[
                RecommendationItem(podcast_id=1, score=0.95, reason="按热度兜底推荐"),
                RecommendationItem(podcast_id=2, score=0.89, reason="近期播放量较高"),
            ],
        )
