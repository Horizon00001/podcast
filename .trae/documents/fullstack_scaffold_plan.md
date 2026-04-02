# 全栈项目脚手架搭建计划（FastAPI + React）

## 一、Summary

基于当前仓库已存在的播客生成主流程（`rss_fetch.py`、`generate_text.py`、`tts_synthesize.py`、`main.py`），本次将补齐“可协作开发的全栈脚手架”，目标是让组员按 WBS 直接在各自模块并行开发。

本计划将创建：
- 后端 FastAPI 分层骨架（可运行，占位接口 + DTO + 路由组织）
- 数据层基础（SQLite 开发即用，预留 PostgreSQL 切换）
- 前端 React（Vite + TypeScript + React Router）骨架
- 团队协作基线（README、环境变量模板、统一命令、接口契约模板、测试样例、.gitignore、LICENSE）
- 与现有脚本流水线的衔接层（将“脚本化产线”纳入新工程目录体系而不破坏原有逻辑）

## 二、Current State Analysis

### 1) 已有能力（可复用）
- 根目录已有可跑通的离线流水线：
  - `rss_fetch.py`：RSS 抓取并输出 `output/rss_data.json`
  - `generate_text.py`：基于 DeepSeek 生成播客脚本并落盘
  - `tts_synthesize.py`：TTS 语音合成与拼接
  - `main.py`：串联流程入口
- 已有配置与产物：
  - `config/feed.json`
  - `output/` 下已有示例 JSON/TXT/MP3 产物

### 2) 主要缺口（需要脚手架补齐）
- 缺少标准后端工程结构（API、service、repository、schema、config 分层）
- 缺少前端工程结构和接口调用基线
- 缺少统一依赖与启动方式（requirements、前端 package、环境变量示例）
- 缺少测试框架入口与协作文档（README、任务分工、接口规范）
- 缺少部署基线文件（Docker / compose 占位）

### 3) 已确认决策（来自你刚才的选择）
- 范围：全栈骨架
- 前端：Vite + TS + React Router
- 数据库：SQLite 开发 + PostgreSQL 预留
- 协作：完整协作基线
- Python 依赖：`requirements.txt`
- 后端深度：可运行占位 + DTO + 路由（不在本轮写重业务）

## 三、Proposed Changes（按文件/目录落地）

### A. 仓库结构重组（不删除现有脚本）
- 新增顶层目录：
  - `backend/`：FastAPI 服务代码
  - `frontend/`：React 前端代码
  - `common/`：跨端契约与示例（如 API schema、示例 JSON）
  - `docs/`：协作文档、WBS-目录映射、接口契约模板
  - `tests/`：后端测试入口（与 `backend/tests` 并存或二选一，最终统一到一处）
- 保留现有根目录脚本，新增 `legacy_pipeline/` 或在 README 标注其“历史入口/兼容入口”定位（本轮以文档标注优先，不强制迁移文件）。

### B. 后端脚手架（FastAPI）
- 计划新增：
  - `backend/app/main.py`：FastAPI 启动入口、健康检查、路由注册
  - `backend/app/api/v1/`：按 WBS 划分路由（podcasts、users、interactions、recommendations、generation）
  - `backend/app/schemas/`：Pydantic DTO（请求/响应模型）
  - `backend/app/services/`：业务占位服务
  - `backend/app/repositories/`：DAO 占位与接口抽象
  - `backend/app/models/`：SQLAlchemy 模型（Podcast/User/Interaction 等）
  - `backend/app/db/`：数据库连接、session 管理、初始化
  - `backend/app/core/config.py`：环境变量读取（SQLite 默认、Postgres 可切换）
- 行为目标：
  - 服务可启动
  - 文档页可见（OpenAPI）
  - 关键路由有可用占位返回，便于前端联调

### C. 前端脚手架（Vite + TS + Router）
- 计划新增：
  - `frontend/` 标准 Vite React TS 结构
  - `src/pages/`：列表页、详情页、生成页占位
  - `src/components/`：播放器、脚本区、高亮占位组件
  - `src/services/api.ts`：后端 API 调用封装
  - `src/router/`：路由配置
  - `src/types/`：与后端 DTO 对齐的类型定义
- 行为目标：
  - 前端可启动
  - 路由可访问
  - 能调用后端占位接口并展示基础数据

### D. 协作与规范基线
- 计划新增/补齐：
  - 根目录 `README.md`：项目说明、目录结构、启动步骤、分工建议
  - 根目录 `.gitignore`：Python/Node/IDE/产物忽略规则
  - 根目录 `.env.example`：后端/模型/TTS 所需变量模板
  - 根目录 `LICENSE`（默认 MIT）
  - `docs/api_contract.md`：接口契约与字段约定模板
  - `docs/team_modules.md`：WBS 任务与目录模块映射
  - `docs/deployment.md`：本地与演示环境部署说明（含 Docker 占位）

### E. 依赖与运行入口统一
- 计划新增：
  - `backend/requirements.txt`（或根 `requirements.txt`，最终选一种并统一）
  - `frontend/package.json`（由 Vite 初始化产生）
  - 根目录 `Makefile` 或 `scripts` 文档化命令（Windows 环境下以 README 命令为主）
- 注意：
  - Python 安装示例会遵循“清华源镜像”约定
  - 不在本轮引入复杂任务编排器，先保证组员能直接启动

### F. 测试脚手架
- 计划新增：
  - `backend/tests/test_health.py`：健康检查样例
  - `backend/tests/test_podcast_routes.py`：路由样例测试（占位）
  - 前端可选 `src/__tests__/` 或先在 README 标注测试规划入口（按复杂度落地）
- 行为目标：
  - 至少后端测试可执行，保证 CI 本地基础通过

### G. 与现有流水线集成策略
- 在后端 `generation` 路由中预留触发接口（先占位）：
  - 后续可调用现有 `main.py` 或拆分调用 `rss_fetch.py/generate_text.py/tts_synthesize.py`
- 在 `common/examples/` 放置脚本 JSON 示例，确保前端“脚本同步高亮”模块有稳定输入。

## 四、Assumptions & Decisions

- 决策：本轮重点是“工程化脚手架”，不是完整业务实现；复杂算法（推荐模型训练、音频优化）只留模块与接口占位。
- 决策：默认单仓（monorepo）组织，便于课程项目协作与统一提交。
- 决策：后端先以 SQLite 快速落地，配置层预留 PostgreSQL。
- 决策：前后端以 REST + JSON 交互，接口先满足联调稳定性。
- 假设：当前成员开发环境允许 Python + Node 并存；若后续发现限制，再补充最小化替代方案。

## 五、Verification Steps

实施后将按以下步骤验证：
- 结构验证：目录与关键文件是否与计划一致。
- 后端验证：
  - 安装依赖后可启动 FastAPI
  - `/health` 与核心占位路由返回正常
  - OpenAPI 文档可访问
- 前端验证：
  - 安装依赖后可启动 Vite
  - 路由页面可访问
  - API 封装能请求后端占位接口并显示结果
- 测试验证：
  - 后端样例测试可运行通过
- 文档验证：
  - 新成员按 README 可完成“拉仓库→安装依赖→启动前后端→访问页面”的流程

## 六、执行顺序（实施阶段将按此顺序）

1. 建立目录骨架与基础配置文件  
2. 落地后端 FastAPI 可运行最小系统（分层 + 路由 + DTO + DB 配置）  
3. 落地前端 Vite React TS Router 最小系统（页面 + API 封装）  
4. 打通前后端最小联调链路  
5. 补齐测试样例与协作文档  
6. 进行一次完整本地验收并修正脚手架细节  

