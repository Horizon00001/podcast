from abc import ABC, abstractmethod

from app.services.recommendation.scoring import ScoreContext


class BaseStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy identifier (e.g. 'cold-start', 'hybrid-v1')."""
        ...

    @abstractmethod
    def compute_score(self, ctx: ScoreContext) -> float:
        """Blend sub-scores into a single final score."""
        ...

    @abstractmethod
    def select_reason(self, ctx: ScoreContext) -> str:
        """Pick the dominant signal as a human-readable reason label."""
        ...
