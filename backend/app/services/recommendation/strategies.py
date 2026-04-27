from app.services.recommendation.base import BaseStrategy
from app.services.recommendation.scoring import ScoreContext


class ColdStartStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "cold-start"

    def compute_score(self, ctx: ScoreContext) -> float:
        return 0.35 * ctx.hot + 0.25 * ctx.fresh + 0.25 * ctx.content + 0.15 * ctx.completion

    def select_reason(self, ctx: ScoreContext) -> str:
        signals = {"全站热门推荐": ctx.hot, "新发布的播客": ctx.fresh, "完播率较高": ctx.completion}
        return max(signals.items(), key=lambda item: item[1])[0]


class WarmUpStrategy(BaseStrategy):
    def __init__(self, pos_count: int):
        self._hybrid_ratio = pos_count / 3.0
        self._cold_ratio = 1.0 - self._hybrid_ratio

    @property
    def name(self) -> str:
        return "warm-up"

    def compute_score(self, ctx: ScoreContext) -> float:
        cold = 0.35 * ctx.hot + 0.25 * ctx.fresh + 0.25 * ctx.content + 0.15 * ctx.completion
        hybrid = (
            0.35 * ctx.cf + 0.20 * ctx.content
            + 0.15 * ctx.hot + 0.10 * ctx.sequence + 0.10 * ctx.fresh + 0.10 * ctx.completion
        )
        return self._cold_ratio * cold + self._hybrid_ratio * hybrid

    def select_reason(self, ctx: ScoreContext) -> str:
        signals = {
            "全站热门推荐": ctx.hot,
            "新发布的播客": ctx.fresh,
            "与你历史喜好相似": ctx.cf,
            "完播率较高": ctx.completion,
        }
        return max(signals.items(), key=lambda item: item[1])[0]


class HybridStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "hybrid-v1"

    def compute_score(self, ctx: ScoreContext) -> float:
        return (
            0.35 * ctx.cf + 0.20 * ctx.content
            + 0.15 * ctx.hot + 0.10 * ctx.fresh
            + 0.10 * ctx.sequence + 0.10 * ctx.completion
        )

    def select_reason(self, ctx: ScoreContext) -> str:
        signals = {
            "与你历史喜好相似": ctx.cf,
            "与你常听内容主题一致": ctx.content,
            "近期全站热度较高": ctx.hot,
            "发布时间较新": ctx.fresh,
            "与你最近的收听序列相近": ctx.sequence,
            "完播率较高": ctx.completion,
        }
        return max(signals.items(), key=lambda item: item[1])[0]
