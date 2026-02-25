# Cerisier Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a personal blog with integrated A-share quantitative stock-picking system.

**Architecture:** Monorepo with Vue 3 frontend and Django 5.2 backend, containerized with Docker Compose. Blog uses Tailwind CSS sci-fi theme (public) + Element Plus (admin). Quant system uses ECharts for K-line charts, 11-dimension analyzers with multi-factor scoring, AI-powered analysis via DeepSeek/ChatGPT, and paper trading simulator.

**Tech Stack:** Vue 3, Vite, Pinia, Vue Router, Tailwind CSS, Element Plus, ECharts, DataV, Django 5.2, DRF, Celery, Redis, PostgreSQL + TimescaleDB, Docker

**Design Doc:** `docs/plans/2026-02-25-cerisier-blog-quant-design.md`

---

## Phase 0: Project Scaffolding & Docker Infrastructure

### Task 0.1: Create .gitignore and .env.example

**Files:**
- Create: `.gitignore`
- Create: `.env.example`

**Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
*.egg

# Django
*.log
db.sqlite3
media/
staticfiles/

# Node
node_modules/
dist/
.vite/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
docker/postgres/data/

# OS
.DS_Store
Thumbs.db
```

**Step 2: Create .env.example**

```env
# Django
DJANGO_SECRET_KEY=change-me-to-a-random-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_DB=cerisier
POSTGRES_USER=cerisier
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/1

# AI API Keys
OPENAI_API_KEY=
DEEPSEEK_API_KEY=

# Tushare (optional)
TUSHARE_TOKEN=
```

**Step 3: Commit**

```bash
git add .gitignore .env.example
git commit -m "chore: add .gitignore and .env.example"
```

### Task 0.2: Create Docker infrastructure

**Files:**
- Create: `docker/django/Dockerfile`
- Create: `docker/nginx/Dockerfile`
- Create: `docker/nginx/nginx.conf`
- Create: `docker/nginx/default.conf`
- Create: `docker-compose.yml`
- Create: `docker-compose.prod.yml`

**Step 1: Create Django Dockerfile**

```dockerfile
# docker/django/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements/base.txt requirements/base.txt
COPY backend/requirements/dev.txt requirements/dev.txt
RUN pip install --no-cache-dir -r requirements/dev.txt

COPY backend/ .

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
```

**Step 2: Create Nginx configs**

```dockerfile
# docker/nginx/Dockerfile
FROM nginx:alpine
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
```

```nginx
# docker/nginx/nginx.conf
worker_processes auto;
events { worker_connections 1024; }
http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 10M;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    include /etc/nginx/conf.d/*.conf;
}
```

```nginx
# docker/nginx/default.conf
upstream django {
    server django:8000;
}

server {
    listen 80;
    server_name localhost;

    location /api/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin-django/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
    }

    location /media/ {
        alias /var/www/media/;
    }

    location / {
        root /var/www/frontend;
        try_files $uri $uri/ /index.html;
    }
}
```

**Step 3: Create docker-compose.yml (development)**

```yaml
# docker-compose.yml
services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-cerisier}
      POSTGRES_USER: ${POSTGRES_USER:-cerisier}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-devpassword}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  django:
    build:
      context: .
      dockerfile: docker/django/Dockerfile
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres
      - redis

  celery:
    build:
      context: .
      dockerfile: docker/django/Dockerfile
    command: celery -A config worker -l info --pool=solo
    volumes:
      - ./backend:/app
    env_file: .env
    depends_on:
      - postgres
      - redis

  celery-beat:
    build:
      context: .
      dockerfile: docker/django/Dockerfile
    command: celery -A config beat -l info
    volumes:
      - ./backend:/app
    env_file: .env
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

**Step 4: Create docker-compose.prod.yml**

```yaml
# docker-compose.prod.yml
services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          memory: 400M
          cpus: "0.5"
    command: >
      postgres
        -c shared_buffers=256MB
        -c work_mem=4MB
        -c effective_cache_size=512MB
        -c max_connections=50

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 50mb --maxmemory-policy allkeys-lru
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: "0.1"

  django:
    build:
      context: .
      dockerfile: docker/django/Dockerfile
    env_file: .env
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          memory: 300M
          cpus: "0.5"

  celery:
    build:
      context: .
      dockerfile: docker/django/Dockerfile
    command: celery -A config worker -l info --pool=solo -c 1
    env_file: .env
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          memory: 200M
          cpus: "0.5"

  celery-beat:
    build:
      context: .
      dockerfile: docker/django/Dockerfile
    command: celery -A config beat -l info
    env_file: .env
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          memory: 100M
          cpus: "0.1"

  nginx:
    build:
      context: .
      dockerfile: docker/nginx/Dockerfile
    ports:
      - "80:80"
    volumes:
      - frontend_dist:/var/www/frontend
      - media_files:/var/www/media
    depends_on:
      - django
    deploy:
      resources:
        limits:
          memory: 50M
          cpus: "0.1"

volumes:
  postgres_data:
  frontend_dist:
  media_files:
```

**Step 5: Commit**

```bash
git add docker/ docker-compose.yml docker-compose.prod.yml
git commit -m "infra: add Docker Compose setup with TimescaleDB, Redis, Nginx"
```

### Task 0.3: Scaffold Django backend

**Files:**
- Create: `backend/requirements/base.txt`
- Create: `backend/requirements/dev.txt`
- Create: `backend/requirements/prod.txt`
- Create: `backend/manage.py`
- Create: `backend/config/__init__.py`
- Create: `backend/config/settings/__init__.py`
- Create: `backend/config/settings/base.py`
- Create: `backend/config/settings/dev.py`
- Create: `backend/config/settings/prod.py`
- Create: `backend/config/urls.py`
- Create: `backend/config/wsgi.py`
- Create: `backend/config/celery.py`

**Step 1: Create requirements files**

```
# backend/requirements/base.txt
Django==5.2
djangorestframework==3.15.2
djangorestframework-simplejwt==5.4.0
django-cors-headers==4.6.0
django-filter==24.3
psycopg[binary]==3.2.4
celery==5.4.0
redis==5.2.1
gunicorn==23.0.0
Pillow==11.1.0
python-decouple==3.8
akshare==1.15.59
openai==1.60.0
pandas==2.2.3
numpy==2.2.2
```

```
# backend/requirements/dev.txt
-r base.txt
pytest==8.3.4
pytest-django==4.9.0
pytest-cov==6.0.0
factory-boy==3.3.1
ipython==8.31.0
django-debug-toolbar==5.0.1
```

```
# backend/requirements/prod.txt
-r base.txt
sentry-sdk[django]==2.19.2
```

**Step 2: Create Django project config**

Create the standard Django project files under `backend/config/` with split settings (base/dev/prod). Key config:

- `base.py`: Installed apps include `rest_framework`, `corsheaders`, `django_filters`, apps (`blog`, `users`, `quant`). Database uses PostgreSQL via env vars. REST framework uses JWT auth. Celery config points to Redis.
- `dev.py`: DEBUG=True, CORS allow all, debug toolbar.
- `prod.py`: DEBUG=False, strict CORS/ALLOWED_HOSTS, security headers.
- `celery.py`: Standard Celery app with `config.settings` config, autodiscover tasks.

**Step 3: Create empty Django apps**

```bash
cd backend
python manage.py startapp blog apps/blog
python manage.py startapp users apps/users
python manage.py startapp quant apps/quant
```

Each app gets `__init__.py`, `models.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py`, `apps.py`.

**Step 4: Run test to verify Django starts**

```bash
docker compose up -d postgres redis
docker compose run django python manage.py check
```
Expected: "System check identified no issues."

**Step 5: Commit**

```bash
git add backend/
git commit -m "feat: scaffold Django 5.2 backend with split settings, Celery, and app stubs"
```

### Task 0.4: Scaffold Vue 3 frontend

**Files:**
- Create: `frontend/` (via `npm create vite@latest`)
- Modify: `frontend/package.json` (add dependencies)
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/stores/index.ts`
- Create: `frontend/src/api/client.ts`

**Step 1: Create Vite + Vue 3 + TypeScript project**

```bash
cd frontend
npm create vite@latest . -- --template vue-ts
```

**Step 2: Install dependencies**

```bash
npm install vue-router@4 pinia axios element-plus @element-plus/icons-vue
npm install tailwindcss @tailwindcss/vite
npm install echarts vue-echarts @kjgl77/datav-vue3
npm install @tsparticles/vue3 @tsparticles/engine @tsparticles/slim
npm install aplayer vditor @tinymce/tinymce-vue
npm install -D @types/node
```

**Step 3: Configure Tailwind CSS**

```js
// tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#00d4ff', dark: '#0a1628' },
        surface: { DEFAULT: '#0f1923', light: '#162133' },
        accent: '#ff6b35',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

**Step 4: Set up Vue Router with placeholder routes**

Create `src/router/index.ts` with all routes from design doc (blog public + admin + quant), each pointing to placeholder components.

**Step 5: Set up Pinia store**

Create `src/stores/index.ts` with basic store setup.

**Step 6: Set up axios client**

Create `src/api/client.ts` with base URL, JWT interceptor, error handling.

**Step 7: Verify frontend starts**

```bash
npm run dev
```
Expected: Vite dev server starts at localhost:5173.

**Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Vue 3 frontend with Vite, Tailwind, Element Plus, Router, Pinia"
```

---

## Phase 1: User Authentication System

### Task 1.1: User model and JWT auth backend

**Files:**
- Create: `backend/apps/users/models.py`
- Create: `backend/apps/users/serializers.py`
- Create: `backend/apps/users/views.py`
- Create: `backend/apps/users/urls.py`
- Create: `backend/apps/users/tests/test_models.py`
- Create: `backend/apps/users/tests/test_api.py`

**Step 1: Write failing test for custom User model**

```python
# backend/apps/users/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_create_admin_user():
    user = User.objects.create_user(
        username="admin", email="admin@test.com", password="testpass123",
        role="admin"
    )
    assert user.role == "admin"
    assert user.is_active
    assert str(user) == "admin"

@pytest.mark.django_db
def test_create_visitor():
    user = User.objects.create_user(
        username="visitor", email="v@test.com", password="testpass123",
        role="visitor"
    )
    assert user.role == "visitor"
```

**Step 2: Run test to verify it fails**

```bash
docker compose run django pytest apps/users/tests/test_models.py -v
```

**Step 3: Implement User model**

```python
# backend/apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [("admin", "Admin"), ("visitor", "Visitor")]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="visitor")
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.username
```

Set `AUTH_USER_MODEL = "users.User"` in `config/settings/base.py`.

**Step 4: Write failing test for JWT auth API**

```python
# backend/apps/users/tests/test_api.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.mark.django_db
def test_jwt_login():
    User.objects.create_user(username="admin", password="testpass123", role="admin")
    client = APIClient()
    resp = client.post("/api/auth/token/", {"username": "admin", "password": "testpass123"})
    assert resp.status_code == 200
    assert "access" in resp.data

@pytest.mark.django_db
def test_jwt_protected_endpoint():
    client = APIClient()
    resp = client.get("/api/admin/dashboard/")
    assert resp.status_code == 401
```

**Step 5: Implement JWT auth views and URLs**

Wire up `TokenObtainPairView`, `TokenRefreshView` at `/api/auth/token/` and `/api/auth/token/refresh/`.

**Step 6: Run tests, verify pass**

```bash
docker compose run django pytest apps/users/tests/ -v
```

**Step 7: Commit**

```bash
git add backend/apps/users/
git commit -m "feat: add custom User model with roles and JWT authentication"
```

---

## Phase 2: Blog Backend

### Task 2.1: Blog models (Category, Tag, Post)

**Files:**
- Create: `backend/apps/blog/models.py`
- Create: `backend/apps/blog/tests/test_models.py`

**TDD Flow:** Write tests for Category (tree structure), Tag, Post (status, slugs, pinned). Then implement models. Then migrate. Then verify tests pass.

### Task 2.2: Blog serializers and public API

**Files:**
- Create: `backend/apps/blog/serializers.py`
- Create: `backend/apps/blog/views.py`
- Create: `backend/apps/blog/urls.py`
- Create: `backend/apps/blog/tests/test_api.py`

**TDD Flow:** Write tests for GET `/api/posts/` (list, pagination, filter by category/tag), GET `/api/posts/:slug/` (detail with view count increment), GET `/api/categories/` (tree), GET `/api/tags/`, GET `/api/archives/`. Then implement serializers and viewsets.

### Task 2.3: Comment model and API

**Files:**
- Modify: `backend/apps/blog/models.py` (add Comment, FriendLink, SiteConfig)
- Create: `backend/apps/blog/tests/test_comments.py`

**TDD Flow:** Write tests for nested comments, anonymous commenting (nickname+email), moderation (is_approved). Public GET returns only approved comments. POST creates pending comment. Admin can approve/delete.

### Task 2.4: Blog admin API

**Files:**
- Create: `backend/apps/blog/views_admin.py`
- Create: `backend/apps/blog/tests/test_admin_api.py`

**TDD Flow:** Write tests for admin CRUD on posts (create draft, publish, archive), categories, tags, comments (approve/delete), image upload. All require JWT admin auth.

### Task 2.5: Dashboard stats API

**Files:**
- Modify: `backend/apps/blog/views_admin.py`

**TDD Flow:** Test GET `/api/admin/dashboard/` returns: total posts, total views, total comments, posts by month (for chart), recent comments.

**Commit after each task.**

---

## Phase 3: Blog Frontend - Public Pages

### Task 3.1: Layout and sci-fi theme

**Files:**
- Create: `frontend/src/layouts/BlogLayout.vue`
- Create: `frontend/src/styles/theme.css`
- Modify: `frontend/src/App.vue`

Build the main blog layout: dark background (#0a1628), navbar with glow effects, footer. Integrate tsparticles as background on homepage.

### Task 3.2: Homepage

**Files:**
- Create: `frontend/src/views/blog/HomePage.vue`
- Create: `frontend/src/components/blog/PostCard.vue`
- Create: `frontend/src/components/blog/HeroSection.vue`

Homepage with DataV border decoration on hero section, particle background, latest posts waterfall grid.

### Task 3.3: Post list and detail pages

**Files:**
- Create: `frontend/src/views/blog/PostListPage.vue`
- Create: `frontend/src/views/blog/PostDetailPage.vue`
- Create: `frontend/src/components/blog/CommentSection.vue`
- Create: `frontend/src/api/blog.ts`

Post list with pagination, category/tag filter. Post detail with markdown rendering (highlight.js for code), comment section with submit form.

### Task 3.4: Category, Tag, Archive pages

**Files:**
- Create: `frontend/src/views/blog/CategoriesPage.vue`
- Create: `frontend/src/views/blog/TagsPage.vue`
- Create: `frontend/src/views/blog/ArchivesPage.vue`

Category tree, tag cloud visualization, timeline archive.

### Task 3.5: About page and special effects

**Files:**
- Create: `frontend/src/views/blog/AboutPage.vue`
- Create: `frontend/src/components/common/MusicPlayer.vue`
- Create: `frontend/src/components/common/Live2DWidget.vue`

About page. Integrate APlayer (floating music player). Integrate oh-my-live2d (bottom-right character).

**Commit after each task.**

---

## Phase 4: Blog Admin Frontend

### Task 4.1: Admin layout and auth

**Files:**
- Create: `frontend/src/layouts/AdminLayout.vue`
- Create: `frontend/src/views/admin/LoginPage.vue`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/api/auth.ts`

Element Plus based admin layout with sidebar navigation. Login page with JWT. Pinia auth store with token management. Router guard for admin routes.

### Task 4.2: Dashboard page

**Files:**
- Create: `frontend/src/views/admin/DashboardPage.vue`

Stats cards (total posts, views, comments), traffic trend chart (ECharts line chart), recent comments table.

### Task 4.3: Post management with dual editor

**Files:**
- Create: `frontend/src/views/admin/PostListPage.vue`
- Create: `frontend/src/views/admin/PostEditPage.vue`
- Create: `frontend/src/components/admin/MarkdownEditor.vue`
- Create: `frontend/src/components/admin/RichTextEditor.vue`

Post list table with status filter, bulk actions. Edit page with Vditor (markdown) / TinyMCE (rich text) toggle. Image upload. Category/tag selector.

### Task 4.4: Category, Tag, Comment management

**Files:**
- Create: `frontend/src/views/admin/CategoryPage.vue`
- Create: `frontend/src/views/admin/TagPage.vue`
- Create: `frontend/src/views/admin/CommentPage.vue`

CRUD tables using Element Plus el-table. Comment moderation with approve/delete actions.

### Task 4.5: Site settings page

**Files:**
- Create: `frontend/src/views/admin/SettingsPage.vue`

Form for site name, description, logo upload, social links.

**Commit after each task.**

---

## Phase 5: Quant Data Layer

### Task 5.1: TimescaleDB models and migrations

**Files:**
- Create: `backend/apps/quant/models.py`
- Create: `backend/apps/quant/tests/test_models.py`
- Create: `backend/apps/quant/migrations/0002_create_hypertables.py` (RunSQL)

**TDD Flow:** Write tests for StockBasic, KlineData, MoneyFlow, MarginData, FinancialReport, NewsArticle models. Create custom migration to convert KlineData, MoneyFlow, MarginData to TimescaleDB hypertables using `SELECT create_hypertable(...)`.

### Task 5.2: Data source abstraction layer

**Files:**
- Create: `backend/apps/quant/datasources/__init__.py`
- Create: `backend/apps/quant/datasources/base.py`
- Create: `backend/apps/quant/datasources/akshare_source.py`
- Create: `backend/apps/quant/datasources/tushare_source.py`
- Create: `backend/apps/quant/datasources/router.py`
- Create: `backend/apps/quant/tests/test_datasources.py`

**TDD Flow:** Define `DataSourceBase` ABC. Implement `AKShareSource` with methods: `fetch_stock_list()`, `fetch_kline()`, `fetch_money_flow()`, `fetch_news()`. Implement `TushareSource` as supplementary. Implement `DataSourceRouter` with failover logic. Test with mocked API responses.

### Task 5.3: Celery tasks for data ingestion

**Files:**
- Create: `backend/apps/quant/tasks.py`
- Create: `backend/apps/quant/tests/test_tasks.py`

**TDD Flow:** Write tasks: `sync_daily_kline`, `sync_money_flow`, `sync_news`, `sync_financial_reports`, `validate_data`. Configure Celery Beat schedule. Test with mocked data sources.

**Commit after each task.**

---

## Phase 6: Quant Analysis Layer

### Task 6.1: Analyzer base and result types

**Files:**
- Create: `backend/apps/quant/analyzers/__init__.py`
- Create: `backend/apps/quant/analyzers/base.py`
- Create: `backend/apps/quant/analyzers/types.py`
- Create: `backend/apps/quant/tests/test_analyzer_base.py`

Define `AnalysisResult` dataclass (score, signals, explanation, confidence), `Signal` enum (BUY/SELL/HOLD), `AnalyzerBase` ABC.

### Task 6.2: Technical Analyzer

**Files:**
- Create: `backend/apps/quant/analyzers/technical.py`
- Create: `backend/apps/quant/tests/test_technical.py`

Implement MA, MACD, KDJ, BOLL, RSI, Volume analysis. Calculate score based on confluence of indicators. TDD with known stock data fixtures.

### Task 6.3: Fundamental Analyzer

**Files:**
- Create: `backend/apps/quant/analyzers/fundamental.py`
- Create: `backend/apps/quant/tests/test_fundamental.py`

PE/PB valuation, ROE quality, revenue/profit growth trends, gross margin. Score based on value + quality + growth.

### Task 6.4: Money Flow Analyzer

**Files:**
- Create: `backend/apps/quant/analyzers/money_flow.py`
- Create: `backend/apps/quant/tests/test_money_flow.py`

Main/retail net flow, DDX/DDY/DDZ indicators, consecutive days of main inflow.

### Task 6.5: Chip Analyzer

**Files:**
- Create: `backend/apps/quant/analyzers/chip.py`
- Create: `backend/apps/quant/tests/test_chip.py`

Cost distribution estimation, concentration ratio, profit ratio at current price.

### Task 6.6: Sentiment Analyzer

**Files:**
- Create: `backend/apps/quant/analyzers/sentiment.py`
- Create: `backend/apps/quant/tests/test_sentiment.py`

Market advance/decline ratio, limit-up/down counts, average turnover rate, volatility index.

### Task 6.7: Remaining analyzers (News, Sector Rotation, Game Theory, Behavior Finance, Macro)

**Files:**
- Create one file per analyzer in `backend/apps/quant/analyzers/`
- Create corresponding test files

Each follows the same `AnalyzerBase` pattern. NewsAnalyzer will integrate with AI service (Task 7.1).

### Task 6.8: Multi-Factor Scorer

**Files:**
- Create: `backend/apps/quant/scorers/__init__.py`
- Create: `backend/apps/quant/scorers/multi_factor.py`
- Create: `backend/apps/quant/tests/test_scorer.py`

Implement `MultiFactorScorer` with configurable weights per trading style (ultra-short, swing, mid-long). Aggregates 11 analyzer results into composite score.

### Task 6.9: Signal Generator

**Files:**
- Create: `backend/apps/quant/signals/__init__.py`
- Create: `backend/apps/quant/signals/generator.py`
- Create: `backend/apps/quant/tests/test_signals.py`

Implement `SignalGenerator`: takes composite score + individual signals, outputs action (BUY/SELL/HOLD), entry price, stop-loss (by style), take-profit (multi-level), position size, reason text.

### Task 6.10: Analysis pipeline Celery task

**Files:**
- Modify: `backend/apps/quant/tasks.py`
- Create: `backend/apps/quant/tests/test_pipeline.py`

`run_analysis_pipeline` task: fetch stock universe → run all analyzers → score → generate signals → save recommendations. Scheduled daily at 17:00.

**Commit after each task.**

---

## Phase 7: AI Integration

### Task 7.1: AI service abstraction

**Files:**
- Create: `backend/apps/quant/ai/__init__.py`
- Create: `backend/apps/quant/ai/service.py`
- Create: `backend/apps/quant/ai/prompts.py`
- Create: `backend/apps/quant/tests/test_ai.py`

**TDD Flow:** Implement `AIService` with provider switching (deepseek/chatgpt). Methods: `analyze_news()`, `analyze_financial()`, `generate_report()`, `score_factors()`. System prompts in `prompts.py`. Daily API budget tracking. Test with mocked OpenAI responses.

### Task 7.2: Wire AI into NewsAnalyzer and AIAnalyzer

**Files:**
- Modify: `backend/apps/quant/analyzers/news.py`
- Create: `backend/apps/quant/analyzers/ai_analyzer.py`
- Create: `backend/apps/quant/tests/test_ai_analyzer.py`

NewsAnalyzer calls `AIService.analyze_news()` for sentiment scoring. AIAnalyzer calls `AIService.score_factors()` for AI-assisted factor scoring and `AIService.generate_report()` for reports.

**Commit after each task.**

---

## Phase 8: Paper Trading Simulator

### Task 8.1: Simulator models

**Files:**
- Modify: `backend/apps/quant/models.py` (add Portfolio, Position, Trade, PerformanceMetric)
- Create: `backend/apps/quant/simulator/__init__.py`
- Create: `backend/apps/quant/tests/test_simulator_models.py`

### Task 8.2: Simulator logic

**Files:**
- Create: `backend/apps/quant/simulator/engine.py`
- Create: `backend/apps/quant/tests/test_simulator.py`

**TDD Flow:** Implement `SimulatorEngine`: `buy()`, `sell()`, `get_portfolio()`, `calculate_performance()`. Track trades, update positions, calculate daily returns, max drawdown, Sharpe ratio, win rate.

### Task 8.3: Simulator API

**Files:**
- Create: `backend/apps/quant/simulator/views.py`
- Create: `backend/apps/quant/simulator/serializers.py`
- Create: `backend/apps/quant/tests/test_simulator_api.py`

API endpoints for portfolio, trades, performance.

**Commit after each task.**

---

## Phase 9: Quant API

### Task 9.1: Quant API endpoints

**Files:**
- Create: `backend/apps/quant/views.py`
- Create: `backend/apps/quant/serializers.py`
- Create: `backend/apps/quant/urls.py`
- Create: `backend/apps/quant/tests/test_api.py`

**TDD Flow:** Implement all quant API endpoints from design doc: recommendations (filterable by style), stock analysis, K-line data, AI reports, factor weight config, task monitoring. All require admin JWT auth.

**Commit.**

---

## Phase 10: Quant Frontend

### Task 10.1: Quant dashboard

**Files:**
- Create: `frontend/src/views/admin/quant/DashboardPage.vue`
- Create: `frontend/src/api/quant.ts`
- Create: `frontend/src/stores/quant.ts`

Today's top picks cards, portfolio P&L summary, market overview (ECharts).

### Task 10.2: Stock picks page

**Files:**
- Create: `frontend/src/views/admin/quant/PicksPage.vue`
- Create: `frontend/src/components/quant/StockPickCard.vue`

Tab-based view (ultra-short / swing / mid-long). Each card shows: stock name, composite score, signal, stop-loss/take-profit, brief reason.

### Task 10.3: Stock analysis page

**Files:**
- Create: `frontend/src/views/admin/quant/StockAnalysisPage.vue`
- Create: `frontend/src/components/quant/RadarChart.vue`
- Create: `frontend/src/components/quant/AnalysisPanels.vue`

11-dimension radar chart (ECharts). Expandable panels for each dimension's detailed analysis. DataV decorative borders.

### Task 10.4: K-line workbench

**Files:**
- Create: `frontend/src/views/admin/quant/KlineWorkbench.vue`
- Create: `frontend/src/components/quant/KlineChart.vue`
- Create: `frontend/src/components/quant/IndicatorPanel.vue`

ECharts candlestick chart with volume. Toggleable overlays: MA, BOLL. Sub-charts: MACD, KDJ, RSI. Period selector (daily/weekly/monthly). DataV sci-fi frame.

### Task 10.5: Paper trading page

**Files:**
- Create: `frontend/src/views/admin/quant/SimulatorPage.vue`
- Create: `frontend/src/components/quant/PortfolioTable.vue`
- Create: `frontend/src/components/quant/EquityCurve.vue`
- Create: `frontend/src/components/quant/TradeHistory.vue`

Portfolio positions table, equity curve (ECharts line), trade history table, performance metrics cards (return, drawdown, Sharpe, win rate).

### Task 10.6: AI reports and system config pages

**Files:**
- Create: `frontend/src/views/admin/quant/ReportsPage.vue`
- Create: `frontend/src/views/admin/quant/SettingsPage.vue`

AI report list with expandable detail. Config page: factor weight sliders (per style), API key fields, data source toggles, Celery task status.

**Commit after each task.**

---

## Phase 11: Production Deployment

### Task 11.1: Production configs

**Files:**
- Modify: `docker-compose.prod.yml` (finalize)
- Create: `docker/nginx/ssl.conf` (HTTPS with Let's Encrypt placeholder)
- Create: `scripts/deploy.sh`
- Create: `scripts/backup.sh`

Finalize production Docker Compose. Add deploy script (build, push, docker compose up). Add backup script for PostgreSQL.

### Task 11.2: CI/CD (optional)

GitHub Actions workflow for: lint (ruff + eslint), test (pytest + vitest), build (Docker images).

**Commit.**

---

## Execution Order Summary

| Phase | Description | Depends On | Est. Tasks |
|-------|-------------|------------|------------|
| 0 | Scaffolding & Docker | - | 4 |
| 1 | User Auth | Phase 0 | 1 |
| 2 | Blog Backend | Phase 1 | 5 |
| 3 | Blog Frontend Public | Phase 0.4 | 5 |
| 4 | Blog Admin Frontend | Phase 2, 3 | 5 |
| 5 | Quant Data Layer | Phase 1 | 3 |
| 6 | Quant Analysis Layer | Phase 5 | 10 |
| 7 | AI Integration | Phase 6 | 2 |
| 8 | Paper Trading | Phase 5 | 3 |
| 9 | Quant API | Phase 6, 7, 8 | 1 |
| 10 | Quant Frontend | Phase 9 | 6 |
| 11 | Production Deploy | All | 2 |

**Parallelizable pairs:**
- Phase 2 (blog backend) + Phase 3 (blog frontend) after Phase 1
- Phase 5 (quant data) can start alongside Phase 3/4
- Phase 6 analyzers (6.2-6.7) can be parallelized across subagents
- Phase 8 (simulator) can parallel with Phase 7 (AI)

**Total estimated tasks: ~47**
