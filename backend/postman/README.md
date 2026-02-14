# Postman – خليجي API

## Import options

### 1. Import this collection (recommended)

1. Open Postman → **Import** → **Upload Files** or **Link**.
2. Select `Khaleeji-API.postman_collection.json`.
3. Set variables in the collection:
   - **base_url**: `http://127.0.0.1:8000` (or your API URL).
   - **access_token**: Paste the token after **Login** or **Register** (or set in Auth tab).
   - **match_id** / **category_id**: Optional; set after creating a match or picking a category.

The collection uses **Bearer Token** auth by default. If `access_token` is set, it is sent on all requests. For **Auth** and **Health** you can use “No Auth” on the request if needed.

### 2. Import from OpenAPI (Swagger)

With the API running:

1. Postman → **Import** → **Link**.
2. Enter: `http://127.0.0.1:8000/openapi.json`
3. Postman will generate a collection from the OpenAPI spec. You may still want to set a base URL and token in variables.

## Quick flow

1. **Health** → GET `/health`
2. **Auth** → **Register** with full name, email, password → OTP sent to email → **Verify OTP (register)** with email + OTP → copy `access_token`. Or **Login** (or **Request OTP** → **Verify OTP (login)**).
3. **Categories** → **List categories** → copy a category `id` into `category_id`.
4. **Matches** → **Create match** (use `category_id`) → copy match `id` into `match_id`.
5. **Matches** → **Next question** (use `category_id`, `level`: 1, 2, or 3).
6. **Matches** → **Judge round** (use `round_no` from next-question response, `judge_selection`: TEAM_A | TEAM_B | NO_ONE).
7. **Matches** → **Finish match** when done.

## Error responses

All errors use this shape:

```json
{
  "error": {
    "code": "STRING",
    "message": "...",
    "details": {}
  }
}
```

Common codes: `MAX_CATEGORIES_EXCEEDED`, `NO_QUESTIONS_LEFT_FOR_LEVEL`, `LEVEL_QUOTA_EXCEEDED`, `ROUND_ALREADY_JUDGED`, `MATCH_NOT_FOUND`, `UNAUTHORIZED`, `INVALID_OTP`, `OTP_EXPIRED`.

### Registration (OTP to verify email)

- **Register**: `POST /auth/register` with `{ "name", "email", "password" }` → sends OTP to email (no account created yet).
- **Enter OTP**: `POST /auth/verify-otp/register` with `{ "email", "otp" }` → creates account and returns token (user enters app).

### OTP flow (login / forgot password)

- **Request OTP**: `POST /auth/request-otp` with `{ "email", "purpose": "register" | "login" | "forgot_password" }`.
- **Verify OTP (login)**: `POST /auth/verify-otp/login` with `{ "email", "otp" }` → returns token.
- **Verify OTP (forgot password)**: `POST /auth/verify-otp/forgot-password` with `{ "email", "otp", "new_password" }` → sets password and returns token.

Set `RETURN_OTP_IN_RESPONSE=true` in env to get the OTP in the register/request-otp response (dev only).
