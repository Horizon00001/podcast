from __future__ import annotations

import json
import sys

from sentence_transformers import SentenceTransformer


def main() -> int:
    payload = json.load(sys.stdin)
    model_name = payload["model"]
    device = payload.get("device", "cpu")
    texts = payload.get("texts", [])

    model = SentenceTransformer(model_name, device=device)
    vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    json.dump({"vectors": [vector.tolist() for vector in vectors]}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
