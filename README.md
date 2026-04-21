# Podcast Prompt API

一个用于播客脚本生成、音频合成和任务管理的全栈项目。后端提供 FastAPI 接口和命令行流水线，前端提供 Web 管理界面。

## 项目组成

- `backend/`：FastAPI 后端、数据库模型、生成流水线、CLI、测试
- `frontend/`：Vite + React 管理界面
- `config/`：RSS 源和主题配置
- `output/`：生成产物目录，包含脚本、音频和中间结果
- `prompt.txt`：脚本生成提示词

## 功能

- RSS 源读取与筛选
- 主题驱动的节目选材与编排
- 基于大模型的播客脚本生成
- TTS 语音合成并输出音频文件
- 生成任务创建、状态查询和 SSE 日志流
- 播客、用户、交互和推荐相关接口

## 技术栈

- 后端：Python、FastAPI、SQLAlchemy、Pydantic
- 前端：React、TypeScript、Vite
- 数据库：SQLite，支持通过配置切换到 PostgreSQL
- 语音：DashScope CosyVoice 或 Edge TTS

## 环境要求

- Python 3.11+
- Node.js 18+
- npm
- `ffmpeg`

## 后端配置

后端配置由 `backend/app/core/config.py` 管理，默认从 `backend/.env` 读取。

常用配置项：

- `APP_NAME`：应用名称
- `APP_ENV`：运行环境
- `API_PREFIX`：接口前缀，默认 `/api/v1`
- `DATABASE_URL`：默认 SQLite 地址 `sqlite:///./podcast.db`
- `POSTGRES_URL`：可选 PostgreSQL 地址
- `CORS_ORIGINS`：前端地址，默认 `http://localhost:5173`
- `TTS_PROVIDER`：`dashscope` 或 `edge`
- `TTS_MODEL`：默认 `cosyvoice-v2`
- `DASHSCOPE_API_KEY`：DashScope API Key

说明：

- `Settings` 会优先读取当前工作目录下的 `.env`
- 从 `backend/` 启动服务时，默认数据库文件是 `backend/podcast.db`
- 音频静态目录是仓库根目录下的 `output/audio/`

## 启动方式

### 后端

从 `backend/` 目录启动：

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

服务启动后：

- 健康检查：`http://localhost:8000/health`
- OpenAPI 文档：`http://localhost:8000/docs`

### 前端

从 `frontend/` 目录启动：

```bash
cd frontend
npm install
npm run dev
```

默认地址：`http://localhost:5173`

## CLI

后端统一 CLI 入口在 `backend/app/cli/`，从 `backend/` 运行：

```bash
python -m app.cli --help
```

可用命令：

- `run-pipeline`：执行完整播客生成流水线
- `fetch-rss`：抓取 RSS 源并输出 `rss_data.json`
- `generate-text`：根据 RSS 和主题生成脚本
- `synthesize-tts`：将脚本 JSON 合成为音频

示例：

```bash
python -m app.cli fetch-rss
python -m app.cli generate-text --topic daily-news
python -m app.cli synthesize-tts --json-path output/podcast_script.json --output-dir output
python -m app.cli run-pipeline --topic daily-news
```

## 生成流程

完整流水线大致分为 4 步：

1. 读取 `config/feed.json`
2. 按主题选择素材并生成节目编排
3. 调用大模型生成结构化播客脚本
4. 调用 TTS 合成音频并保存到 `output/audio/`

生成结果通常会落在：

- `output/rss_data.json`
- `output/episode_plan.json`
- `output/podcast_script.json`
- `output/podcast_script.txt`
- `output/audio/podcast_full.mp3`

## API

### 生成任务

- `GET /api/v1/generation/sources`：获取启用的 RSS 源
- `GET /api/v1/generation/topics`：获取可选主题
- `POST /api/v1/generation/trigger`：创建生成任务
- `GET /api/v1/generation/{task_id}`：查询任务状态
- `GET /api/v1/generation/{task_id}/stream`：订阅任务日志 SSE

请求示例：

```json
{
  "rss_source": "espn-rpm",
  "topic": "daily-news"
}
```

### 其他资源

- `GET /api/v1/podcasts`
- `GET /api/v1/podcasts/{podcast_id}`
- `POST /api/v1/podcasts`
- `GET /api/v1/users`
- `GET /api/v1/interactions`
- `GET /api/v1/recommendations`

## 测试

### 后端

从 `backend/` 目录运行：

```bash
pytest
```

常用测试命令：

```bash
pytest tests/test_health.py
pytest tests/test_generation_routes.py
pytest tests/test_podcast_routes.py
pytest tests/test_recommendation_routes.py
pytest tests/test_tts_provider.py
```

### 前端

从 `frontend/` 目录运行：

```bash
npm run lint
npm run build
```

`npm run build` 会先执行 TypeScript 检查，再构建前端产物。

## 目录说明

```text
backend/
  app/
    api/v1/         FastAPI 路由
    cli/            命令行入口
    core/           配置
    db/             数据库初始化和迁移
    models/         ORM 模型
    pipelines/      生成流水线
    repositories/   数据访问层
    schemas/        Pydantic 模型
    services/       业务逻辑
  tests/            后端测试
frontend/
  src/              前端源码
config/
  feed.json         RSS 配置
  topics.json       主题配置
output/
  audio/            音频输出目录
```

## 注意事项

- 后端启动时会自动初始化数据库并执行迁移
- `output/` 下的生成文件通常不应手动提交
- 如果切换 TTS 服务提供方，需要同时检查 `.env` 和后端配置是否一致
