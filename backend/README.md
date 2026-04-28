# Backend Quick Start

这是 `backend/` 的快速使用说明。

## 环境

```bash
cd /root/Projects/podcast/backend
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -r requirements.txt
```

后端运行时会从 `backend/.env` 读取配置。

## 启动 API

```bash
cd /root/Projects/podcast/backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

- 健康检查：`http://localhost:8000/health`
- OpenAPI：`http://localhost:8000/docs`

## CLI

```bash
cd /root/Projects/podcast/backend
source .venv/bin/activate
python -m app.cli --help
python -m app.cli fetch-rss
python -m app.cli generate-text --topic daily-news
python -m app.cli synthesize-tts --json-path output/podcast_script.json --output-dir output
python -m app.cli run-pipeline --topic daily-news
```

## 测试

```bash
cd /root/Projects/podcast/backend
source .venv/bin/activate
pytest
pytest tests/test_health.py -v
pytest tests/test_generation_routes.py -v
pytest tests/test_podcast_routes.py -v
pytest tests/test_recommendation_routes.py -v
pytest tests/test_tts_provider.py -v
```

## 说明

- 默认数据库文件是 `backend/podcast.db`
- 前端地址默认是 `http://localhost:5173`
- 音频产物输出到仓库根目录的 `output/`
