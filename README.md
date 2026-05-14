# AddrSplitCheckFill

中文地址拆分、批量处理和规则校验系统。项目采用前后端分离架构：后端使用 FastAPI 提供地址解析、Excel 处理、任务进度、校验规则、记录管理和环境配置接口；前端使用 Vue 3、TypeScript 和 Vite 提供可视化操作界面。

## 功能概览

- 地址拆分：支持 Excel 上传和手动输入地址。
- 输出模式：支持 8 级地址、11 级地址和 MGeo 原始字段输出。
- MGeo 模型解析：使用本地 MGeo 模型进行中文地址要素识别。
- Excel 预检查：上传前识别表头、地址列、总行数和可处理行数。
- 自定义校验规则：支持新增、编辑、删除和 Excel 批量导入正则规则。
- 规则命中结果：输出 `new_validation_status` 和 `new_violated_rule_ids`。
- 任务进度：支持 WebSocket 进度推送、阶段展示、耗时统计和任务取消。
- 记录管理：支持查看拆分记录、分页查看结果、下载结果文件和删除记录。
- 环境配置：支持 Redis 本地或远程连接参数维护和连接测试。

## 项目结构

```text
AddrSplitCheckFill/
  address_back/          # FastAPI 后端服务
    app/                 # API、配置、模型服务、任务和数据处理逻辑
    data/                # 运行时数据目录，数据库、上传文件和结果文件不提交
    iic/                 # MGeo 模型文件，使用 Git LFS 管理
    scripts/             # 辅助脚本
    main.py              # 后端启动入口
    pyproject.toml       # 后端依赖配置
    uv.lock              # 后端锁定依赖
  address_web/           # Vue 3 + TypeScript + Vite 前端应用
    public/              # 静态资源
    src/                 # 页面、组件、接口、路由和样式
    package.json         # 前端依赖和脚本
  .gitattributes         # Git LFS 规则
  README.md              # 项目说明
```

## 环境要求

- Python 3.11 或更高版本
- uv
- Node.js 18 或更高版本
- npm
- Git LFS
- Redis，可选但推荐，默认连接 `127.0.0.1:6379/0`
- CUDA 11.8，可选；当前后端锁文件使用 PyTorch CUDA 11.8 版本

## 拉取代码

```bash
git clone git@github.com:eqeqeqr/AddrSplitCheckFill.git
cd AddrSplitCheckFill
git lfs install
git lfs pull
```

`address_back/iic/` 下的 `*.bin` 和 `*.tar` 模型文件由 Git LFS 管理。未完整拉取 LFS 文件时，首次执行地址解析可能会出现模型文件缺失或加载失败。

## 后端安装与启动

安装依赖：

```bash
cd address_back
uv sync
```

启动服务：

```bash
uv run python main.py
```

默认地址：

```text
后端服务：http://127.0.0.1:8008
健康检查：http://127.0.0.1:8008/api/health
接口文档：http://127.0.0.1:8008/docs
```

后端依赖包含 FastAPI、uvicorn、pandas、openpyxl、redis、modelscope、transformers、datasets、PyTorch CUDA 11.8 相关包等。若目标机器没有 NVIDIA GPU 或 CUDA 11.8 环境，需要按部署环境调整 `address_back/pyproject.toml` 中的 PyTorch 版本和源。

## 前端安装与启动

安装依赖：

```bash
cd address_web
npm install
```

启动开发服务：

```bash
npm run dev
```

默认地址：

```text
前端服务：http://127.0.0.1:5178
默认接口：http://127.0.0.1:8008/api
```

如需修改接口地址，可在 `address_web/.env.local` 中配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8008/api
```

## 常用命令

后端启动：

```bash
cd address_back
uv run python main.py
```

前端开发：

```bash
cd address_web
npm run dev
```

前端构建：

```bash
cd address_web
npm run build
```

前端预览：

```bash
cd address_web
npm run preview
```

## 数据、模型与本地文件

- `address_back/iic/`：MGeo 模型目录，使用 Git LFS 管理。
- `address_back/data/address.db`：SQLite 运行数据库，本地生成，不建议提交。
- `address_back/data/uploads/`：上传文件目录，本地生成，不建议提交。
- `address_back/data/results/`：拆分结果目录，本地生成，不建议提交。
- `address_back/*.log`、`address_web/*.log`：开发服务日志，不建议提交。
- `address_back/.venv/`、`address_web/node_modules/`、`address_web/dist/`：依赖和构建产物，不建议提交。
- `address_web/.env`、`address_web/.env.local`：本地环境配置，不建议提交。

## Redis 配置

默认 Redis 地址：

```text
redis://127.0.0.1:6379/0
```

可在前端“环境配置”页面切换本地或远程 Redis，并进行连接测试。没有可用 Redis 时，部分缓存、任务状态或分布式能力可能受影响。

## 校验规则导入

自定义校验规则支持 Excel 批量导入，模板前三列表头需要为：

```text
规则ID | 正则表达式 | 校验层级
```

校验层级支持 `level_1` 到 `level_11`。拆分后会根据规则输出：

```text
new_validation_status      # 通过、未通过、未校验
new_violated_rule_ids      # 命中的规则 ID
```

MGeo 原始字段输出模式不参与自定义规则校验。

## 基本使用流程

1. 拉取代码并执行 `git lfs pull` 获取模型文件。
2. 进入 `address_back`，执行 `uv sync` 安装后端依赖。
3. 执行 `uv run python main.py` 启动后端服务。
4. 进入 `address_web`，执行 `npm install` 安装前端依赖。
5. 执行 `npm run dev` 启动前端服务。
6. 打开 `http://127.0.0.1:5178`。
7. 上传 Excel 或手动输入地址，选择输出模式和校验规则。
8. 执行拆分，查看进度、结果详情或下载结果文件。
