# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI 播客生成系统：抓取 RSS → 分类聚类 → 生成剧本 → TTS 合成音频。

- **Backend**: FastAPI + SQLAlchemy + Pydantic v2，API 版本化部署于 `/api/v1`
- **Frontend**: React 19 + TypeScript + Vite + React Router 7
- **AI**: pydantic-ai + DeepSeek（`openai:deepseek-chat`）生成剧本，读取 `prompt.txt` 作为 system prompt
- **TTS**: DashScope cosyvoice-v2（主要）+ Edge TTS（备用），通过 `SpeechProvider` 协议抽象
- **Database**: SQLite（开发）+ 可选 PostgreSQL（生产），启动时自动建表 + 执行迁移

## 架构模式

Routes → Services → Repositories（三层架构）

```
HTTP Request → FastAPI Route → Service → Repository → SQLAlchemy Session → SQLite/PostgreSQL
```

`app/db/session.py` 定义了 `get_db()` 依赖注入，路由层使用 `Depends(get_db)` 获取 session。

## 常用命令

```bash
# Backend - 必须使用 backend venv 中的 Python
cd /home/default/Projects/podcast/backend && source .venv/bin/activate
uvicorn app.main:app --reload          # 开发服务器 (端口 8000)
pytest                                  # 运行所有测试
pytest tests/test_health.py -v         # 单个测试文件（详细输出）

# Frontend
cd /home/default/Projects/podcast/frontend
npm install                              # 安装依赖
npm run dev                              # 开发服务器 (localhost:5173)
npm run lint && npm run build           # 检查 + TypeScript 编译 + 构建
npm test                                 # vitest 前端测试

# Standalone 管道（无需 Web UI）
cd /home/default/Projects/podcast/backend && python -m app.cli run-pipeline
# 分步执行：
python -m app.cli fetch-rss
python -m app.cli generate-text
python -m app.cli synthesize-tts
```

## 目录结构

```
backend/
  app/
    api/v1/           FastAPI 路由（podcasts, users, interactions, recommendations, generation）
    cli/              命令行入口（子命令：run-pipeline, fetch-rss, generate-text, synthesize-tts）
    core/             Settings 配置类（从 .env 读取）
    db/               数据库初始化（create_all）和迁移（ALTER TABLE 补列）
    models/           SQLAlchemy ORM 模型
    pipelines/        4 步流水线：RSS → 聚类编排 → 剧本生成 → TTS 合成
    repositories/     数据访问层（每个 model 对应一个 repository）
    schemas/          Pydantic 请求/响应模型
    services/         业务逻辑层（含推荐算法、TTS 抽象、剧本生成）
  tests/              后端 pytest 测试
frontend/
  src/
    components/       全局播放器、脚本面板、时间线高亮
    context/          UserProvider, PlayerProvider, FavoritesProvider
    pages/            播客列表、详情、生成、订阅、设置、收藏
    services/api.ts   API 客户端（fetch 封装）
    router/           路由配置
    types/            TypeScript 类型定义
output/               生成的脚本和音频（git-ignored）
  rss_data.json       原始 RSS 抓取结果
  podcasts/           按分类/分组的播客脚本和音频
config/
  feed.json           RSS 源配置
  topics.json         话题定义
prompt.txt            AI 播客剧本 system prompt
```

## 关键约定

### Python Runtime
- **必须使用**: `backend/.venv/bin/python`
- 系统 conda 和 pip 缺少 `pydantic_ai`、`dashscope` 等依赖
- venv 二进制: `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/uvicorn`
- `requirements.txt` 落后于实际安装：`dashscope` 装的是 `1.25.17` 但列表中是 `1.24.2`；`mutagen` 和 `imageio_ffmpeg` 未列在 requirements 中

### 数据库
- SQLite 默认: `sqlite:///./podcast.db`（相对于 cwd）
- 从 `backend/` 运行时数据库在 `backend/podcast.db`
- 启动时调用 `bootstrap_database()` → `initialize_schema()`（create_all）+ `apply_migrations()`（ALTER TABLE 补列）
- 迁移脚本 `app/db/migrations.py`：以幂等方式补充列（category, preferences, interactions 扩展字段, generation_tasks 表）

### 静态文件
- 音频文件: `/audio` 路径映射到 `output/audio/`（repo 根目录）

### 配置文件
- `config/feed.json` - RSS 源配置（前端通过 `/api/v1/generation/sources` 读取）
- `config/topics.json` - 话题定义
- `prompt.txt` - AI 生成规则（pydantic-ai 读取为 system prompt）
- `.env` - 环境变量（DashScope API key 等）

### 注意事项
- `README.md` 部分描述与当前代码不完全一致（README 中 API 列表过时）
- `frontend/README.md` 是 Vite 默认模板，非项目指导
- `output/` 下的生成文件已 git-ignored
- `package-lock.json` 同时在根目录和 `frontend/` 存在，但只有 `frontend/package.json` 定义了实际脚本
- API keys 暴露需轮换

## 数据库模型

### User (`backend/app/models/user.py`)
- `id`: Integer, PK
- `username`: String(64), unique
- `email`: String(128), unique
- `preferences`: Text, nullable（JSON 格式，存储用户偏好分类）
- `created_at`: DateTime

### Podcast (`backend/app/models/podcast.py`)
- `id`: Integer, PK
- `title`: String(200)
- `summary`: Text
- `category`: String(64), default="general"
- `audio_url`: String(500)
- `script_path`: String(500)
- `published_at`: DateTime

### Interaction (`backend/app/models/interaction.py`)
- `id`: Integer, PK
- `user_id`: FK → users.id
- `podcast_id`: FK → podcasts.id
- `action`: String(32) — "play", "pause", "resume", "like", "favorite", "skip", "complete"
- `listen_duration_ms`: Integer, nullable
- `progress_pct`: Float, nullable
- `session_id`: String(64), nullable
- `context_hour`: Integer, nullable
- `context_weekday`: Integer, nullable
- `context_bucket`: String(32), nullable
- `recommendation_request_id`: String(64), nullable
- `created_at`: DateTime

### GenerationTask (`backend/app/models/generation_task.py`)
- `task_id`: String(64), PK
- `status`: String(32) — "queued", "running", "succeeded", "failed", "cancelled"
- `message`: Text
- `rss_source`: String(128)
- `topic`: String(128)
- `logs`: Text（JSON 字符串数组，SSE 流式输出）
- `created_at`: DateTime
- `updated_at`: DateTime

## 前端架构

### Context Providers

**UserContext** (`frontend/src/context/UserContext.tsx`)
- 管理用户身份：自动 get-or-create 用户
- `ensureUser(username)` 模式，存储在 localStorage

**PlayerContext** (`frontend/src/context/PlayerContext.tsx`)
- 管理全局音频播放状态：`currentPodcast`, `isPlaying`, `progress`, `duration`, `currentTime`, `playbackRate`
- 使用 HTMLAudioElement + useRef 实现

**FavoritesContext** (`frontend/src/context/FavoritesContext.tsx`)
- 管理收藏状态，与后端 interaction API 同步

### 核心组件

**GlobalPlayer** (`frontend/src/components/GlobalPlayer.tsx`)
- 固定底部播放条（90px）
- 显示播客标题/摘要、播放控制、进度条、播放速率
- 使用 PlayerContext 的音频状态

**TimelineHighlighter** (`frontend/src/components/TimelineHighlighter.tsx`)
- 脚本时间线同步高亮
- 根据 `currentTime` 定位当前行并自动滚动
- 点击任意行跳转播放

### API 客户端 (`frontend/src/services/api.ts`)

Base URL: `VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'`
媒体 URL 去掉 `/api/v1` 前缀（从 MEDIA_BASE_URL 拼接）

关键方法:
- `listPodcasts()`, `getPodcast(id)` - 播客 CRUD
- `getRecommendations(userId)` - 个性化推荐
- `setPreferences(userId, categories)` - 设置用户偏好分类
- `reportInteraction(payload)` - 上报交互（含播放时长、进度、上下文时段）
- `ensureUser(username)` - get-or-create（先 GET 再 POST）
- `getRSSSources()`, `getTopics()` - 生成配置
- `triggerGeneration(payload)` - 触发生成，返回 `{task_id, status}`
- `getGenerationStatus(taskId)` - 轮询状态
- `createEventSource(taskId)` - SSE 实时日志流
- `cancelGeneration(taskId)` - 取消生成任务（DELETE）
- `getPodcastScript(id)` - 获取脚本时间线（带时间戳）

### 测试

Frontend 使用 vitest + @testing-library/react：
```bash
# 前端测试
cd frontend && npm test          # vitest run
npm run test:watch               # watch 模式
```

测试文件在 `frontend/src/components/__tests__/`, `frontend/src/context/__tests__/`, `frontend/src/services/__tests__/`

## Generation API（生成任务 API）

- `GET  /generation/sources` — 获取启用 RSS 源列表
- `GET  /generation/topics` — 获取可选主题
- `POST /generation/trigger` — 创建任务（BackgroundTasks 异步执行）
- `GET  /generation/{task_id}` — 查询任务状态+日志
- `GET  /generation/{task_id}/stream` — SSE 流（每 0.5s 推送新日志）
- `DELETE /generation/{task_id}` — 取消任务（设置 status=cancelled，pipeline 定期检查）

BackgroundTasks 调用 `generation_service.run_task()`，内部 `asyncio.run(run_pipeline(...))`。不支持 FastAPI 生命周期内的真正后台 await，因此使用了 `asyncio.run()` 套 shell。

## Pipeline 管道

4 步流水线（`backend/app/pipelines/podcast_pipeline.py`）：

### Step 1: RSS Fetch
- 读取 `config/feed.json`
- 抓取所有 `enabled: true` 的 RSS 源
- 输出 `output/rss_data.json`

### Step 2: Episode Planning（分类 + 聚类）
- 读取 `output/rss_data.json`
- **分类**：基于关键词分类（tech_ai, business, sports, general）
- **聚类**：TF-IDF + 余弦相似度 + 并查集（阈值 0.5）
- 按 anchor 正则分组
- **Pending Groups**：不足 2 条的聚类存入 `pending_groups.json`，跨运行合并
- 输出 per-group `episode_plan.json` 到 `output/podcasts/<category>/<slug>/`

### Step 3: Script Generation
- 使用 pydantic-ai Agent + `openai:deepseek-chat`
- 流式输出 `PodcastScript`（见下方模型定义）
- 支持 `on_section_ready` 回调 → 每个 section 生成后立即触发 TTS 合成（流式 pipeline）
- 输出 `podcast_script.txt`（纯文本）和 `podcast_script.json`

**PodcastScript 模型**（`backend/app/schemas/script.py`）:
```
PodcastScript          — 含标题、简介、段落列表、总时长
├── sections: List[PodcastSection]
└── 验证：必须同时包含 A/B 两位说话者

PodcastSection         — opening/transition/main_content/closing
├── dialogues: List[DialogueTurn]
├── audio_effect: Optional[AudioEffect]
└── 验证：至少 2 句对话，A/B 严格交替

DialogueTurn           — speaker: "A" | "B", content, emotion（可选）
```

### Step 4: TTS Synthesis
- 调用 `TTSService.synthesize_podcast()` 或 `synthesize_section()`（逐段合成）
- 每段合成后异步合并 → `output/podcasts/<category>/<slug>/audio/podcast_full.mp3`
- 需要外部 `ffmpeg` 合并音频片段

## TTS 抽象

`SpeechProvider` 协议（`backend/app/services/speech_provider.py`）:
```python
async def synthesize(text, output_path, voice, style) -> Path: ...
```

- **DashScopeTTSProvider**: Alibaba cosyvoice-v2（主要），通过 WebSocket API 合成
- **EdgeTTSProvider**: Microsoft Edge TTS（备用），支持多语音 fallback
- `create_speech_provider()` 读取 `TTS_PROVIDER` 环境变量

Voice 映射:
- `voice="male"` → `loongdavid_v2`
- `voice="female"` 或 unset → `longanwen`

## 推荐算法

`RecommendationService` 混合推荐（`backend/app/services/recommendation_service.py`）：

核心策略基于用户正交互数量自动切换：
- **n=0** → `cold-start`：40% hot + 30% fresh + 30% content
- **n=1-2** → `warm-up`：线性混合 cold + hybrid
- **n≥3** → `hybrid-v1`：40% CF + 25% content + 15% hot + 10% sequence + 10% fresh

高级特性：
- **分时推荐**：按 morning/afternoon/evening/night 时段构建用户画像，当前时段正交互 ≥3 时优先使用时段画像
- **序列评分**：基于最近 5 个正交互的 TF-IDF 加权（recency × importance）与候选播客计算余弦相似度
- **冷启动偏好**：新用户可通过 `POST /recommendations/{user_id}/preferences` 设置偏好分类标签
- **负反馈**：skip 行为加权（进度 ≤10% 时 -3.0），被 skip 的播客不进入候选

交互权重：
- `favorite`: 5.0, `like`: 3.0, `complete`: 3.0, `play`: 1.0, `resume`: 0.5, `skip`: -2.0

## 测试说明

### Backend 测试

`backend/tests/conftest.py` 提供 `db_session` fixture：
- 使用 `sqlite:///:memory:` + `StaticPool`
- 每次测试创建独立 schema，结束时 `drop_all` 清理
- 需导入 models 注册到 Base metadata

常用测试文件：
```
tests/test_health.py              — 健康检查路由
tests/test_generation_routes.py   — 生成任务 API
tests/test_podcast_routes.py      — 播客 CRUD API
tests/test_recommendation_routes.py — 推荐 API
tests/test_tts_provider.py        — TTS provider 抽象层
tests/services/                   — service 层单元测试
tests/integration/                — 流水线集成测试
```

### Frontend 测试

使用 vitest，在 `frontend/` 目录运行 `npm test`。测试文件用 `.test.tsx` 后缀，`frontend/src/test/setup.ts` 配置 jsdom 环境。

## 脚本时间线

`PodcastService.get_podcast_script()` 从 `podcast_script.json` 解析出带时间戳的 `ScriptLineResponse`：
- speaker = "host" (A) / "guest" (B)
- startTime/endTime 根据字符数估算：`ESTIMATED_CHARS_PER_SECOND = 4.0`
- 最短时长 500ms
