from app.services.recommendation.base import BaseStrategy
from app.services.recommendation.strategies import (
    ColdStartStrategy,
    HybridStrategy,
    WarmUpStrategy,
)


class StrategyFactory:
    _cold_start = ColdStartStrategy()
    _hybrid = HybridStrategy()

    @staticmethod
    def get_strategy(pos_count: int) -> BaseStrategy:
        if pos_count == 0:
            return StrategyFactory._cold_start
        if pos_count <= 2:
            return WarmUpStrategy(pos_count)
        return StrategyFactory._hybrid
