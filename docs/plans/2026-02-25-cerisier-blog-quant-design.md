# Cerisier - Personal Blog & A-Share Quantitative System Design

> Date: 2026-02-25
> Status: Approved

## 1. Project Overview

A personal blog platform with an integrated A-share quantitative stock-picking system.

**Two core subsystems:**
- **Blog System**: Public-facing blog with categories, tags, archives, comments, and a sci-fi/data-viz dark theme
- **Quant System**: Admin-only quantitative analysis platform with 11-dimension stock analysis, multi-factor scoring, AI-powered reports, and paper trading simulator

**Development strategy:** Parallel development. Shared infrastructure first, then both systems built concurrently.

## 2. Tech Stack

### Frontend (Vue 3 Ecosystem)
- **Core:** Vue 3 + Vite + Pinia + Vue Router
- **UI:** Element Plus (admin) + Tailwind CSS (public blog)
- **Charts:** Apache ECharts (K-line/indicators) + DataV (sci-fi decorations)
- **Effects:** tsparticles (particle background) + oh-my-live2d (Live2D) + APlayer (music)
- **Editors:** Vditor (Markdown) + TinyMCE (rich text)
- **HTTP:** axios

### Backend (Django 5.2 Ecosystem)
- **API:** Django REST Framework (DRF) + djangorestframework-simplejwt
- **Async/Scheduling:** Celery + Redis
- **AI:** OpenAI SDK (DeepSeek for bulk, ChatGPT for premium reports)
- **Data Sources:** AKShare (primary) + Tushare (supplementary), unified abstraction layer

### Data
- **PostgreSQL** with **TimescaleDB** extension (hypertables for time-series K-line data)
- **Redis:** Cache + Celery broker

### Deployment
- **Production:** Docker + Docker Compose + Nginx on VPS (2C/2.5G RAM Ubuntu)
- **Development:** Local Docker Compose

## 3. Architecture

### 3.1 Deployment Architecture (Plan A: Single-machine Containerized)

```
VPS (2C / 2.5G RAM)
+-- Nginx (reverse proxy + static files)         ~50MB
+-- Django + Gunicorn (2 workers)                 ~200MB
+-- Celery Worker (solo pool, 1 worker)           ~150MB
+-- Celery Beat (scheduler)                       ~80MB
+-- PostgreSQL + TimescaleDB                      ~300MB
+-- Redis (cache + broker)                        ~50MB
+-- Vue frontend (compiled, served by Nginx)      ~0MB runtime
                                            Total ~830MB
```

Resource constraints (production):

| Service | Memory Limit | CPU Limit |
|---------|-------------|-----------|
| PostgreSQL | 400MB | 0.5 |
| Django | 300MB | 0.5 |
| Celery Worker | 200MB | 0.5 |
| Celery Beat | 100MB | 0.1 |
| Redis | 64MB | 0.1 |
| Nginx | 50MB | 0.1 |

Optimization: PostgreSQL shared_buffers=256MB, work_mem=4MB. 2GB swap. Celery solo pool. Heavy analysis runs post-market close (17:00).

### 3.2 Repository Structure (Monorepo)

```
cerisier/
+-- frontend/                    # Vue 3 frontend
|   +-- src/
|   |   +-- views/
|   |   |   +-- blog/            # Public blog pages
|   |   |   +-- admin/           # Admin pages (blog + quant)
|   |   +-- components/
|   |   |   +-- common/          # Shared components
|   |   |   +-- blog/            # Blog-specific components
|   |   |   +-- quant/           # Quant-specific components
|   |   +-- stores/              # Pinia stores
|   |   +-- router/              # Vue Router
|   |   +-- api/                 # API request layer (axios)
|   |   +-- styles/              # Tailwind + global styles
|   |   +-- utils/
|   +-- public/
|   +-- vite.config.ts
|   +-- tailwind.config.js
|   +-- package.json
|
+-- backend/                     # Django 5.2 backend
|   +-- config/                  # Django project config
|   |   +-- settings/
|   |   |   +-- base.py
|   |   |   +-- dev.py
|   |   |   +-- prod.py
|   |   +-- urls.py
|   |   +-- celery.py
|   |   +-- wsgi.py
|   +-- apps/
|   |   +-- blog/                # Blog module
|   |   +-- users/               # User/comment module
|   |   +-- quant/               # Quant module
|   |       +-- datasources/     # Data source abstraction
|   |       +-- analyzers/       # 11 dimension analyzers
|   |       +-- scorers/         # Multi-factor scoring
|   |       +-- ai/              # AI integration
|   |       +-- signals/         # Trade signal generation
|   |       +-- simulator/       # Paper trading
|   +-- requirements/
|   |   +-- base.txt
|   |   +-- dev.txt
|   |   +-- prod.txt
|   +-- manage.py
|
+-- docker/                      # Docker configs
|   +-- nginx/
|   +-- django/
|   +-- postgres/
+-- docker-compose.yml           # Development
+-- docker-compose.prod.yml      # Production
+-- .env.example
```

## 4. Blog System Design

### 4.1 Data Models

**User** (extends Django Auth):
- username, email, avatar, bio
- role: admin / visitor
- oauth_provider (optional: GitHub login)

**Category**:
- name, slug, description
- parent (self-referencing, multi-level)
- sort_order

**Tag**:
- name, slug, color

**Post**:
- title, slug, content (HTML + raw Markdown stored)
- excerpt, cover_image
- category (FK), tags (M2M)
- status: draft / published / archived
- is_pinned, view_count, like_count
- created_at, updated_at, published_at
- author (FK -> User)

**Comment**:
- post (FK -> Post)
- user (FK -> User, nullable for anonymous)
- nickname, email (for anonymous comments)
- content
- parent (self-referencing, nested comments)
- is_approved (moderation)
- created_at

**FriendLink**: name, url, description, logo
**SiteConfig**: singleton, site name/description/logo/social links

### 4.2 Blog Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Home | `/` | Sci-fi design, article waterfall + DataV decorations, particle background |
| Post List | `/posts` | Paginated, filter by category/tag |
| Post Detail | `/post/:slug` | Markdown render + code highlight + comment section |
| Categories | `/categories` | Category tree display |
| Tag Cloud | `/tags` | Tag cloud visualization |
| Archives | `/archives` | Timeline by year/month |
| About | `/about` | Personal intro page |

### 4.3 Blog Admin Pages (Element Plus)

| Page | Features |
|------|----------|
| Dashboard | Article stats, traffic trends (ECharts), recent comments |
| Post Management | CRUD, Markdown/rich-text toggle editor, image upload |
| Category/Tag Management | CRUD |
| Comment Management | Approve/reply/delete |
| Site Settings | Site name, description, logo, social links |

### 4.4 Frontend Effects

- **tsparticles**: Homepage dynamic particle background, dark sci-fi theme
- **oh-my-live2d**: Bottom-right Live2D character, interactive
- **APlayer + MetingJS**: Floating music player at bottom, BGM playlist
- **DataV**: Sci-fi border decorations on homepage title area and quant section entry

### 4.5 Editor Solution

- **Markdown:** Vditor (WYSIWYG + instant render + split preview, built-in code highlight and math)
- **Rich Text:** TinyMCE via @tinymce/tinymce-vue
- Toggle between modes during editing

## 5. Quantitative System Design

### 5.1 Data Layer (datasources/)

**Unified data source abstraction:**

```
DataSourceBase (ABC)
+-- fetch_kline(stock_code, period, start, end) -> DataFrame
+-- fetch_money_flow(stock_code) -> DataFrame
+-- fetch_news(stock_code) -> list[dict]
+-- fetch_financial_report(stock_code) -> DataFrame
+-- fetch_margin_data(stock_code) -> DataFrame
+-- fetch_stock_list() -> DataFrame

AKShareSource(DataSourceBase)   # Primary source
TushareSource(DataSourceBase)   # Supplementary source
DataSourceRouter                # Auto-select available source, failover
```

**TimescaleDB Models (hypertables):**

- **StockBasic**: code, name, industry, sector, list_date, market
- **KlineData** (hypertable): stock_code, datetime, OHLCV, amount, turnover. Partitioned by datetime, auto-compress >7 days.
- **MoneyFlow** (hypertable): stock_code, datetime, main_net, huge_net, big_net, mid_net, small_net
- **MarginData** (hypertable): stock_code, datetime, margin fields
- **FinancialReport**: stock_code, period, PE/PB/ROE/revenue/profit metrics
- **NewsArticle**: stock_code, title, content, source, sentiment_score, published_at

**Celery Scheduled Tasks:**

| Task | Frequency | Time |
|------|-----------|------|
| Update daily K-line | Daily | 16:00 |
| Update money flow | Daily | 16:30 |
| Update financial reports | Quarterly | Post-reporting season |
| Update news/announcements | Hourly | 09:00-18:00 |
| Data cleaning/validation | Daily | 02:00 |
| Run analysis pipeline | Daily | 17:00 |

### 5.2 Analysis Layer (analyzers/)

11 modular analyzers, each producing independent scores and explanations:

```
AnalyzerBase (ABC)
+-- analyze(stock_code) -> AnalysisResult
    +-- score: float (0-100)
    +-- signals: list[Signal]       # BUY/SELL/HOLD
    +-- explanation: str            # Text explanation
    +-- confidence: float (0-1)     # Confidence level

Concrete analyzers:
 1. TechnicalAnalyzer       # MA/MACD/KDJ/BOLL/RSI/Volume
 2. NewsAnalyzer            # AI-powered news/announcement sentiment
 3. FundamentalAnalyzer     # PE/PB/ROE/revenue growth/gross margin
 4. MoneyFlowAnalyzer       # Main/retail fund flow, DDX/DDY/DDZ
 5. ChipAnalyzer            # Cost distribution, concentration, profit ratio
 6. SentimentAnalyzer       # Advance/decline ratio, limit-up boards, turnover anomaly
 7. SectorRotationAnalyzer  # Sector rotation, industry prosperity
 8. GameTheoryAnalyzer      # Institutional/retail game theory model
 9. BehaviorFinanceAnalyzer # Herding effect, overreaction indicators
10. MacroAnalyzer           # M2, interest rates, FX, PMI
11. AIAnalyzer              # DeepSeek/ChatGPT comprehensive analysis
```

### 5.3 Multi-Factor Scoring & Signal Generation (scorers/ + signals/)

**MultiFactorScorer:**
- Input: 11 AnalysisResult objects
- Dynamic weights by trading style:

| Dimension | Ultra-short | Swing | Mid-long |
|-----------|------------|-------|----------|
| Technical | 30% | 20% | 10% |
| Money Flow | 25% | 20% | 15% |
| Chip | 20% | 15% | 5% |
| Sentiment | 15% | 5% | 5% |
| News | 10% | 15% | 5% |
| Fundamental | 0% | 15% | 25% |
| Macro | 0% | 0% | 20% |
| Sector Rotation | 0% | 0% | 15% |
| AI | 0% | 15% | 15% |
| Game Theory | 0% | 5% | 0% |
| Behavior Finance | 0% | 0% | 5% |

- Output: Composite score + ranking

**SignalGenerator:**
- Input: Composite score + individual analyzer signals
- Output:
  - action: BUY / SELL / HOLD
  - entry_price: Suggested entry price
  - stop_loss: Based on trading style (ultra-short: -3%~-5%, swing: -5%~-8%, mid-long: -8%~-15%)
  - take_profit: Multi-level take-profit targets
  - position_size: Suggested position percentage
  - reason: Selection rationale with per-dimension analysis summary

### 5.4 AI Integration (ai/)

```
AIService
+-- analyze_news(news_list) -> sentiment + summary
+-- analyze_financial(report) -> insights
+-- generate_report(stock, all_results) -> str
+-- score_factors(stock, context) -> dict
+-- provider: "deepseek" / "chatgpt" (switchable)
```

Strategy: DeepSeek for bulk analysis (cost-effective), ChatGPT for premium reports (higher quality). Daily API call budget cap.

### 5.5 Paper Trading Simulator (simulator/)

- **Portfolio**: cash, total_value, created_at
- **Position**: stock_code, quantity, avg_cost, current_price
- **Trade**: stock_code, action, price, quantity, datetime, reason
- **PerformanceMetric**: daily_return, cumulative_return, max_drawdown, sharpe_ratio, win_rate

### 5.6 Quant Admin Pages (Element Plus + ECharts)

| Page | Features |
|------|----------|
| Quant Dashboard | Today's picks, portfolio P&L, market overview |
| Stock Picks | By style (ultra-short/swing/mid-long), scores, signals, reasons |
| Stock Analysis | 11-dimension radar chart + K-line + detailed analysis panels |
| K-line Workbench | ECharts candlestick + MACD/KDJ/BOLL overlay + DataV decorations |
| Simulator | Positions, trade history, equity curve, performance metrics |
| AI Reports | Browse AI-generated analysis reports |
| System Config | Data source config, factor weights, API key management, task monitoring |

## 6. API Design

### 6.1 Blog Public API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/posts/` | GET | Post list (paginated, filterable) |
| `/api/posts/:slug/` | GET | Post detail |
| `/api/categories/` | GET | Category list (tree) |
| `/api/tags/` | GET | Tag list |
| `/api/archives/` | GET | Archive timeline |
| `/api/posts/:slug/comments/` | GET/POST | Comments list / submit comment |
| `/api/site-config/` | GET | Site configuration |

### 6.2 Blog Admin API (auth required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/posts/` | CRUD | Post management |
| `/api/admin/categories/` | CRUD | Category management |
| `/api/admin/tags/` | CRUD | Tag management |
| `/api/admin/comments/` | CRUD | Comment moderation |
| `/api/admin/upload/` | POST | Image/file upload |
| `/api/admin/dashboard/` | GET | Dashboard stats |

### 6.3 Quant API (admin auth required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/quant/recommendations/` | GET | Today's picks (filterable by style) |
| `/api/quant/stocks/:code/analysis/` | GET | Multi-dimension analysis |
| `/api/quant/stocks/:code/kline/` | GET | K-line data (period param) |
| `/api/quant/stocks/:code/report/` | GET | AI analysis report |
| `/api/quant/simulator/portfolio/` | GET | Paper portfolio |
| `/api/quant/simulator/trades/` | GET/POST | Trade history / execute paper trade |
| `/api/quant/simulator/performance/` | GET | Performance metrics |
| `/api/quant/config/weights/` | GET/PUT | Factor weight config |
| `/api/quant/tasks/` | GET | Celery task monitor |

### 6.4 Authentication

- **Admin:** JWT (djangorestframework-simplejwt)
- **Visitor comments:** No registration, nickname + email, moderated before display
- Frontend: axios interceptor for unified token management

## 7. Frontend Route Architecture

```
/                               # Blog public (Tailwind sci-fi theme)
+-- /posts                      # Post list
+-- /post/:slug                 # Post detail
+-- /categories                 # Categories
+-- /tags                       # Tags
+-- /archives                   # Archives
+-- /about                      # About

/admin                          # Admin (Element Plus)
+-- /admin/dashboard            # Dashboard
+-- /admin/posts                # Post management
+-- /admin/comments             # Comment management
+-- /admin/quant                # Quant system
|   +-- /admin/quant/dashboard  # Quant dashboard
|   +-- /admin/quant/picks      # Stock picks
|   +-- /admin/quant/stock/:code # Stock analysis
|   +-- /admin/quant/kline/:code # K-line workbench
|   +-- /admin/quant/simulator  # Paper trading
|   +-- /admin/quant/reports    # AI reports
|   +-- /admin/quant/settings   # System config
+-- /admin/settings             # Site settings
```
