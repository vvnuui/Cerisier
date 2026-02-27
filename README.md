# Cerisier

个人博客 + A股量化选股系统，基于 Django 5.2 和 Vue 3 构建。

## 技术栈

### 后端
- **Django 5.2** + Django REST Framework
- **PostgreSQL 16**（TimescaleDB 时序扩展）
- **Redis 7** + **Celery 5.4**（异步任务队列 + Beat 定时调度）
- **SimpleJWT** 认证
- **AKShare** / **Tushare** A股数据源（故障切换路由）
- **OpenAI** / **DeepSeek** AI 分析服务

### 前端
- **Vue 3**（Composition API）+ **TypeScript 5.9**
- **Vite 7** 构建工具
- **Element Plus** UI 组件库
- **ECharts 6** 图表（K线、雷达图、折线图等）
- **Pinia** 状态管理 + **Vue Router**
- **Tailwind CSS** 暗色科幻主题

### 基础设施
- **Docker** 多阶段构建 + **Docker Compose**（开发 / 生产）
- **Nginx** 反向代理 + Let's Encrypt SSL
- **GitHub Actions** CI/CD（lint → test → build）

## 功能模块

### 博客系统
- 文章 CRUD、分类、标签、归档
- 评论系统、友链、站点配置
- Markdown 编辑器（Vditor）
- 后台仪表盘（统计卡片、趋势图）

### 量化选股系统
- **数据采集**：股票基本信息、K线、资金流、财报、新闻
- **8 大分析器**：技术面、基本面、资金流、筹码、情绪面、板块、实验性、AI
- **多因子打分**：风格自适应权重（超短、波段、中长线）
- **信号生成**：ATR 止损止盈 + 仓位管理
- **模拟交易**：组合管理、买卖执行、绩效追踪
- **AI 报告**：DeepSeek / ChatGPT 双引擎智能分析
- **K线工作台**：蜡烛图 + MA / BOLL / MACD / KDJ / RSI 技术指标

## 项目结构

```
cerisier/
├── backend/
│   ├── apps/
│   │   ├── blog/              # 博客模块
│   │   ├── quant/             # 量化模块
│   │   │   ├── ai/            #   AI 分析服务
│   │   │   ├── analyzers/     #   8 大分析器 + 打分器 + 信号生成
│   │   │   ├── datasources/   #   数据源（AKShare / Tushare）
│   │   │   └── simulator/     #   模拟交易引擎
│   │   └── users/             # 用户认证
│   ├── config/                # Django 配置（base / dev / prod）
│   └── requirements/          # 依赖（base / dev / prod）
├── frontend/
│   ├── src/
│   │   ├── api/               # 类型化 API 客户端
│   │   ├── components/        # 可复用组件
│   │   ├── layouts/           # 布局（博客 / 后台）
│   │   ├── stores/            # Pinia 状态管理
│   │   └── views/             # 页面视图
├── docker/                    # Dockerfile（Django / Nginx）
├── scripts/                   # 部署 / 备份脚本
├── docker-compose.yml         # 开发环境
└── docker-compose.prod.yml    # 生产环境
```

## 快速开始

### 环境要求
- Python 3.12+
- Node.js 20+
- PostgreSQL 16（推荐 TimescaleDB）
- Redis 7

### 1. 克隆项目

```bash
git clone https://github.com/vvnuui/Cerisier.git
cd Cerisier
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际配置
```

### 3. Docker 方式启动（推荐）

```bash
docker-compose up -d
```

服务启动后：
- 后端 API：http://localhost:8000
- 前端页面：http://localhost:5173

### 4. 本地开发

**后端：**

```bash
cd backend
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py runserver
```

**前端：**

```bash
cd frontend
npm install
npm run dev
```

### 5. 运行测试

```bash
# 后端测试（407 个用例）
cd backend && python -m pytest apps/ -q

# 前端类型检查
cd frontend && npx vue-tsc --noEmit
```

## 生产部署

```bash
# 使用部署脚本
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# 或手动启动
docker-compose -f docker-compose.prod.yml up -d
```

## CI/CD

GitHub Actions 自动运行三个阶段：

| 阶段 | 内容 |
|------|------|
| **Lint** | ruff（Python）+ vue-tsc（TypeScript） |
| **Test** | pytest 407 个测试用例 |
| **Build** | 前端构建 + Docker 镜像构建 |

## 许可证

MIT
