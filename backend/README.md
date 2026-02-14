# خليجي (Khaleeji) – Backend

Production-ready FastAPI backend for the Gulf-themed quiz game "خليجي". Uses MongoDB, JWT auth, and round-based monetization.

## Tech stack

- **FastAPI** + Pydantic for request/response models
- **MongoDB** with PyMongo (sync)
- **JWT** access tokens + bcrypt password hashing
- **OpenAPI** docs at `/docs` (Swagger) and `/redoc`
- **CORS** enabled (configurable origins)
- Clean layout: **routers** / **services** / **models** / **core**

## Game flow (judge-based, no answers)

1. **Match start**: User selects up to **6 categories** and optional team names / timer. Match is created with status `active`.
2. **Per question**: User chooses **category + level** (L1, L2, L3). System returns the next **unused** question for that category+level (max **2 questions per category per level**). Timer runs.
3. **After timer**: User (judge) selects who answered correctly: **TEAM_A**, **TEAM_B**, or **NO_ONE**. Scores are updated (L1=100, L2=200, L3=500).
4. **Finish**: User clicks "finish round". Backend marks match `finished`, returns **scores**, **winner** (or draw), and **summary** (teamA_correct, teamB_correct, no_one, total_rounds).

Error responses use a consistent shape: `{ "error": { "code": "...", "message": "...", "details": {} } }`.

## Local run

1. **Python 3.11+** and a running **MongoDB** instance (e.g. `mongod` on `localhost:27017`).

2. Create a virtualenv and install dependencies:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Optional: create a `.env` in `backend/`:

   ```
   MONGODB_URI=mongodb://localhost:27017
   MONGODB_DB_NAME=khaleeji
   JWT_SECRET=your-secret-key
   CORS_ORIGINS=http://localhost:3000,http://localhost:8000
   # OTP (optional): RETURN_OTP_IN_RESPONSE=true in dev to get OTP in request-otp response
   ```

4. Run the API:

   ```bash
   uvicorn app.main:app --reload
   ```

   API: `http://localhost:8000`  
   Swagger: `http://localhost:8000/docs`  
   ReDoc: `http://localhost:8000/redoc`

5. Seed categories and sample questions (run once):

   ```bash
   python -m scripts.seed
   ```

   Ensure `MONGODB_URI` and `MONGODB_DB_NAME` match your app.

6. If you have **old questions** (with `answers` / `correct`), run the migration once:

   ```bash
   python -m scripts.migrate_questions_to_no_answers
   ```

## Docker Compose

From the `backend/` directory:

```bash
docker compose up --build
```

- **MongoDB**: `localhost:27017`
- **API**: `http://localhost:8000`

To seed when using Docker:

```bash
docker compose exec api python -m scripts.seed
```

## Tests

```bash
cd backend
pip install -r requirements.txt
# Ensure MongoDB is running (e.g. local or docker)
export MONGODB_DB_NAME=khaleeji_test   # optional: use a test DB
pytest tests/ -v
```

Tests cover: create match with &gt;6 categories (400), next-question quota (409 on 3rd per category+level), judging updates scores and rejects double-judge (409), finish returns winner/draw and summary.

## API overview

- **Auth**: Register with full name, email, password: `POST /auth/register` (body: `{ "name", "email", "password" }` → sends OTP). Then enter OTP: `POST /auth/verify-otp/register` (body: `{ "email", "otp" }` → token). Login: `POST /auth/login`; forgot: `POST /auth/forgot-password`; OTP: `POST /auth/request-otp`, `POST /auth/verify-otp/login`, `POST /auth/verify-otp/forgot-password`
- **User**: `GET /me`, `PATCH /me`
- **Categories**: `GET /categories`
- **Admin** (requires `is_admin` user): `POST /admin/questions`, `GET /admin/questions` (filters: `category_id`, `level`, `status`), `PATCH /admin/questions/{id}`, `DELETE /admin/questions/{id}`; `POST /admin/media/upload`, `GET /admin/media/files/{file_id}`

  **Create or promote an admin user:**
  ```bash
  python -m scripts.create_admin admin@example.com
  python -m scripts.create_admin admin@example.com mypassword   # set password when creating new user
  ```
  After seeding (`python -m scripts.seed`), you can also log in as `admin@example.com` or `demo@example.com` (password: `password123`) — both are admins.
- **Matches**:
  - `POST /matches` – body: `selected_category_ids` (≤6), `teamA_name`, `teamB_name`, `timer_seconds?`
  - `GET /matches`, `GET /matches/{id}`, `DELETE /matches/{id}`
  - `POST /matches/{id}/next-question` – body: `category_id`, `level` (1|2|3)
  - `POST /matches/{id}/judge` – body: `round_no`, `judge_selection` (TEAM_A | TEAM_B | NO_ONE)
  - `POST /matches/{id}/finish` – finalize match, returns scores, winner, summary
  - `PATCH /matches/{id}/teams` – optional team names/avatars
- **Wallet**: `GET /wallet`, `POST /purchases/round-pack`, `POST /wallet/consume-round`

## Data model (summary)

- **categories**: `_id`, `name_ar`, `name_en`, `icon_url`, `active`, `order`
- **questions**: `_id`, `category_id`, `level` (1|2|3), `points` (100|200|500), `prompt` (text + media), `hint` (enabled + content), `status`; no answers
- **matches**: `_id`, `created_by_user_id`, `mode`, `status`, `selected_category_ids`, `teams`, `settings`, `progress.usage` (per category+level used question ids), `rounds` (round_no, category_id, level, question_id, judge_selection, scored_team, scored_points), `finished_at`, timestamps
