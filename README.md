# Podcast Prompt API

一个用于播客脚本生成、音频合成和任务管理的全栈项目。后端提供 FastAPI 接口和 CLI 流水线，前端提供 Web 管理界面。

## 开源与协作

- 授权协议：Apache-2.0，见 `LICENSE`
- 贡献说明：见 `CONTRIBUTING.md`
- 安全报告：见 `SECURITY.md`
- 提交问题前，请先查看现有 issue，避免重复

## 项目组成

- `backend/`：FastAPI 后端、数据库模型、生成流水线、CLI、测试
- `frontend/`：Vite + React 管理界面
- `config/`：RSS 源和主题配置
- `output/`：生成产物目录，包含脚本、音频和中间结果
- `prompt.txt`：脚本生成提示词

## 功能

- RSS 源读取与筛选
- 主题驱动的节目选材与编排
- 基于 `pydantic-ai` 的播客脚本生成
- TTS 语音合成并输出音频文件
- 生成任务创建、状态查询、取消和 SSE 日志流
- 播客、用户、交互、点赞、收藏和推荐接口

## 技术栈

- 后端：Python、FastAPI、SQLAlchemy、Pydantic
- AI：`pydantic-ai` + DeepSeek 脚本模型
- 前端：React、TypeScript、Vite、React Router
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

- `Settings` 会优先读取 `backend/.env`
- 从 `backend/` 启动服务时，默认数据库文件是 `backend/podcast.db`
- 音频静态目录是仓库根目录下的 `output/audio/`
- 播客静态音频目录挂载在 `output/podcasts/`

## 启动方式

### 后端

从 `backend/` 目录启动：

```bash
cd /root/Projects/podcast/backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

服务启动后：

- 健康检查：`http://localhost:8000/health`
- OpenAPI 文档：`http://localhost:8000/docs`

### 前端

从 `frontend/` 目录启动：

```bash
cd /root/Projects/podcast/frontend
npm install
npm run dev
```

默认地址：`http://localhost:5173`

## CLI

后端统一 CLI 入口在 `backend/app/cli/`，从 `backend/` 运行：

```bash
cd /root/Projects/podcast/backend
source .venv/bin/activate
python -m app.cli --help
```

常用命令：

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
4. 调用 TTS 合成音频并保存到 `output/`

生成结果通常会落在：

- `output/rss_data.json`
- `output/episode_plan.json`
- `output/podcast_script.json`
- `output/podcast_script.txt`
- `output/audio/podcast_full.mp3`

## API

### 核心资源

- `GET /health`
- `GET /api/v1/podcasts`
- `GET /api/v1/podcasts/{podcast_id}`
- `GET /api/v1/podcasts/{podcast_id}/script`
- `POST /api/v1/podcasts`
- `GET /api/v1/users`
- `GET /api/v1/interactions`
- `GET /api/v1/recommendations/{user_id}`
- `POST /api/v1/recommendations/{user_id}/preferences`
- `GET /api/v1/favorites?user_id=...`
- `POST /api/v1/favorites`
- `DELETE /api/v1/favorites/{user_id}/{podcast_id}`
- `GET /api/v1/likes?user_id=...`
- `POST /api/v1/likes`
- `DELETE /api/v1/likes/{user_id}/{podcast_id}`

### 生成任务

- `GET /api/v1/generation/sources`
- `GET /api/v1/generation/topics`
- `GET /api/v1/generation/tts/providers`
- `GET /api/v1/generation/capabilities`
- `GET /api/v1/generation/provider-health`
- `POST /api/v1/generation/trigger`
- `GET /api/v1/generation/{task_id}`
- `GET /api/v1/generation/{task_id}/stream`
- `DELETE /api/v1/generation/{task_id}`

请求示例：

```json
{
  "rss_source": "default",
  "topic": "daily-news",
  "user_id": 1,
  "use_subscriptions": false,
  "custom_rss": []
}
```

## 测试

### 后端

从 `backend/` 目录运行：

```bash
pytest
```

常用测试命令：

```bash
pytest tests/test_health.py
pytest tests/test_db_migrations.py
pytest tests/test_interaction_routes.py
pytest tests/test_podcast_routes.py
pytest tests/test_recommendation_routes.py
pytest tests/test_tts_provider.py
```

### 前端

从 `frontend/` 目录运行：

```bash
npm run lint
npm run build
npm test
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
  src/
    components/     播放器、脚本面板、时间线等 UI 组件
    context/        状态管理
    pages/          列表、详情、生成、订阅、模型、设置、点赞、收藏页面
    router/         前端路由
    services/       API 客户端
    types/          TypeScript 类型定义
config/
  feed.json         RSS 配置
  topics.json       主题配置
output/
  audio/            音频输出目录
prompt.txt          剧本生成 prompt
assets/audio/       开场、转场、结尾等音频素材
```

## 注意事项

- 后端启动时会自动初始化数据库并执行迁移
- `output/` 下的生成文件通常不应手动提交
- 如果切换 TTS 服务提供方，需要同时检查 `.env` 和后端配置是否一致
- 音频素材按用途分目录，优先使用 `assets/audio/opening/`、`assets/audio/transition/`、`assets/audio/closing/`
