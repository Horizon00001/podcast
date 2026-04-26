import re

import jieba


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")
CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fff]+")
DOMAIN_WORDS = (
    "人工智能",
    "机器学习",
    "深度学习",
    "大模型",
    "生成式AI",
    "生成式人工智能",
)


for word in DOMAIN_WORDS:
    jieba.add_word(word)


def tokenize_text(text: str) -> list[str]:
    tokens: list[str] = []
    for chunk in TOKEN_PATTERN.findall(text or ""):
        if CHINESE_PATTERN.fullmatch(chunk):
            tokens.extend(token.lower() for token in jieba.lcut(chunk) if token.strip())
            continue
        tokens.append(chunk.lower())
    return tokens


def spaced_tokens(text: str) -> str:
    return f" {' '.join(tokenize_text(text))} "
