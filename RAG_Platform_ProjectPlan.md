# 📋 RAG 知識庫平台開發計畫書 v2.1

**版本**: v2.1  
**日期**: 2026-04-01  
**開發工具**: Claude Code + shadcn/ui Skills  
**框架核心**: HKUDS/RAG-Anything v1.2.9

---

## 📌 專案概覽

### 專案名稱
**RAG Knowledge Platform** — 基於 RAG-Anything 的多模態知識庫多輪對話問答系統

### 核心技術棧

| 層級 | 技術 |
|------|------|
| 前端 | Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui，套件管理使用 **yarn** |
| 後端 | FastAPI + Python 3.11 + SQLAlchemy ORM (Async) |
| AI 引擎 | HKUDS/RAG-Anything (建構在 LightRAG 之上) |
| LLM（文字推理） | Ollama → `gpt-oss:latest` |
| Vision（圖片分析） | Ollama → `llava:7b`（文件內圖片 caption 專用） |
| Embedding | HuggingFace `BAAI/bge-m3` (本地，1024-dim) |
| 向量資料庫 | ChromaDB |
| 關聯式資料庫 | SQLite via SQLAlchemy Async ORM + Alembic |
| 容器化 | Docker + Docker Compose |
| 本地開發 | uv 虛擬環境 |

---

## 🏗️ 系統架構圖

```
┌──────────────────────────────────────────────────────────────────┐
│                         Docker Network                            │
│                                                                  │
│  ┌────────────────┐       ┌───────────────────────────────────┐  │
│  │   Frontend     │       │           Backend (FastAPI)        │  │
│  │  Next.js 14    │◄─────►│  ┌─────────────────────────────┐  │  │
│  │  Port: 3000    │  SSE  │  │       API Routers           │  │  │
│  │                │       │  │  auth / documents / chat /  │  │  │
│  │  - Chat UI     │       │  │  sessions / query(SSE)      │  │  │
│  │  - Session List│       │  └──────────┬──────────────────┘  │  │
│  │  - Doc Upload  │       │             │                      │  │
│  │  - Admin Panel │       │  ┌──────────▼──────────────────┐  │  │
│  └────────────────┘       │  │       Services              │  │  │
│                           │  │  AuthService                │  │  │
│                           │  │  DocumentService            │  │  │
│                           │  │  ChatSessionService         │  │  │
│                           │  │  ConversationService ◄──────┼──┼──── 多輪對話管理
│                           │  │  RAGQueryService            │  │  │
│                           │  └──────────┬──────────────────┘  │  │
│                           │             │                      │  │
│                           │  ┌──────────▼──────────────────┐  │  │
│                           │  │     RAG Engine Layer        │  │  │
│                           │  │  OllamaLLMAdapter (gpt-oss) │  │  │
│                           │  │  OllamaVisionAdapter (llava) │  │  │
│                           │  │  BGEEmbeddingAdapter        │  │  │
│                           │  │  ChromaVectorStorage        │  │  │
│                           │  │  ConversationCompactor ◄────┼──┼──── Compact 壓縮
│                           │  └──────────┬──────────────────┘  │  │
│                           └────────────┬┴───────────────────── ┘  │
│                                        │                          │
│  ┌─────────────┐  ┌───────────────┐  ┌─┴──────────┐  ┌────────┐  │
│  │  ChromaDB   │  │  SQLite DB    │  │   Ollama   │  │(future)│  │
│  │  Port:8001  │  │  (知識圖譜+   │  │  Port:11434│  │        │  │
│  │  向量儲存   │  │   對話紀錄)   │  │  gpt-oss + │  │        │  │
│  └─────────────┘  └───────────────┘  │  llava:7b  │  └────────┘  │
│                                      └────────────┘              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ 完整目錄結構

```
rag-platform/
├── CLAUDE.md                              # Claude Code 開發規範
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── docker-compose.dev.yml
├── scripts/
│   └── init-ollama.sh                     # 首次拉取 Ollama 模型腳本
│
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── scripts/
│   │   └── create_admin.py
│   │
│   └── app/
│       ├── __init__.py
│       ├── main.py                        # FastAPI lifespan 入口
│       ├── config.py                      # Pydantic Settings
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── deps.py                    # 依賴注入
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── auth.py
│       │       ├── documents.py
│       │       ├── sessions.py            # 對話視窗 CRUD ← 新增
│       │       └── query.py              # SSE 串流查詢
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── security.py
│       │   └── exceptions.py
│       │
│       ├── db/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── session.py
│       │   └── migrations/
│       │       └── versions/
│       │
│       ├── models/                        # ORM Models
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── document.py
│       │   ├── chat_session.py            # 對話視窗 ← 新增
│       │   └── message.py                # 每則訊息 ← 新增
│       │
│       ├── schemas/                       # Pydantic Schemas
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── document.py
│       │   ├── session.py                 # ← 新增
│       │   ├── message.py                 # ← 新增
│       │   └── query.py
│       │
│       ├── repositories/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── user_repository.py
│       │   ├── document_repository.py
│       │   ├── session_repository.py      # ← 新增
│       │   └── message_repository.py      # ← 新增
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── auth_service.py
│       │   ├── document_service.py
│       │   ├── chat_session_service.py    # 對話視窗管理 ← 新增
│       │   ├── conversation_service.py    # 多輪對話 + Compact ← 新增
│       │   └── rag_query_service.py
│       │
│       └── rag/
│           ├── __init__.py
│           ├── engine.py
│           ├── llm_adapter.py
│           ├── embedding_adapter.py
│           ├── chroma_adapter.py
│           └── conversation_compactor.py  # Compact 壓縮邏輯 ← 新增
│
└── frontend/
    ├── .claude/
    │   └── skills/                        # shadcn/ui skills (自動建立)
    ├── package.json
    ├── yarn.lock                          # yarn 鎖定檔（取代 package-lock.json）
    ├── .yarnrc.yml                        # yarn 設定（nodeLinker: node-modules）
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── next.config.ts
    ├── middleware.ts
    ├── Dockerfile
    │
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx
        │   ├── (auth)/
        │   │   ├── login/page.tsx
        │   │   └── signup/page.tsx
        │   └── (dashboard)/
        │       ├── layout.tsx
        │       ├── chat/
        │       │   ├── page.tsx           # 新建對話
        │       │   └── [sessionId]/
        │       │       └── page.tsx       # 特定對話視窗 ← 新增
        │       ├── documents/page.tsx
        │       └── admin/
        │           ├── users/page.tsx
        │           └── documents/page.tsx
        │
        ├── components/
        │   ├── ui/                        # shadcn/ui 元件
        │   ├── auth/
        │   │   ├── LoginForm.tsx
        │   │   └── SignupForm.tsx
        │   ├── chat/
        │   │   ├── ChatWindow.tsx
        │   │   ├── MessageBubble.tsx
        │   │   ├── InputBar.tsx
        │   │   ├── StreamingText.tsx
        │   │   └── SessionSidebar.tsx     # 對話列表側欄 ← 新增
        │   ├── documents/
        │   │   ├── UploadZone.tsx
        │   │   ├── DocumentList.tsx
        │   │   └── DocumentCard.tsx
        │   └── layout/
        │       ├── DashboardLayout.tsx
        │       ├── Header.tsx
        │       └── AdminGuard.tsx
        │
        ├── hooks/
        │   ├── useAuth.ts
        │   ├── useSSEStream.ts            # SSE 串流 hook
        │   ├── useChatSession.ts          # 對話視窗 CRUD ← 新增
        │   └── useDocuments.ts
        │
        ├── lib/
        │   ├── api.ts
        │   ├── auth.ts
        │   └── utils.ts
        │
        ├── store/
        │   ├── authStore.ts
        │   └── chatStore.ts               # session + messages 狀態 ← 擴充
        │
        └── types/
            ├── auth.ts
            ├── document.ts
            ├── session.ts                 # ← 新增
            └── message.ts                 # ← 新增
```

---

## 📅 開發 Steps

---

## STEP 0 — 專案初始化與環境設置

> 目標：建立整個專案的骨架、開發規範與環境，後續所有 Step 都在此基礎上進行。

### Checklist

- [ ] **建立 Monorepo 根目錄結構**
  - 建立 `rag-platform/` 根目錄
  - 建立 `backend/`、`frontend/`、`data/` 子目錄
  - `git init`，建立 `.gitignore`（含 `.env`、`__pycache__`、`.next`、`data/`）

- [ ] **撰寫 `CLAUDE.md` 開發規範**
  - 定義架構分層規則：`Router → Service → Repository → ORM Model`
  - 定義 OOP 規則：所有 Service / Repository 必須使用 `class`，禁止 standalone function 作為業務邏輯
  - 定義 Clean Code 規則：所有 public method 必須有 type hints、所有 class 必須有 docstring、禁止 magic number
  - 定義 Git Convention：`feat/xxx`、`fix/xxx`、`refactor/xxx`、每個 Step 完成後需 commit
  - 定義 Schema 使用規範：Pydantic Schema 只在 Router 層做 request/response 轉換

- [ ] **初始化 Backend uv 環境**
  - 在 `backend/` 執行 `uv init`
  - 安裝核心依賴：
    ```
    fastapi uvicorn[standard] sqlalchemy[asyncio] aiosqlite alembic
    pydantic-settings python-jose[cryptography] passlib[bcrypt]
    python-multipart aiofiles httpx
    raganything sentence-transformers chromadb
    ```
  - 安裝開發依賴：`pytest pytest-asyncio httpx`
  - 確認 `pyproject.toml` 與 `uv.lock` 生成正確

- [ ] **初始化 Frontend 環境**
  - 執行 `yarn create next-app` (App Router + TypeScript + Tailwind)
  - 執行 `yarn dlx shadcn@latest init`，確認 `frontend/.claude/skills/` 目錄存在
  - 安裝依賴：`yarn add zustand axios react-dropzone react-markdown react-hook-form zod`
  - 安裝開發依賴：`yarn add -D @types/node`
  - 確認 `yarn.lock` 產生，**禁止同時存在 `package-lock.json`**（加入 `.gitignore`）

- [ ] **建立 `.env.example`**
  ```env
  # === Backend ===
  SECRET_KEY=change-me-to-random-32-char-string
  ACCESS_TOKEN_EXPIRE_MINUTES=60
  DATABASE_URL=sqlite+aiosqlite:///./data/rag_platform.db

  CHROMA_HOST=chromadb
  CHROMA_PORT=8001

  OLLAMA_BASE_URL=http://ollama:11434
  OLLAMA_LLM_MODEL=gpt-oss:latest      # 文字推理、多輪對話、摘要
  OLLAMA_VISION_MODEL=llava:7b          # 文件內圖片 caption（RAG-Anything vision_model_func 專用）

  EMBEDDING_MODEL_NAME=BAAI/bge-m3
  EMBEDDING_DIM=1024

  RAG_WORKING_DIR=/app/rag_storage
  UPLOAD_DIR=/app/uploads

  # 多輪對話設定
  CONVERSATION_MAX_HISTORY_TURNS=20
  CONVERSATION_COMPACT_THRESHOLD=15
  CONVERSATION_COMPACT_TARGET=6

  # === Frontend ===
  NEXT_PUBLIC_API_URL=http://localhost:8000
  ```

- [ ] **建立 `backend/app/config.py`**
  - 使用 `pydantic-settings` 的 `BaseSettings` 讀取 `.env`
  - 所有設定集中在單一 `Settings` class，禁止散落在各模組中

---

## STEP 1 — 資料庫 ORM 設計與 Migration

> 目標：定義所有資料表結構（含多輪對話新增表），建立 Repository 抽象層，完成首次 migration。

### Checklist

- [ ] **建立 `db/base.py`：SQLAlchemy Async Base**
  - 使用 `DeclarativeBase` (SQLAlchemy 2.0 新式寫法)
  - 建立 `TimestampMixin`：提供 `created_at`、`updated_at` 自動填值（`datetime.utcnow`）
  - 建立 `UUIDMixin`：提供 `id: Mapped[UUID]` 作為所有 table 的 PK

- [ ] **建立 `db/session.py`：Async Session Factory**
  - 使用 `create_async_engine` + `async_sessionmaker`
  - 提供 `get_async_session` async generator 供依賴注入使用
  - 設定 `echo=False`（production）/ `echo=True`（dev）

- [ ] **設計 ORM Model：`models/user.py`**
  ```
  Table: users
  ├── id: UUID (PK)
  ├── email: str (unique, not null)
  ├── hashed_password: str (not null)
  ├── full_name: str
  ├── role: Enum ["admin", "user"] (default: "user")
  ├── is_active: bool (default: True)
  ├── created_at: datetime
  └── updated_at: datetime

  Relationships:
  └── chat_sessions: list[ChatSession]
  └── documents: list[Document]
  ```

- [ ] **設計 ORM Model：`models/document.py`**
  ```
  Table: documents
  ├── id: UUID (PK)
  ├── title: str
  ├── original_filename: str
  ├── stored_filename: str (UUID-renamed，避免衝突)
  ├── file_path: str
  ├── file_size: int (bytes)
  ├── mime_type: str
  ├── status: Enum ["pending","processing","completed","failed"]
  ├── error_message: str | None (失敗時記錄原因)
  ├── uploaded_by_id: UUID (FK → users.id)
  ├── rag_doc_id: str | None (RAG-Anything 內部 doc_id)
  ├── created_at: datetime
  └── updated_at: datetime
  ```

- [ ] **設計 ORM Model：`models/chat_session.py`** ← 新增
  ```
  Table: chat_sessions
  ├── id: UUID (PK)
  ├── user_id: UUID (FK → users.id, CASCADE DELETE)
  ├── title: str (預設 "新對話"，可由使用者或第一句話自動命名)
  ├── query_mode: str (default: "hybrid"，儲存此 session 使用的 RAG 模式)
  ├── message_count: int (冗餘計數，方便列表顯示)
  ├── last_message_at: datetime | None
  ├── is_compacted: bool (default: False，標記是否曾被壓縮)
  ├── compact_summary: str | None (Compact 後的摘要文字)
  ├── created_at: datetime
  └── updated_at: datetime

  Relationships:
  └── messages: list[Message]
  └── user: User
  ```

- [ ] **設計 ORM Model：`models/message.py`** ← 新增
  ```
  Table: messages
  ├── id: UUID (PK)
  ├── session_id: UUID (FK → chat_sessions.id, CASCADE DELETE)
  ├── role: Enum ["user", "assistant", "system"]
  ├── content: str (完整文字內容)
  ├── token_count: int | None (估算 token 數，供 Compact 判斷使用)
  ├── is_compacted_summary: bool (default: False，標記此訊息是否為 Compact 摘要)
  ├── rag_sources: str | None (JSON 字串，儲存 RAG 來源 document IDs)
  ├── query_mode: str | None (此訊息使用的查詢模式)
  ├── created_at: datetime
  └── updated_at: datetime

  Index: (session_id, created_at) — 加速按時間排序的訊息查詢
  ```

- [ ] **建立 `repositories/base.py`：泛型 BaseRepository**
  ```python
  class BaseRepository(Generic[ModelT]):
      """
      所有 Repository 繼承此類別，提供通用 CRUD 操作。
      使用 SQLAlchemy Async session。
      """
      def __init__(self, session: AsyncSession, model: Type[ModelT])

      async def get_by_id(self, id: UUID) -> ModelT | None
      async def get_all(self, skip: int = 0, limit: int = 50) -> list[ModelT]
      async def create(self, data: dict) -> ModelT
      async def update(self, id: UUID, data: dict) -> ModelT | None
      async def delete(self, id: UUID) -> bool
      async def count(self) -> int
  ```

- [ ] **建立 `repositories/user_repository.py`**
  ```python
  class UserRepository(BaseRepository[User]):
      async def get_by_email(self, email: str) -> User | None
      async def get_active_users(self) -> list[User]
      async def deactivate(self, id: UUID) -> User | None
  ```

- [ ] **建立 `repositories/document_repository.py`**
  ```python
  class DocumentRepository(BaseRepository[Document]):
      async def get_by_uploader(self, user_id: UUID, skip: int, limit: int) -> list[Document]
      async def get_by_status(self, status: str) -> list[Document]
      async def update_status(self, doc_id: UUID, status: str, error: str | None) -> Document
      async def get_by_rag_doc_id(self, rag_doc_id: str) -> Document | None
  ```

- [ ] **建立 `repositories/session_repository.py`** ← 新增
  ```python
  class SessionRepository(BaseRepository[ChatSession]):
      async def get_by_user(self, user_id: UUID, skip: int, limit: int) -> list[ChatSession]
      async def update_title(self, session_id: UUID, title: str) -> ChatSession
      async def update_last_message(self, session_id: UUID, ts: datetime) -> None
      async def increment_message_count(self, session_id: UUID) -> None
      async def update_compact_data(
          self, session_id: UUID, summary: str, is_compacted: bool
      ) -> ChatSession
  ```

- [ ] **建立 `repositories/message_repository.py`** ← 新增
  ```python
  class MessageRepository(BaseRepository[Message]):
      async def get_by_session(
          self, session_id: UUID, skip: int = 0, limit: int = 100
      ) -> list[Message]
      async def get_recent_by_session(
          self, session_id: UUID, n: int
      ) -> list[Message]
      async def get_session_token_total(self, session_id: UUID) -> int
      async def delete_by_session(self, session_id: UUID) -> int
      async def bulk_create(self, messages: list[dict]) -> list[Message]
  ```

- [ ] **設定 Alembic**
  - 建立 `alembic.ini`，設定 async migration driver (`aiosqlite`)
  - 建立 `env.py`，import 所有 models 確保 autogenerate 能偵測到
  - 執行 `uv run alembic revision --autogenerate -m "init_all_tables"`
  - 確認 migration 檔案內容正確（含 index 定義）
  - 執行 `uv run alembic upgrade head` 確認 migration 成功

---

## STEP 2 — 會員認證系統 (Auth)

> 目標：實作 JWT 認證、Signup/Login/Logout，建立 Admin/User 角色保護機制。

### Checklist

- [ ] **建立 `core/security.py`：SecurityService**
  ```python
  class SecurityService:
      """JWT 建立/驗證 + bcrypt 密碼 hash。所有方法為 @staticmethod。"""

      @staticmethod
      def hash_password(plain_password: str) -> str
          # 使用 passlib bcrypt，rounds=12

      @staticmethod
      def verify_password(plain_password: str, hashed_password: str) -> bool

      @staticmethod
      def create_access_token(
          subject: str,           # user_id (UUID as str)
          role: str,
          expires_delta: timedelta | None = None
      ) -> str
          # payload: {"sub": subject, "role": role, "exp": ...}

      @staticmethod
      def decode_token(token: str) -> dict
          # 失敗拋出 InvalidTokenError (自訂例外)
  ```

- [ ] **建立 `core/exceptions.py`：自訂例外體系**
  ```python
  class AppBaseException(Exception): ...
  class AuthenticationError(AppBaseException): ...   # 401
  class AuthorizationError(AppBaseException): ...    # 403
  class NotFoundError(AppBaseException): ...         # 404
  class ConflictError(AppBaseException): ...         # 409
  class ValidationError(AppBaseException): ...       # 422
  class RAGProcessingError(AppBaseException): ...    # 500
  ```
  - 在 `main.py` 中註冊全域 exception handler，統一回傳格式

- [ ] **建立 `services/auth_service.py`：AuthService**
  ```python
  class AuthService:
      def __init__(self, user_repo: UserRepository)

      async def register(self, email: str, password: str, full_name: str) -> User
          # 1. 檢查 email 是否已存在 → ConflictError
          # 2. hash password
          # 3. 建立 User (role=user)

      async def authenticate(self, email: str, password: str) -> tuple[User, str]
          # 1. 查詢 user by email → AuthenticationError
          # 2. verify password → AuthenticationError
          # 3. 檢查 is_active → AuthenticationError
          # 4. 建立 access_token
          # 5. 回傳 (user, token)

      async def get_user_by_id(self, user_id: UUID) -> User
  ```

- [ ] **建立 `schemas/auth.py`**
  ```python
  class UserCreateRequest(BaseModel):
      email: EmailStr
      password: str  # min_length=8, 需包含數字+字母
      full_name: str

  class UserLoginRequest(BaseModel):
      email: EmailStr
      password: str

  class TokenResponse(BaseModel):
      access_token: str
      token_type: str = "bearer"

  class UserPublicResponse(BaseModel):
      id: UUID
      email: str
      full_name: str
      role: str
      is_active: bool
      created_at: datetime
  ```

- [ ] **建立 `api/deps.py`：依賴注入函數**
  ```python
  async def get_db() -> AsyncGenerator[AsyncSession, None]
      # yield async session

  async def get_current_user(
      token: str = Depends(oauth2_scheme),
      db: AsyncSession = Depends(get_db)
  ) -> User
      # decode token → get user → 驗證 is_active

  async def get_current_admin(
      current_user: User = Depends(get_current_user)
  ) -> User
      # 驗證 role == "admin"，否則 → AuthorizationError
  ```

- [ ] **建立 `api/v1/auth.py`：Auth Router**
  ```
  POST /api/v1/auth/signup    → UserCreateRequest → UserPublicResponse
  POST /api/v1/auth/login     → UserLoginRequest  → TokenResponse
  POST /api/v1/auth/logout    → (無 body，client 端丟棄 token，回傳 200)
  GET  /api/v1/auth/me        → (需 JWT) → UserPublicResponse
  ```

- [ ] **Admin 管理 User 的 API** (放在 `api/v1/auth.py` 或獨立 `admin.py`)
  ```
  GET    /api/v1/admin/users           → 列出所有用戶 (Admin only)
  PATCH  /api/v1/admin/users/{id}/role → 修改角色
  PATCH  /api/v1/admin/users/{id}/status → 啟用/停用
  ```

- [ ] **撰寫 `tests/test_auth.py`**
  - 測試 signup 成功 / email 重複
  - 測試 login 成功 / 密碼錯誤 / 帳號不存在
  - 測試 JWT 驗證 / 過期 token
  - 測試 admin route 保護

---

## STEP 3 — RAG-Anything 整合核心

> 目標：將 RAG-Anything 的 LLM / Embedding / Vector Storage 全部替換為本地方案（Ollama + bge-m3 + ChromaDB），封裝成可測試的 OOP 模組。

### Checklist

- [ ] **建立 `rag/llm_adapter.py`：OllamaLLMAdapter**
  ```python
  class OllamaLLMAdapter:
      """
      封裝 Ollama /api/chat endpoint，
      對外提供符合 RAG-Anything llm_model_func 簽名的 callable。
      """
      def __init__(self, base_url: str, model: str, timeout: int = 300)

      async def complete(
          self,
          prompt: str,
          system_prompt: str | None = None,
          history_messages: list[dict] = [],
          stream: bool = False,
          **kwargs
      ) -> str
          # 組裝 Ollama messages format
          # POST {base_url}/api/chat
          # stream=False 時等待完整回覆

      async def complete_stream(
          self,
          prompt: str,
          system_prompt: str | None = None,
          history_messages: list[dict] = [],
          **kwargs
      ) -> AsyncGenerator[str, None]
          # stream=True，逐 token yield

      def as_llm_func(self) -> Callable
          # 回傳符合 RAG-Anything llm_model_func 介面的 callable
  ```

- [ ] **建立 `rag/llm_adapter.py`：OllamaVisionAdapter**
  ```python
  class OllamaVisionAdapter:
      """
      封裝 Ollama multimodal endpoint，使用 llava:7b 模型，
      專門負責 RAG-Anything 文件解析階段的圖片 caption 生成。

      職責範圍：
        - 文件上傳背景處理時，對 PDF/DOCX 內嵌圖片生成描述文字
        - 描述文字存入 ChromaDB 知識庫，供後續文字查詢使用
        - 不負責即時對話，對話一律走 OllamaLLMAdapter (gpt-oss)

      vision_model_func 簽名（RAG-Anything 要求）：
        - image_data 存在 → 傳入 base64 圖片給 llava:7b 分析
        - messages 存在 → VLM Enhanced Query 模式，直接傳 messages
        - 兩者皆無 → fallback 到純文字，改呼叫 llm_model_func
      """
      def __init__(self, base_url: str, model: str = "llava:7b", timeout: int = 120)

      async def vision_complete(
          self,
          prompt: str,
          system_prompt: str | None = None,
          history_messages: list[dict] = [],
          image_data: str | None = None,   # base64 encoded image
          messages: list | None = None,    # VLM Enhanced Query 直接傳入
          **kwargs
      ) -> str
          """
          處理邏輯（對應 RAG-Anything 範例中的 vision_model_func）：
          if messages:
              # VLM Enhanced Query 模式：直接送 messages 給 llava
          elif image_data:
              # 單張圖片分析：組裝含 base64 image_url 的 messages
          else:
              # Fallback：純文字，委派給 llm_model_func (gpt-oss)
          """

      def as_vision_func(self) -> Callable
          # 回傳符合 RAG-Anything vision_model_func 介面的 callable
          # fallback 時需持有 llm_adapter 的參考
  ```

- [ ] **建立 `rag/embedding_adapter.py`：BGEEmbeddingAdapter**
  ```python
  class BGEEmbeddingAdapter:
      """
      使用 sentence-transformers 本地載入 BAAI/bge-m3。
      Lazy loading，首次呼叫時才載入模型。
      """
      EMBEDDING_DIM: int = 1024
      MAX_TOKEN_SIZE: int = 8192

      def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu")

      def _ensure_model_loaded(self) -> None
          # thread-safe lazy load，使用 threading.Lock

      async def embed(self, texts: list[str]) -> list[list[float]]
          # 在 asyncio executor 中執行同步的 model.encode()
          # 批次處理，batch_size=32

      def to_embedding_func(self) -> EmbeddingFunc
          # 回傳 LightRAG EmbeddingFunc(embedding_dim=1024, max_token_size=8192, func=...)
  ```

- [ ] **建立 `rag/chroma_adapter.py`：ChromaVectorStorage**
  ```python
  class ChromaVectorStorage:
      """
      將 ChromaDB 作為 RAG-Anything (LightRAG) 的向量儲存後端。
      實作 LightRAG 要求的 vector storage 介面。
      """
      def __init__(self, host: str, port: int, collection_name: str)

      async def initialize(self) -> None
          # 連線 ChromaDB，建立或載入 collection
          # 指定 embedding 函數為 None（外部傳入 vector）

      async def upsert(self, data: list[dict]) -> None
          # data 格式: [{"id": str, "vector": list[float], "metadata": dict, "content": str}]

      async def query(
          self,
          query_vector: list[float],
          top_k: int = 10,
          filter: dict | None = None
      ) -> list[dict]

      async def delete(self, ids: list[str]) -> None
      async def drop(self) -> None
  ```

- [ ] **建立 `rag/engine.py`：RAGEngine（單例管理器）**
  ```python
  class RAGEngine:
      """
      RAG-Anything 生命週期管理器，以單例模式在 FastAPI lifespan 中初始化。
      """
      _rag_instance: RAGAnything | None = None
      _llm_adapter: OllamaLLMAdapter | None = None
      _vision_adapter: OllamaVisionAdapter | None = None
      _embedding_adapter: BGEEmbeddingAdapter | None = None

      @classmethod
      async def initialize(cls, settings: Settings) -> None
          """
          啟動順序：
          1. 建立 OllamaLLMAdapter（model=gpt-oss:latest，負責文字推理與對話）
          2. 建立 OllamaVisionAdapter（model=llava:7b，負責文件圖片 caption）
             → OllamaVisionAdapter 持有 llm_adapter 參考，供 fallback 純文字時使用
          3. 建立 BGEEmbeddingAdapter（觸發 lazy load）
          4. 建立 ChromaVectorStorage 並 initialize()
          5. 建立 RAGAnythingConfig：
             working_dir, parser="mineru",
             enable_image_processing=True,   ← llava:7b 負責
             enable_table_processing=True,   ← gpt-oss 負責
             enable_equation_processing=True ← gpt-oss 負責
          6. 初始化 RAGAnything instance，注入 llm/vision/embedding func
          """

      @classmethod
      def get_rag(cls) -> RAGAnything

      @classmethod
      def get_llm_adapter(cls) -> OllamaLLMAdapter

      @classmethod
      async def shutdown(cls) -> None
  ```

- [ ] **整合進 `main.py` lifespan**
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      await RAGEngine.initialize(settings)
      yield
      await RAGEngine.shutdown()
  ```

- [ ] **撰寫 `tests/test_rag_adapters.py`**
  - 測試 OllamaLLMAdapter（mock httpx client）
  - 測試 OllamaVisionAdapter 三段式邏輯（messages / image_data / fallback）
  - 測試 BGEEmbeddingAdapter（mock model.encode）
  - 測試 ChromaVectorStorage（mock chromadb client）

---

## STEP 4 — 多輪對話設計：Conversation 管理與 Compact

> 目標：實作核心的多輪對話管理，包含歷史訊息注入 LLM context、token 計數、Compact 壓縮機制，確保 LLM 不會因 context 過長而「失憶」。

### 多輪對話設計說明

```
使用者第 N 句提問的完整 context 組裝流程：

Step A: 從 DB 取出此 session 最近 N 條 messages（已排序）
        messages = [msg1(user), msg2(assistant), ..., msgN-1(user)]

Step B: 判斷是否需要 Compact
        total_tokens = sum(msg.token_count for msg in messages)
        if total_tokens > COMPACT_THRESHOLD:
            → 觸發 Compact，壓縮舊訊息為摘要

Step C: 組裝送入 RAG-Anything 的 history_messages
        [
          {"role": "system", "content": "你是一個知識庫助理..."},
          {"role": "assistant", "content": "<compact_summary>"},  ← 若已 Compact
          {"role": "user", "content": msg1.content},
          {"role": "assistant", "content": msg2.content},
          ...最近 COMPACT_TARGET 輪對話
          {"role": "user", "content": "（當前這句提問）"}
        ]

Step D: 呼叫 RAG-Anything aquery()，傳入 history_messages
Step E: 儲存本輪 user message + assistant response 至 DB
```

### Compact 壓縮設計

```
觸發條件：
  messages.length >= COMPACT_THRESHOLD (預設 15 條)

壓縮策略（Sliding Window + Summary）：
  1. 取最舊的 (total - COMPACT_TARGET) 條訊息
  2. 呼叫 LLM 將這些訊息摘要為 1 段 "對話摘要"
  3. 刪除這些舊訊息，改在 DB 中插入一條 role="system"、
     is_compacted_summary=True 的摘要訊息
  4. 更新 chat_sessions.compact_summary 與 is_compacted=True
  5. 保留最近 COMPACT_TARGET 條訊息繼續使用

結果：history_messages 長度始終控制在 COMPACT_TARGET + 1 (摘要) 以內
```

### Checklist

- [ ] **建立 `rag/conversation_compactor.py`：ConversationCompactor**
  ```python
  class ConversationCompactor:
      """
      負責將過長的對話歷史壓縮為摘要，避免 LLM context 超限。
      """
      COMPACT_PROMPT_TEMPLATE: str = """
      以下是一段對話的歷史紀錄，請將其整理成一段簡潔的摘要，
      保留所有重要的問題、答案與關鍵資訊，以繁體中文回答：

      {conversation_history}

      請以「對話摘要：」開頭，輸出摘要內容。
      """

      def __init__(
          self,
          llm_adapter: OllamaLLMAdapter,
          compact_threshold: int = 15,
          compact_target: int = 6
      )

      def should_compact(self, message_count: int) -> bool
          # message_count >= compact_threshold → True

      async def compact(
          self,
          messages: list[Message],
          keep_last_n: int
      ) -> tuple[str, list[Message]]
          """
          輸入: 完整 messages list
          輸出: (summary_text, messages_to_keep)
          - summary_text: LLM 生成的壓縮摘要
          - messages_to_keep: 保留的最近 keep_last_n 條訊息
          """
          # 1. 取出需壓縮的舊訊息（messages[:-keep_last_n]）
          # 2. 格式化為純文字對話
          # 3. 呼叫 llm_adapter.complete(compact_prompt)
          # 4. 回傳 (summary, messages[-keep_last_n:])

      def estimate_tokens(self, text: str) -> int
          # 簡易估算：len(text) // 3 (中文約 1 char ≈ 0.5 token，英文約 4 chars/token)
  ```

- [ ] **建立 `services/conversation_service.py`：ConversationService**
  ```python
  class ConversationService:
      """
      管理單一 session 的多輪對話狀態，
      負責 context 組裝、Compact 觸發、訊息持久化。
      """
      def __init__(
          self,
          session_repo: SessionRepository,
          message_repo: MessageRepository,
          compactor: ConversationCompactor
      )

      async def get_conversation_context(
          self,
          session_id: UUID,
          current_question: str
      ) -> list[dict]
          """
          組裝送入 LLM 的 history_messages。
          流程：
          1. 從 DB 取出最近 COMPACT_THRESHOLD 條訊息
          2. 判斷是否需要 Compact，若需要則先執行 Compact
          3. 組裝 [system_msg, summary_msg(optional), ...history, user_msg]
          4. 回傳 history_messages list
          """

      async def save_user_message(
          self,
          session_id: UUID,
          content: str,
          query_mode: str
      ) -> Message
          # 建立 role="user" 的 Message，估算 token_count

      async def save_assistant_message(
          self,
          session_id: UUID,
          content: str,
          rag_sources: list[str] | None = None
      ) -> Message
          # 建立 role="assistant" 的 Message
          # 同步更新 session.last_message_at 與 message_count

      async def _execute_compact(
          self,
          session_id: UUID,
          messages: list[Message]
      ) -> str
          """
          1. 呼叫 compactor.compact()
          2. 刪除 DB 中被壓縮的舊訊息
          3. 插入摘要 message（role=system, is_compacted_summary=True）
          4. 更新 session.compact_summary 與 is_compacted=True
          5. 回傳 summary_text
          """

      async def auto_title_session(
          self,
          session_id: UUID,
          first_user_message: str
      ) -> None
          """
          Session 第一條 user message 送出後，
          用前 20 字自動命名 session title（若 title 仍為預設值）
          """
  ```

- [ ] **建立 `services/chat_session_service.py`：ChatSessionService**
  ```python
  class ChatSessionService:
      """
      管理對話視窗的 CRUD 操作。
      """
      def __init__(self, session_repo: SessionRepository, message_repo: MessageRepository)

      async def create_session(self, user_id: UUID, query_mode: str = "hybrid") -> ChatSession
          # title 預設為 "新對話 {datetime}"

      async def list_sessions(
          self,
          user_id: UUID,
          skip: int = 0,
          limit: int = 30
      ) -> list[ChatSession]
          # 按 last_message_at DESC 排序

      async def get_session_with_messages(
          self,
          session_id: UUID,
          user_id: UUID,
          message_limit: int = 50
      ) -> tuple[ChatSession, list[Message]]
          # 驗證 session.user_id == user_id（防止跨用戶存取）

      async def rename_session(
          self, session_id: UUID, user_id: UUID, new_title: str
      ) -> ChatSession

      async def delete_session(self, session_id: UUID, user_id: UUID) -> None
          # 刪除 session，CASCADE 自動刪除 messages
  ```

- [ ] **撰寫 `tests/test_conversation.py`**
  - 測試 `get_conversation_context`：正常 context 組裝
  - 測試 Compact 觸發：訊息數 >= threshold 時自動壓縮
  - 測試 Compact 後 context 長度正確
  - 測試跨輪對話連貫性（mock LLM）
  - 測試 auto_title_session

---

## STEP 5 — 文件上傳與 RAG 處理 API

> 目標：實作文件上傳、背景處理（呼叫 RAG-Anything 解析）、狀態查詢、刪除。

### Checklist

- [ ] **建立 `services/document_service.py`：DocumentService**
  ```python
  class DocumentService:
      """
      負責文件的 CRUD、本地儲存、RAG-Anything 解析觸發。
      """
      ALLOWED_EXTENSIONS: frozenset = frozenset({
          ".pdf", ".docx", ".doc", ".pptx", ".ppt",
          ".xlsx", ".xls", ".md", ".txt", ".jpg", ".jpeg", ".png"
      })
      MAX_FILE_SIZE_MB: int = 50

      def __init__(
          self,
          doc_repo: DocumentRepository,
          rag_engine: RAGAnything,
          upload_dir: Path
      )

      async def validate_file(self, file: UploadFile) -> None
          # 驗證 extension、MIME type、file size

      async def save_file(self, file: UploadFile) -> tuple[str, str, int]
          # 儲存至 upload_dir/{uuid}{ext}
          # 回傳 (stored_filename, file_path, file_size)

      async def create_document_record(
          self,
          original_filename: str,
          stored_filename: str,
          file_path: str,
          file_size: int,
          mime_type: str,
          uploader_id: UUID
      ) -> Document

      async def process_document_background(self, document_id: UUID) -> None
          """
          背景任務（BackgroundTasks）：
          1. 更新 status = "processing"
          2. 呼叫 rag.process_document_complete(file_path, output_dir)
          3. 取得 rag_doc_id 並儲存
          4. 更新 status = "completed"
          5. 失敗時更新 status = "failed" + error_message
          """

      async def list_documents(
          self, user: User, skip: int, limit: int
      ) -> list[Document]
          # Admin → 全部；User → 只看自己的

      async def get_document(self, doc_id: UUID, user: User) -> Document
          # 驗證存取權限

      async def delete_document(self, doc_id: UUID, user: User) -> None
          # 1. 從 ChromaDB 刪除對應向量
          # 2. 刪除本地檔案
          # 3. 刪除 DB record
  ```

- [ ] **建立 `schemas/document.py`**
  ```python
  class DocumentUploadResponse(BaseModel):
      id: UUID
      title: str
      status: str
      created_at: datetime

  class DocumentListResponse(BaseModel):
      id: UUID
      title: str
      original_filename: str
      file_size: int
      mime_type: str
      status: str
      error_message: str | None
      uploaded_by_id: UUID
      created_at: datetime
      updated_at: datetime

  class DocumentStatusResponse(BaseModel):
      id: UUID
      status: str
      error_message: str | None
  ```

- [ ] **建立 `api/v1/documents.py`：Documents Router**
  ```
  POST   /api/v1/documents/upload
          → multipart/form-data (file)
          → 儲存檔案 + 建立 DB record + 觸發背景任務
          → DocumentUploadResponse

  GET    /api/v1/documents/
          → 列出文件（支援 skip/limit pagination）
          → list[DocumentListResponse]

  GET    /api/v1/documents/{doc_id}
          → 單一文件詳情
          → DocumentListResponse

  GET    /api/v1/documents/{doc_id}/status
          → 輪詢解析狀態
          → DocumentStatusResponse

  DELETE /api/v1/documents/{doc_id}
          → 刪除文件（Admin 或上傳者本人）
          → 204 No Content
  ```

- [ ] **撰寫 `tests/test_documents.py`**
  - 測試上傳 PDF 成功 / 格式不允許 / 超過大小限制
  - 測試 status 查詢（pending → processing → completed）
  - 測試 delete（本人 / 他人 / admin）

---

## STEP 6 — 對話視窗 API 與 SSE Streaming 查詢

> 目標：實作對話 Session CRUD API、SSE 串流查詢（整合多輪對話 context），讓前端可以完整操作對話視窗並取得串流回應。

### Checklist

- [ ] **建立 `schemas/session.py`**
  ```python
  class SessionCreateRequest(BaseModel):
      query_mode: str = "hybrid"   # hybrid / local / global / naive

  class SessionResponse(BaseModel):
      id: UUID
      title: str
      query_mode: str
      message_count: int
      last_message_at: datetime | None
      is_compacted: bool
      created_at: datetime

  class SessionListResponse(BaseModel):
      sessions: list[SessionResponse]
      total: int
  ```

- [ ] **建立 `schemas/message.py`**
  ```python
  class MessageResponse(BaseModel):
      id: UUID
      session_id: UUID
      role: str
      content: str
      is_compacted_summary: bool
      rag_sources: list[str] | None
      query_mode: str | None
      created_at: datetime

  class SessionDetailResponse(BaseModel):
      session: SessionResponse
      messages: list[MessageResponse]
  ```

- [ ] **建立 `schemas/query.py`**
  ```python
  class QueryRequest(BaseModel):
      session_id: UUID
      question: str           # min_length=1, max_length=2000
      mode: str = "hybrid"    # hybrid / local / global / naive

  class SSEEvent(BaseModel):
      type: str    # "token" | "done" | "error" | "sources"
      content: str | None = None
      sources: list[str] | None = None
      session_id: str | None = None
      message_id: str | None = None
  ```

- [ ] **建立 `api/v1/sessions.py`：Sessions Router**
  ```
  POST   /api/v1/sessions/
          → SessionCreateRequest
          → SessionResponse（建立新對話視窗）

  GET    /api/v1/sessions/
          → ?skip=0&limit=30
          → SessionListResponse（列出當前用戶所有 session）

  GET    /api/v1/sessions/{session_id}
          → SessionDetailResponse（含最近 50 條 messages）

  PATCH  /api/v1/sessions/{session_id}/title
          → {"title": "新名稱"}
          → SessionResponse

  DELETE /api/v1/sessions/{session_id}
          → 204 No Content（含所有 messages 一起刪除）
  ```

- [ ] **建立 `services/rag_query_service.py`：RAGQueryService**
  ```python
  class RAGQueryService:
      """
      整合 RAG-Anything 查詢、多輪對話 context 組裝、SSE 串流輸出。
      """
      def __init__(
          self,
          rag_engine: RAGAnything,
          llm_adapter: OllamaLLMAdapter,
          conversation_service: ConversationService
      )

      async def query_stream(
          self,
          session_id: UUID,
          question: str,
          mode: str = "hybrid",
          user_id: UUID | None = None
      ) -> AsyncGenerator[str, None]
          """
          核心查詢流程：
          1. 儲存 user message 至 DB
          2. 呼叫 conversation_service.get_conversation_context()
             → 取得含歷史的 history_messages（含 Compact 處理）
          3. 呼叫 rag.aquery(question, mode=mode, history_messages=...)
             → 取得 RAG 增強後的 context
          4. 呼叫 llm_adapter.complete_stream(question, history=context)
             → 逐 token yield
          5. 串流結束後：
             a. 儲存完整 assistant message 至 DB
             b. auto_title_session（若為第一輪）
             c. yield sources SSE event
          6. 串流期間任何錯誤 → yield error SSE event

          SSE 輸出格式：
          data: {"type": "token", "content": "逐"}
          data: {"type": "token", "content": "字"}
          data: {"type": "sources", "sources": ["doc_id_1", ...]}
          data: {"type": "done", "message_id": "uuid"}
          data: {"type": "error", "content": "error message"}
          """
  ```

- [ ] **建立 `api/v1/query.py`：Query Router**
  ```python
  @router.post("/stream")
  async def query_stream(
      request: QueryRequest,
      current_user: User = Depends(get_current_user),
      rag_query_service: RAGQueryService = Depends(...)
  ) -> StreamingResponse:
      """
      SSE endpoint。
      Headers: Content-Type: text/event-stream
               Cache-Control: no-cache
               X-Accel-Buffering: no
      """
      async def event_generator():
          async for sse_data in rag_query_service.query_stream(
              session_id=request.session_id,
              question=request.question,
              mode=request.mode,
              user_id=current_user.id
          ):
              yield f"data: {sse_data}\n\n"
          yield "data: [DONE]\n\n"

      return StreamingResponse(
          event_generator(),
          media_type="text/event-stream"
      )
  ```

- [ ] **撰寫 `tests/test_query.py`**
  - 測試 SSE endpoint 回傳正確 Content-Type
  - 測試 session_id 不存在 → 404
  - 測試未登入 → 401
  - 測試完整一輪問答後 DB 中存在對應 messages

---

## STEP 7 — 前端開發

> 目標：實作所有前端頁面與元件，包含登入/註冊、對話列表側欄、聊天視窗（SSE 串流）、文件上傳、Admin 管理頁。

### Checklist

#### 7.1 型別與 API 客戶端

- [ ] **建立 `types/auth.ts`、`types/session.ts`、`types/message.ts`、`types/document.ts`**
  ```typescript
  // session.ts
  interface ChatSession {
    id: string
    title: string
    queryMode: string
    messageCount: number
    lastMessageAt: string | null
    isCompacted: boolean
    createdAt: string
  }

  // message.ts
  interface Message {
    id: string
    sessionId: string
    role: 'user' | 'assistant' | 'system'
    content: string
    isCompactedSummary: boolean
    ragSources: string[] | null
    createdAt: string
  }
  ```

- [ ] **建立 `lib/api.ts`：Axios Instance + Interceptors**
  - 建立 axios instance，baseURL 設為 `NEXT_PUBLIC_API_URL`
  - 設定 `withCredentials: true` 支援 cookie-based 認證備用
  - Request interceptor：自動附加 `Authorization: Bearer {token}`
  - Response interceptor：401 → 清除 token + redirect `/login`
  - 封裝 auth / session / document / query API 函數

- [ ] **建立 `store/authStore.ts`：Zustand Auth Store**
  ```typescript
  interface AuthStore {
    user: UserPublic | null
    token: string | null
    isLoading: boolean
    login: (email: string, password: string) => Promise<void>
    logout: () => void
    restoreFromStorage: () => void
  }
  ```

- [ ] **建立 `store/chatStore.ts`：Zustand Chat Store**
  ```typescript
  interface ChatStore {
    sessions: ChatSession[]
    currentSessionId: string | null
    messages: Record<string, Message[]>  // sessionId → messages[]
    isStreaming: boolean
    streamingContent: string            // 當前串流中的文字（未完成）

    // Actions
    loadSessions: () => Promise<void>
    createSession: (mode: string) => Promise<ChatSession>
    selectSession: (sessionId: string) => Promise<void>
    deleteSession: (sessionId: string) => Promise<void>
    renameSession: (sessionId: string, title: string) => Promise<void>
    appendStreamToken: (token: string) => void
    finalizeStreamMessage: (msg: Message) => void
    clearStreamingContent: () => void
  }
  ```

#### 7.2 認證頁面

- [ ] **建立 `(auth)/login/page.tsx`**
  - 使用 shadcn/ui：`Card`、`Input`、`Button`、`Form`
  - 表單驗證：react-hook-form + zod schema
  - 登入成功 → 儲存 token → redirect `/chat`
  - 錯誤訊息顯示（帳號不存在 / 密碼錯誤）

- [ ] **建立 `(auth)/signup/page.tsx`**
  - 欄位：email、password（含強度提示）、full_name
  - 成功後 auto-login → redirect `/chat`

- [ ] **建立 `middleware.ts`：Route Guard**
  ```typescript
  // 保護規則：
  // - 未登入 → 導向 /login
  // - 已登入訪問 /login /signup → 導向 /chat
  // - 訪問 /admin/* → 解析 token 確認 role=admin，否則 403
  ```

#### 7.3 Dashboard Layout

- [ ] **建立 `(dashboard)/layout.tsx`**
  - 左側 `SessionSidebar`（固定寬度）
  - 右側 main content area

- [ ] **建立 `components/chat/SessionSidebar.tsx`**
  - 頂部：「+ 新對話」按鈕（選擇 RAG mode：hybrid/local/global）
  - 中間：對話列表，每項顯示 title + last_message_at + message_count
  - 點擊 → 切換到對應 session（`/chat/{sessionId}`）
  - 長按/右鍵選單：重新命名、刪除
  - 底部：用戶資訊 + 登出按鈕

#### 7.4 聊天主頁面

- [ ] **建立 `chat/page.tsx`（無 session 時的預設頁）**
  - 顯示歡迎畫面
  - 提示「選擇一個對話」或「建立新對話」

- [ ] **建立 `chat/[sessionId]/page.tsx`**
  - 載入 session + messages 資料
  - 渲染 `ChatWindow`

- [ ] **建立 `components/chat/ChatWindow.tsx`**
  - 接收 sessionId，從 chatStore 取出 messages
  - 渲染 `MessageBubble` list（自動捲動至底部）
  - 底部渲染 `InputBar`
  - 串流進行中時顯示 loading indicator

- [ ] **建立 `components/chat/MessageBubble.tsx`**
  - user message：右對齊，藍色氣泡
  - assistant message：左對齊，灰色氣泡，支援 Markdown 渲染（react-markdown）
  - 若 `is_compacted_summary=true`：顯示「📝 對話摘要」標籤
  - 若有 `rag_sources`：顯示可展開的「參考來源」區塊

- [ ] **建立 `components/chat/StreamingText.tsx`**
  - 顯示串流中逐字出現的文字
  - 顯示 cursor 動畫（blinking）

- [ ] **建立 `components/chat/InputBar.tsx`**
  - `Textarea`（Enter 送出，Shift+Enter 換行）
  - 送出按鈕（串流中禁用）
  - 顯示當前 session 的 query mode

- [ ] **建立 `hooks/useSSEStream.ts`**
  ```typescript
  interface UseSSEStreamOptions {
    onToken: (token: string) => void
    onDone: (messageId: string, sources: string[]) => void
    onError: (error: string) => void
  }

  const useSSEStream = (options: UseSSEStreamOptions) => {
    const stream = async (sessionId: string, question: string, mode: string) => {
      // 1. fetch POST /api/v1/query/stream（帶 JWT）
      // 2. 使用 ReadableStream API 逐行讀取 SSE
      // 3. 解析 data: {...} 格式
      // 4. 依 type 分派：token → onToken, done → onDone, error → onError
    }
    return { stream, isStreaming }
  }
  ```

- [ ] **建立 `hooks/useChatSession.ts`**
  ```typescript
  // 封裝 session CRUD 操作
  // 對應 chatStore 的 actions
  const useChatSession = () => {
    return {
      sessions, currentSessionId,
      createSession, deleteSession, renameSession,
      loadMessages
    }
  }
  ```

#### 7.5 文件管理頁面

- [ ] **建立 `documents/page.tsx`**
  - 上半：`UploadZone` 拖拉上傳區
  - 下半：`DocumentList` 文件列表

- [ ] **建立 `components/documents/UploadZone.tsx`**
  - 使用 react-dropzone
  - 支援多檔同時上傳
  - 顯示允許格式（PDF, DOCX, PPTX, XLSX, MD, TXT, JPG, PNG）
  - 上傳進度條

- [ ] **建立 `components/documents/DocumentList.tsx`**
  - 顯示 title、filename、size、status（帶顏色標籤）、上傳時間
  - status = "processing" 時自動每 3 秒 polling `/status`
  - 刪除按鈕（confirm dialog）

#### 7.6 Admin 頁面

- [ ] **建立 `admin/users/page.tsx`**
  - 表格列出所有用戶（email, name, role, is_active, created_at）
  - 角色切換按鈕（admin ↔ user）
  - 啟用/停用帳號按鈕

- [ ] **建立 `admin/documents/page.tsx`**
  - 顯示所有用戶上傳的文件
  - 可按上傳者篩選
  - Admin 可刪除任何文件

---

## STEP 8 — Docker 容器化

> 目標：完成 Backend / Frontend Dockerfile，撰寫 docker-compose.yml，確保一鍵 `docker-compose up -d` 可啟動所有服務。

### Checklist

- [ ] **建立 `backend/Dockerfile`（Multi-stage）**
  ```dockerfile
  FROM python:3.11-slim AS base

  # 系統依賴：LibreOffice（Office 文件解析）、libGL（MinerU 需要）
  RUN apt-get update && apt-get install -y \
      libreoffice libgl1-mesa-glx libglib2.0-0 \
      curl && rm -rf /var/lib/apt/lists/*

  # 安裝 uv
  RUN pip install uv

  WORKDIR /app
  COPY pyproject.toml uv.lock ./
  RUN uv sync --frozen --no-dev

  COPY . .

  # 建立必要目錄
  RUN mkdir -p /app/uploads /app/rag_storage /app/data

  CMD ["sh", "-c", \
    "uv run alembic upgrade head && \
     uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
  ```

- [ ] **建立 `frontend/Dockerfile`（Multi-stage）**
  ```dockerfile
  FROM node:20-alpine AS deps
  WORKDIR /app
  # 啟用 Corepack 以使用專案指定的 yarn 版本
  RUN corepack enable
  COPY package.json yarn.lock .yarnrc.yml* ./
  RUN yarn install --frozen-lockfile

  FROM node:20-alpine AS builder
  WORKDIR /app
  RUN corepack enable
  COPY --from=deps /app/node_modules ./node_modules
  COPY . .
  ENV NEXT_TELEMETRY_DISABLED=1
  RUN yarn build

  FROM node:20-alpine AS runner
  WORKDIR /app
  ENV NODE_ENV=production
  ENV NEXT_TELEMETRY_DISABLED=1
  COPY --from=builder /app/.next/standalone ./
  COPY --from=builder /app/.next/static ./.next/static
  COPY --from=builder /app/public ./public
  CMD ["node", "server.js"]
  ```

- [ ] **建立 `docker-compose.yml`**
  ```yaml
  version: '3.9'

  services:
    frontend:
      build: ./frontend
      ports: ["3000:3000"]
      environment:
        - NEXT_PUBLIC_API_URL=http://backend:8000
      depends_on:
        backend:
          condition: service_healthy

    backend:
      build: ./backend
      ports: ["8000:8000"]
      env_file: .env
      healthcheck:
        test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
        interval: 10s
        timeout: 5s
        retries: 5
      volumes:
        - ./data/uploads:/app/uploads
        - ./data/rag_storage:/app/rag_storage
        - ./data/db:/app/data
        - ./data/hf_cache:/root/.cache/huggingface   # bge-m3 model cache
      depends_on:
        chromadb:
          condition: service_healthy
        ollama:
          condition: service_started

    chromadb:
      image: chromadb/chroma:latest
      ports: ["8001:8000"]
      volumes:
        - ./data/chromadb:/chroma/chroma
      healthcheck:
        test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
        interval: 10s
        timeout: 5s
        retries: 5

    ollama:
      image: ollama/ollama:latest
      ports: ["11434:11434"]
      volumes:
        - ./data/ollama:/root/.ollama
      # 同一個 Ollama service 同時承載 gpt-oss:latest（LLM）與 llava:7b（Vision）
      # GPU 支援（需安裝 nvidia-container-toolkit，預設關閉）：
      # deploy:
      #   resources:
      #     reservations:
      #       devices:
      #         - driver: nvidia
      #           count: all
      #           capabilities: [gpu]
  ```

- [ ] **建立 `docker-compose.dev.yml`（本地開發覆寫）**
  ```yaml
  # 使用方式: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
  services:
    backend:
      volumes:
        - ./backend:/app          # hot reload
      command: >
        sh -c "uv run alembic upgrade head &&
               uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    frontend:
      volumes:
        - ./frontend/src:/app/src  # hot reload
  ```

- [ ] **建立 `scripts/init-ollama.sh`**
  ```bash
  #!/bin/bash
  # 在 docker-compose up 後執行，拉取所需的兩個模型
  echo "⏳ Waiting for Ollama to be ready..."
  until curl -sf http://localhost:11434/api/tags > /dev/null; do sleep 3; done
  echo "✅ Ollama is ready"

  echo "📥 Pulling gpt-oss:latest（文字推理 / 對話 LLM）..."
  docker exec rag-platform-ollama-1 ollama pull gpt-oss:latest

  echo "📥 Pulling llava:7b（文件圖片 Vision Model）..."
  docker exec rag-platform-ollama-1 ollama pull llava:7b

  echo "✅ All models ready!"
  echo "   - gpt-oss:latest → 文字對話、多輪推理、Compact 摘要"
  echo "   - llava:7b       → 文件圖片 caption（RAG-Anything vision_model_func）"
  ```

- [ ] **建立 `backend/app/main.py` 中的 `/health` endpoint 與 CORS 設定**
  ```python
  from fastapi.middleware.cors import CORSMiddleware

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000"],  # dev；prod 改為實際網域
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  @app.get("/health")
  async def health_check():
      return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
  ```

- [ ] **本地測試驗證**
  - 執行 `docker-compose build` 確認無錯誤
  - 執行 `docker-compose up -d` 確認所有服務啟動
  - 驗證 health check endpoint
  - 驗證 Ollama 模型可呼叫

---

## STEP 9 — README.md 撰寫

> 目標：撰寫完整的專案說明文件，包含 Setup Instructions、Hardware Requirements、AI Tool Usage。

### Checklist

- [ ] **專案說明與架構概覽**
  - 系統功能概述（1 段落）
  - 技術棧表格
  - 架構圖（ASCII）

- [ ] **Setup Instructions（詳細步驟）**
  ```markdown
  ## 快速啟動

  ### 前置需求
  - Docker >= 24.0 & Docker Compose >= 2.20
  - Git
  - （可選）NVIDIA GPU + nvidia-container-toolkit（加速 Ollama 推理）

  ### 步驟

  1. Clone 專案
     git clone <repo-url> && cd rag-platform

  2. 複製並設定環境變數
     cp .env.example .env
     # 必改：將 SECRET_KEY 改為 32 字元以上的隨機字串

  3. 啟動所有服務
     docker-compose up -d

  4. 等待服務就緒（約 1-2 分鐘）
     docker-compose ps    # 確認所有服務為 healthy

  5. 拉取 Ollama 模型（首次必須執行，約 10-20 分鐘）
     bash scripts/init-ollama.sh
     # 會依序拉取：
     #   gpt-oss:latest (~4-8 GB) — 文字對話 LLM
     #   llava:7b       (~4.1 GB) — 文件圖片 Vision Model

  6. 建立第一個 Admin 帳號
     docker exec rag-platform-backend-1 uv run python scripts/create_admin.py

  7. 開啟瀏覽器
     http://localhost:3000

  ### 停止服務
  docker-compose down

  ### 完整清除（含資料）
  docker-compose down -v
  rm -rf data/
  ```

- [ ] **Hardware Requirements 表格**
  ```
  | 項目         | 最低需求              | 建議配置           |
  |-------------|----------------------|-------------------|
  | RAM          | 16 GB                | 32 GB             |
  | VRAM (GPU)   | 12 GB (NVIDIA)       | 24 GB             |
  |              | ★ 無 GPU 可 CPU 運行  | (速度較慢)         |
  | CPU          | 4 核心               | 8 核心以上         |
  | 儲存空間      | 40 GB                | 80 GB             |
  | OS           | Ubuntu 22.04         | Ubuntu 22.04      |

  模型佔用空間（同一個 Ollama service 載入）：
  - gpt-oss:latest:  ~4-8 GB VRAM（文字對話 LLM）
  - llava:7b:        ~4.1 GB VRAM（文件圖片 Vision，僅文件解析時載入）
  - BAAI/bge-m3:     ~2.4 GB RAM（HuggingFace Embedding，CPU 即可）
  - MinerU 模型:     ~5-8 GB 磁碟（首次下載）

  ⚠️ 注意：gpt-oss 與 llava:7b 不會同時載入 VRAM。
  Ollama 採用 lazy loading，文件解析時載 llava:7b，
  對話時載 gpt-oss，兩者輪流使用同一塊 VRAM。
  12 GB VRAM 可應付兩個模型分時使用的情境。
  ```

- [ ] **AI Tool Usage 說明**
  ```markdown
  ## AI 工具使用說明

  本專案開發全程使用 **Claude Code** 作為主要 AI Coding 輔助工具。

  ### 使用環節說明：

  **1. 架構設計與 Boilerplate 生成**
  - FastAPI 專案骨架（Router/Service/Repository 分層）
  - SQLAlchemy 2.0 Async ORM models（含 UUID PK、TimestampMixin）
  - Pydantic v2 schemas 設計
  - Next.js App Router 頁面結構

  **2. RAG-Anything 整合**
  - Ollama LLM adapter（gpt-oss）實作，符合 llm_model_func 簽名
  - Ollama Vision adapter（llava:7b）實作，符合 vision_model_func 三段式邏輯
    （messages mode / image_data mode / fallback to llm）
  - BAAI/bge-m3 embedding 封裝（lazy loading + asyncio executor）
  - ChromaDB vector storage adapter（符合 LightRAG 向量儲存介面）

  **3. 多輪對話 Compact 機制**
  - ConversationService context 組裝邏輯
  - ConversationCompactor sliding window + LLM 摘要策略
  - token 估算演算法

  **4. SSE Streaming**
  - FastAPI StreamingResponse + SSE 事件格式
  - React useSSEStream hook（ReadableStream API）
  - 串流中斷錯誤處理

  **5. Docker 配置**
  - Multi-stage Dockerfile（backend/frontend）
  - docker-compose healthcheck 設計
  - GPU 選用設定

  **6. Debug 與問題排解**
  - SQLAlchemy async session scoping 問題
  - ChromaDB 首次連線重試邏輯
  - CORS 設定（FastAPI + Next.js）
  - Alembic async migration 設定
  ```

---

## STEP 10 — 整合測試與最終驗證

> 目標：端對端驗證所有功能正常運作，確保 Docker 部署無誤，進行最終提交。

### Checklist

- [ ] **後端 API 整合測試**
  - 執行完整測試套件：`uv run pytest tests/ -v --tb=short`
  - 所有測試通過率 ≥ 80%
  - 確認無 SQLAlchemy session leak

- [ ] **端對端功能驗證（手動）**
  - [ ] 用戶 Signup → Login → 取得 JWT
  - [ ] 上傳純文字 PDF → 等待 status = "completed"
  - [ ] 上傳含圖片的 PDF → 確認 llava:7b 被呼叫，圖片描述存入 ChromaDB
  - [ ] 建立新 Session → 輸入問題 → 確認 SSE 串流正常回應
  - [ ] 對話超過 15 輪 → 確認 Compact 觸發（DB 中出現 is_compacted_summary=True 的 message）
  - [ ] 切換不同 Session → 確認各 Session 歷史獨立
  - [ ] 重新整理頁面 → 確認 Session 列表與訊息從 DB 正確載入
  - [ ] Admin 登入 → 查看所有 User 與所有 Document
  - [ ] Admin 刪除他人上傳的文件

- [ ] **Docker 部署驗證**
  - 完整執行 `docker-compose build && docker-compose up -d`
  - 確認所有 healthcheck 通過
  - 確認 Ollama 模型可正常呼叫
  - 測試 ChromaDB 向量寫入與查詢
  - 測試前端能正常存取後端 API

- [ ] **效能基準驗證**
  - 單次查詢回應時間（不含首次模型載入）< 30 秒（CPU 模式）
  - 文件上傳後解析完成時間（PDF 10 頁）< 5 分鐘

- [ ] **GitHub Repository 整理**
  - 確認 `.gitignore` 涵蓋：`.env`、`data/`、`__pycache__`、`.next`、`node_modules`、`package-lock.json`（使用 yarn，不應存在 npm lock 檔）
  - 確認 `data/` 目錄不包含任何真實資料
  - 最終 commit message：`release: v1.0.0 final submission`
  - 確認 README.md 完整無誤
  - 推送至 GitHub Public Repository

---

## ⚠️ 關鍵技術挑戰與應對策略

### 挑戰 1：RAG-Anything 預設使用 OpenAI API
**問題**：框架範例程式碼使用 `openai_complete_if_cache` 與 `gpt-4o` 做 vision  
**策略**：
- `llm_model_func` → `OllamaLLMAdapter(model="gpt-oss:latest")` 負責文字推理
- `vision_model_func` → `OllamaVisionAdapter(model="llava:7b")` 負責文件圖片 caption
- `vision_model_func` 實作三段式邏輯（參考社群實作確認的正確簽名）：
  ```python
  if messages:      # VLM Enhanced Query → 直接送 llava:7b
  elif image_data:  # 單張圖片 → 組裝 base64 image_url 送 llava:7b
  else:             # Fallback 純文字 → 委派 gpt-oss
  ```

### 挑戰 2：ChromaDB 作為 LightRAG 向量後端
**問題**：LightRAG 預設使用自己的 nano-vectordb  
**策略**：實作 `ChromaVectorStorage` 符合 LightRAG 的 `BaseVectorStorage` 介面，或利用 RAG-Anything 的 `working_dir` 將中間產物存至本地後再同步至 ChromaDB

### 挑戰 3：多輪對話 context 注入 RAG-Anything
**問題**：RAG-Anything 的 `aquery()` 接受 `history_messages` 參數，需要正確組裝格式  
**策略**：`ConversationService.get_conversation_context()` 組裝標準 OpenAI chat format 的 messages list，直接傳入 `aquery(history_messages=...)`

### 挑戰 4：Compact 後對話連貫性
**問題**：壓縮後 LLM 是否能理解摘要並繼續有意義地回答  
**策略**：Compact 摘要以 `role="system"` 方式注入，位於 history 最前面，讓 LLM 先讀取背景再回答；同時保留最近 6 輪完整對話提供連貫性

### 挑戰 5：BAAI/bge-m3 首次下載速度
**問題**：首次啟動需從 HuggingFace 下載約 2.4 GB 模型  
**策略**：docker-compose 設定 `./data/hf_cache:/root/.cache/huggingface` volume，下載一次後快取在本地，後續重啟不需重新下載

### 挑戰 6：SQLite Async + Alembic
**問題**：SQLAlchemy async 需要 aiosqlite driver，Alembic 需要特殊設定  
**策略**：`DATABASE_URL` 使用 `sqlite+aiosqlite:///`，`alembic/env.py` 使用 `run_async_migrations()` 模式

---

## 📝 CLAUDE.md 規範（完整版）

```markdown
# RAG Platform Development Standards v1.2

## 架構分層規則（嚴格遵守）
Router → Service → Repository → ORM Model
Schema (Pydantic) 只在 Router 層做 request/response 轉換
Service 層不能直接存取 DB，必須透過 Repository
Router 層不能有業務邏輯，只做 HTTP 格式轉換

## OOP 設計規則
- 所有 Service、Repository、Adapter 必須使用 class，禁止 standalone function 作為業務邏輯
- Repository 繼承 BaseRepository[T]
- 建構子注入依賴（Constructor Injection），禁止全域變數
- RAG adapters 統一透過 RAGEngine 單例管理

## Clean Code 規則
- 所有 public method 必須有完整 type hints（含回傳型態）
- 所有 class 必須有 docstring（說明職責）
- 所有 magic number 抽取為 class constant 或 config
- 函數長度上限：50 行；class 長度上限：200 行
- 禁止 bare except，必須捕捉具體例外類型

## 多輪對話規則
- 所有歷史訊息操作只能透過 ConversationService
- Compact 邏輯只能在 ConversationCompactor 中
- 不允許在 Router 或其他 Service 直接查詢 messages 表

## 錯誤處理規則
- 使用 core/exceptions.py 中定義的自訂例外
- 禁止在 Router 層 try/catch，統一由 global handler 處理
- 錯誤 log 使用 Python logging，禁止 print()

## 前端套件管理規則
- **統一使用 yarn**，禁止在 frontend/ 目錄下執行任何 npm 指令
- 新增套件：`yarn add <pkg>`；開發依賴：`yarn add -D <pkg>`
- 執行腳本：`yarn dev`、`yarn build`、`yarn lint`
- 禁止 commit `package-lock.json`（已加入 .gitignore）
- `yarn.lock` 必須 commit，確保環境一致性

## Git Convention
- feat/xxx、fix/xxx、refactor/xxx、docs/xxx
- 每個 Step 完成後必須 commit
- commit message 格式：feat(scope): description

## Testing 規則
- 每個 Service 的 public method 需要對應 unit test
- 使用 pytest-asyncio for async tests
- Mock 外部依賴（Ollama、ChromaDB）使用 pytest-mock
- 測試覆蓋率目標 ≥ 70%
```

---

*計畫書版本: v2.1 | 基於 RAG-Anything v1.2.9 | 適用 Claude Code 開發*  
*新增：多輪對話管理、Compact 壓縮機制、對話 Session 儲存、完整 Step Checklist*  
*v2.1 更新：雙模型架構（gpt-oss LLM + llava:7b Vision）、Hardware Requirements 修正*
