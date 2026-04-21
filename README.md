# 播客 Prompt 脚本生成系统

一个基于 AI 的自动化播客生成平台，支持从 RSS 新闻源自动抓取内容、智能生成播客对话脚本，并合成语音音频。

## 核心功能

- **RSS 新闻聚合** - 自动抓取多个 RSS 源，提取标题与摘要
- **AI 脚本生成** - 使用 pydantic-ai + DeepSeek 生成结构化播客对话脚本
- **TTS 语音合成** - 将脚本转换为自然语音音频
- **Web 管理界面** - React 前端，支持任务提交与状态查看

## 技术栈

**前端**
- React 18 + TypeScript
- Vite 构建工具
- React Router 路由管理

**后端**
- Python 3.11+ / FastAPI
- SQLAlchemy ORM + SQLite
- Pydantic 数据验证

**AI & 语音**
- pydantic-ai (Agent 框架)
- DeepSeek (语言模型)
- TTS API (语音合成)

## 项目结构

```
.
├─ backend/                     # FastAPI 后端
│  ├─ app/
│  │  ├─ api/v1/               # API 路由层
│  │  │  ├─ podcasts.py        # 播客相关接口
│  │  │  ├─ generation.py      # 生成任务接口
│  │  │  ├─ interactions.py    # 用户交互接口
│  │  │  └─ recommendations.py  # 推荐接口
│  │  ├─ services/             # 业务逻辑层
│  │  │  ├─ rss_service.py     # RSS 抓取服务
│  │  │  ├─ script_service.py   # 脚本生成服务
│  │  │  ├─ tts_service.py     # TTS 合成服务
│  │  │  └─ generation_service.py # 任务调度服务
│  │  ├─ models/               # 数据库模型
│  │  ├─ schemas/             # Pydantic DTO
│  │  └─ repositories/        # 数据访问层
│  └─ tests/                   # 单元测试
│
├─ frontend/                    # React 前端
│  ├─ src/
│  │  ├─ pages/               # 页面组件
│  │  │  ├─ GeneratePage.tsx   # 生成页面
│  │  │  ├─ PodcastListPage.tsx # 播客列表
│  │  │  └─ PodcastDetailPage.tsx # 播客详情
│  │  ├─ components/         # 通用组件
│  │  │  ├─ AudioPlayer.tsx   # 音频播放器
│  │  │  ├─ ScriptPanel.tsx   # 脚本面板
│  │  │  └─ TimelineHighlighter.tsx # 时间线高亮
│  │  └─ services/api.ts      # API 调用封装
│  └─ package.json
│
├─ config/                      # 配置文件
│  └─ feed.json                # RSS 源配置
│
├─ output/                      # 生成产物
│  ├─ rss_data.json           # RSS 原始数据
│  ├─ podcast_script.json     # 生成的脚本 JSON
│  ├─ podcast_script.txt      # 脚本文本
│  └─ audio/                  # 音频文件目录
│
├─ rss_fetch.py               # RSS 抓取脚本（独立可运行）
├─ generate_text.py           # 脚本生成脚本（独立可运行）
├─ tts_synthesize.py          # TTS 合成脚本（独立可运行）
├─ main.py                    # 完整流水线入口
└─ prompt.txt                 # AI 生成规则提示词
```

## 快速开始

### 1. 环境准备

确保已安装以下依赖：
- Python 3.11+
- Node.js 18+
- npm 或 yarn

### 2. 配置环境变量

复制环境变量模板文件：

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/macOS
cp .env.example .env
```

编辑 `.env` 文件，填入必要的 API Key：

```
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_API_BASE=https://api.deepseek.com
```

### 3. 配置 RSS 源

编辑 `config/feed.json`：

```json
{
  "feeds": [
    {
      "id": "tech-news",
      "name": "科技新闻",
      "url": "https://example.com/rss/tech.xml",
      "enabled": true,
      "category": "technology"
    }
  ]
}
```

### 4. 启动后端服务

```bash
cd backend

# 安装 Python 依赖（使用清华源）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 启动服务
uvicorn app.main:app --reload
```

后端启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 5. 启动前端服务

```bash
cd frontend

# 安装前端依赖
npm install

# 启动开发服务器
npm run dev
```

前端访问地址：http://localhost:5173

### 6. 一键运行完整流程

如需独立运行完整流水线（不启动 Web 服务）：

```bash
python main.py
```

## API 接口

### 生成任务

```bash
# 获取可选节目主题
GET /api/v1/generation/topics

# 触发生成任务
POST /api/v1/generation/trigger
Body: { "rss_source": "default", "topic": "daily-news" }

# 查询任务状态
GET /api/v1/generation/{task_id}
```

`topic` 现在表示节目主题模板，而不是普通字符串参数。后端会先按主题做选材和节目编排，再把编排结果交给脚本生成器。

### 播客管理

```bash
# 获取播客列表
GET /api/v1/podcasts

# 获取播客详情
GET /api/v1/podcasts/{podcast_id}

# 创建播客
POST /api/v1/podcasts
```

## 运行测试

```bash
cd backend
pytest
```

## 生成流程详解

### Step 1: RSS 抓取

调用 `rss_service.py` 或 `rss_fetch.py`：

1. 读取 `config/feed.json` 配置
2. 使用 feedparser 解析 RSS XML
3. 提取每条新闻的标题、链接、摘要
4. 仅保留标题和摘要（节省 token）
5. 输出到 `output/rss_data.json`

### Step 2: AI 脚本生成

调用 `script_service.py` 或 `generate_text.py`：

1. 根据 `topic` 从 RSS 数据中挑选合适素材
2. 生成 `episode_plan.json`，确定这一集的主线和段落结构
3. 加载 `prompt.txt` 中的生成规则
4. 使用 pydantic-ai Agent 基于节目计划生成脚本
5. Pydantic 模型保证输出格式：
    - title: 播客标题
    - intro: 简介
    - sections: 段落列表
      - section_type: opening/transition/main_content/closing
      - dialogues: A/B 对话轮次
      - audio_effect: 音效标注
    - total_duration: 预估时长
6. 流式输出，实时写入文件

### Step 3: TTS 语音合成

调用 `tts_service.py` 或 `tts_synthesize.py`：

1. 读取生成的脚本 JSON
2. 调用 TTS API 合成语音
3. 输出到 `output/audio/podcast_full.mp3`

## 输出文件说明

| 文件 | 说明 |
|------|------|
| `output/rss_data.json` | RSS 原始数据，包含多个新闻源的条目 |
| `output/podcast_script.json` | 结构化脚本数据，便于程序处理 |
| `output/podcast_script.txt` | 人类可读的脚本文本 |
| `output/audio/podcast_full.mp3` | 最终生成的语音音频 |

## 项目亮点

- **分层架构** - 前后端分离，后端采用标准的三层架构（API/Service/Repository）
- **类型安全** - 前端使用 TypeScript，后端使用 Pydantic，确保数据一致性
- **流式生成** - AI 脚本支持流式输出，实时查看生成进度
- **模块化设计** - 流水线各步骤独立，可单独运行或组合使用
- **配置驱动** - RSS 源、API Key 等通过配置文件管理，便于部署

## 文档

更多技术细节请参考：

- [接口契约](docs/api_contract.md)
- [团队模块分工](docs/team_modules.md)
- [部署指南](docs/deployment.md)

## License

MIT License
