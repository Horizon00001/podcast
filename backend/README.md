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

## 常见问题

### 依赖装不上

先确认已经激活虚拟环境，再执行：

```bash
cd /root/Projects/podcast/backend
source .venv/bin/activate
.venv/bin/pip install -r requirements.txt
```

如果仍然失败，优先检查 Python 版本和网络环境。

### `uvicorn` 启动失败

通常是以下原因之一：

- 没有激活 `backend/.venv`
- `backend/.env` 缺失或配置不完整
- 依赖没有安装完成

建议先执行：

```bash
cd /root/Projects/podcast/backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

### `pytest` 找不到模块

确认是在 `backend/` 目录下运行，并且使用的是 `backend/.venv/bin/python` 对应的环境。

### 读取不到配置

`backend/app/core/config.py` 会加载 `backend/.env`。如果配置改了但没生效，先检查文件是否存在、变量名是否拼写正确。

## 说明

- 默认数据库文件是 `backend/podcast.db`
- 前端地址默认是 `http://localhost:5173`
- 音频产物输出到仓库根目录的 `output/`
