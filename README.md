# AddrSplitCheckFill

中文地址拆分、校验与 AI 补全系统。前后端分离架构：后端 FastAPI + MGeo 本地 NER 模型 + LLM Agent；前端 Vue 3 + TypeScript + Vite。

## 功能概览

- **地址拆分**：Excel 上传或手动输入，MGeo 模型自动识别地址要素，支持 8 级、11 级、MGeo 原始字段三种输出模式。
- **地址补全**：基于 LLM Agent 的智能补全，自动填充缺失的省级、市级等地址层级，支持 DeepSeek、智谱、通义千问等 12+ 国产大模型。
- **规则校验**：自定义正则表达式校验规则，支持 Excel 批量导入，按层级输出校验结果和命中的规则 ID。
- **实时进度**：WebSocket 推送任务进度、处理步骤和状态变更，支持断线重连自动恢复。
- **记录管理**：拆分记录和补全记录的查询、分页浏览、Excel 下载和删除。
- **环境配置**：Redis 多配置管理（本地/远程）、LLM 模型多配置管理（多厂商切换）。
- **一键打包**：PyInstaller 打包为单个 exe，双击即用，无需安装 Python 或 Node.js。

## 项目结构

```text
AI_address_judgment/
  address_back/                    # FastAPI 后端
    app/
      api/routes.py                # 全部 API 端点
      core/config.py               # 路径、常量、环境变量
      schemas/                     # Pydantic 数据模型
        address.py                 # 拆分、校验、Redis、模型配置模型
        address_fill.py            # 补全工作流模型
      services/
        constants.py               # 字段定义（RAW_FIELDS、LEVEL8、LEVEL11）
        db.py                      # SQLite 数据库初始化与连接
        model_service.py           # MGeo NER 模型单例封装
        split_service.py           # 核心拆分逻辑（Excel/文本 -> 地址解析）
        validation_rule_service.py # 校验规则 CRUD + 正则校验
        address_fill_service.py    # 补全任务编排
        address_fill_agent.py      # LLM Agent 地址补全
        agent_prompt.md            # LLM Agent 系统提示词
        bing_search.py             # Bing 网页搜索模块
        document_parsers.py        # 多格式文档解析（DOCX/PDF/Excel/TXT/CSV）
        job_store.py               # 双后端任务存储（Redis + SQLite）
        redis_store.py             # Redis 操作封装
        progress_ws.py             # WebSocket 进度广播
        task_control.py            # 任务取消控制
        environment_config.py      # Redis 配置管理
        model_config.py            # LLM 模型配置管理
    mgeo_geographic_elements_tagging_chinese_base.py   # MGeo 地址要素识别封装
    main.py                        # 后端启动入口
    AddressSplitTool.spec          # PyInstaller 打包配置
    pyproject.toml                 # Python 依赖
    iic/                           # MGeo 模型文件（Git LFS）
    data/                          # 运行时数据（自动生成）
  address_web/                     # Vue 3 前端
    src/
      views/
        SplitView.vue              # 地址拆分页面
        AddressFillView.vue        # 地址补全页面
        AddressFillRecordsView.vue # 补全记录页面
        RecordsView.vue            # 拆分记录页面
        ResultDetailView.vue       # 拆分结果详情页面
        ValidationRulesView.vue    # 校验规则管理页面
        EnvironmentView.vue        # 环境配置页面（Redis + 模型）
      api/address.ts               # API 客户端
      router/index.ts              # 路由配置
      components/                  # 公共组件
    package.json                   # 前端依赖
  AddressSplitTool.spec            # PyInstaller 打包配置（根目录副本）
  README.md
```

## 环境要求

### 开发环境

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | >= 3.11 | 后端运行 |
| uv | 最新 | Python 依赖管理 |
| Node.js | >= 18 | 前端构建 |
| npm | 随 Node.js | 前端包管理 |
| Git LFS | 最新 | 拉取模型文件 |
| Redis | 可选 | 任务缓存（默认 `127.0.0.1:6379/0`） |

### 打包环境

无需额外工具，`uv sync` 会自动安装 PyInstaller 和 CPU 版 PyTorch。

## 快速开始

### 1. 拉取代码

```bash
git clone git@github.com:eqeqeqr/AddrSplitCheckFill.git
cd AddrSplitCheckFill
git lfs install
git lfs pull
```

### 2. 后端安装与启动

```bash
cd address_back
uv sync
uv run python main.py
```

启动后自动打开浏览器访问 `http://127.0.0.1:8008`。

### 3. 前端安装与启动（开发模式）

```bash
cd address_web
npm install
npm run dev
```

访问 `http://127.0.0.1:5178`，后端接口地址可通过 `address_web/.env` 配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8008/api
```

## 页面说明

### 地址拆分（`/split`）

支持两种输入方式：

1. **Excel 上传**：上传包含地址列的 Excel 文件，自动检测地址列、识别表头、统计行数。
2. **手动输入**：直接输入地址文本（每行一条）。

选择输出模式后执行拆分，实时查看进度和结果预览。

输出模式：

| 模式 | 说明 | 字段数 |
|------|------|--------|
| 8 级地址 | 省 -> 市 -> 区 -> 镇 -> 街道/社区 -> 路/POI -> 门牌号 -> 详情 | 8 |
| 11 级地址 | 在 8 级基础上增加单元号、楼层号、房间号 | 11 |
| MGeo 原始 | 保留 MGeo 模型的全部 21 个字段 | 21 |

### 地址补全（`/address-fill`）

基于 LLM Agent 的智能地址补全。选择拆分结果或上传 Excel，Agent 自动分析缺失的地址层级并填充。

处理步骤（每条地址 4 步）：

1. **层级分析**：识别已有层级和缺失层级
2. **目标设定**：确定需要补全的目标层级
3. **推理过程**：基于上下文和参考文档进行推理（含子步骤）
4. **结果生成**：输出补全结果

支持上传参考文档（DOCX/PDF/Excel/TXT/CSV），Agent 会结合文档内容辅助推理。

### 校验规则（`/validation-rules`）

自定义正则表达式校验规则，拆分后自动执行校验。

导入模板（Excel）：

```text
规则ID | 正则表达式 | 校验层级
```

校验层级支持 `level_1` 到 `level_11`。拆分结果输出：

- `new_validation_status`：通过、未通过、未校验
- `new_violated_rule_ids`：命中的规则 ID

### 环境配置（`/environment`）

**Redis 配置**：支持多配置管理（名称、地址、端口、密码），可切换本地/远程，支持连接测试和断开。

**模型配置**：支持多厂商 LLM 配置（DeepSeek、智谱、通义千问、月之暗面、百川等），配置 API 地址、密钥、模型名称，支持连接测试和切换。

## 后端 API

所有端点前缀 `/api`。

### 拆分接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/splits` | 从 Excel 创建拆分任务 |
| POST | `/splits/text` | 从文本创建拆分任务 |
| GET | `/splits` | 查询拆分记录列表 |
| GET | `/splits/{job_id}` | 查询拆分任务详情 |
| GET | `/splits/{job_id}/result` | 分页查询拆分结果 |
| GET | `/splits/{job_id}/download` | 下载拆分结果 Excel |
| POST | `/splits/{job_id}/cancel` | 取消拆分任务 |
| DELETE | `/splits/{job_id}` | 删除拆分记录 |
| POST | `/excels/inspect` | 预检查 Excel 文件 |
| WS | `/ws/splits/{job_id}` | 拆分进度 WebSocket |

### 补全接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/address-fill/jobs` | 创建补全任务 |
| GET | `/address-fill/jobs` | 查询补全记录列表 |
| GET | `/address-fill/jobs/{job_id}/result` | 分页查询补全结果 |
| GET | `/address-fill/jobs/{job_id}/download` | 下载补全结果 Excel |
| GET | `/address-fill/jobs/{job_id}/events` | 查询补全工作流事件 |
| GET | `/address-fill/jobs/{job_id}/row-states` | 查询逐行处理状态 |
| POST | `/address-fill/jobs/{job_id}/cancel` | 取消补全任务 |
| DELETE | `/address-fill/jobs/{job_id}` | 删除补全记录 |
| POST | `/address-fill/inputs/inspect` | 预检查补全输入文件 |
| GET | `/address-fill/split-results` | 查询可补全的拆分结果 |
| WS | `/ws/address-fill/{job_id}` | 补全进度 WebSocket |

### 校验规则接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/validation-rules` | 查询规则列表 |
| POST | `/validation-rules` | 创建规则 |
| PUT | `/validation-rules/{rule_id}` | 更新规则 |
| DELETE | `/validation-rules/{rule_id}` | 删除规则 |
| POST | `/validation-rules/import` | Excel 批量导入规则 |

### 环境配置接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/environment/redis/configs` | Redis 配置列表 |
| POST | `/environment/redis/configs` | 创建/更新 Redis 配置 |
| DELETE | `/environment/redis/configs/{id}` | 删除 Redis 配置 |
| POST | `/environment/redis/configs/{id}/activate` | 激活 Redis 配置 |
| POST | `/environment/redis/test` | 测试 Redis 连接 |
| POST | `/environment/redis/disconnect` | 断开 Redis |
| GET | `/environment/redis/status` | Redis 连接状态 |
| GET | `/environment/models` | 模型配置列表 |
| POST | `/environment/models` | 创建/更新模型配置 |
| DELETE | `/environment/models/{id}` | 删除模型配置 |
| POST | `/environment/models/{id}/activate` | 激活模型配置 |
| POST | `/environment/models/test` | 测试模型连接 |

## 打包为 Windows 可执行文件

使用 PyInstaller 将后端、前端和 MGeo 模型打包为单个 exe，双击即用。

### 前置步骤

构建前端并复制到后端 static 目录：

```bash
cd address_web
npm install
npm run build
rm -rf ../address_back/static
cp -r dist ../address_back/static
```

### 打包命令

```bash
cd address_back
uv sync
rm -rf build/
uv run pyinstaller AddressSplitTool.spec --noconfirm
```

产物位于 `address_back/dist/AddressSplitTool.exe`。

### 分发

将 `AddressSplitTool.exe` 复制到目标 Windows 机器即可运行。首次启动后自动创建 `data/` 目录（数据库、上传文件、结果文件）。

### 打包原理

- 入口：`main.py` 启动 FastAPI + uvicorn，监听 `127.0.0.1:8008`。
- 前端：构建后的 SPA 静态文件通过 FastAPI 挂载提供，支持前端路由。
- 模型：MGeo 模型文件（`iic/`）和 ModelScope AST 索引文件打包在 exe 内部，运行时解压到临时目录。
- 模块收集：使用 `collect_submodules('modelscope')` 收集全部 ModelScope 子模块，确保动态导入不遗漏。
- 运行时依赖：CPU 版 PyTorch，无需 GPU 即可在任意 Windows 机器运行。

### 打包配置文件说明

`AddressSplitTool.spec` 关键配置：

- `datas`：打包静态文件（`static/`）、MGeo 模型（`iic/`）、ModelScope AST 索引
- `hiddenimports`：显式声明动态导入的模块（uvicorn、fastapi、app 子模块等）
- `collect_submodules('modelscope')`：自动收集所有 ModelScope 子模块
- `excludes`：排除 nvidia、cuda 等不需要的包

## 数据文件说明

| 路径 | 说明 | 是否提交 |
|------|------|----------|
| `address_back/iic/` | MGeo 模型文件 | Git LFS |
| `address_back/data/address.db` | SQLite 数据库 | 否（自动生成） |
| `address_back/data/uploads/` | 上传文件 | 否（自动生成） |
| `address_back/data/results/` | 拆分结果文件 | 否（自动生成） |
| `address_back/static/` | 构建后的前端文件 | 否（需手动同步） |
| `address_back/dist/` | PyInstaller 打包产物 | 否 |
| `address_back/build/` | PyInstaller 中间文件 | 否 |
| `address_web/node_modules/` | 前端依赖 | 否 |
| `address_web/dist/` | 前端构建产物 | 否 |

## Redis 配置

默认连接 `redis://127.0.0.1:6379/0`。

Redis 为可选依赖。启用时用于任务状态存储和缓存；未启用时自动降级为 SQLite 存储，功能不受影响。可在前端「环境配置」页面管理多个 Redis 配置并切换。

## 技术栈

### 后端

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI + uvicorn |
| 数据处理 | pandas + openpyxl |
| NER 模型 | ModelScope + MGeo（CPU 模式） |
| LLM 接口 | OpenAI-compatible API |
| 数据库 | SQLite（内置） |
| 缓存 | Redis（可选） |
| 打包 | PyInstaller |

### 前端

| 组件 | 技术 |
|------|------|
| 框架 | Vue 3 + TypeScript |
| 构建 | Vite |
| 路由 | vue-router |
| 图标 | lucide-vue-next |
| 样式 | 自定义 CSS（无 UI 框架） |

## 常用命令

```bash
# 后端启动
cd address_back && uv run python main.py

# 前端开发
cd address_web && npm run dev

# 前端构建
cd address_web && npm run build

# 前端预览
cd address_web && npm run preview

# 打包 exe
cd address_web && npm run build && cp -r dist ../address_back/static
cd address_back && rm -rf build/ && uv run pyinstaller AddressSplitTool.spec --noconfirm
```
