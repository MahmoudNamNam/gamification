from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import init_db
from app.core.errors import AppError
from app.routers import auth, users, categories, admin_questions, admin_media, matches, wallet, products, purchases

app = FastAPI(
    title="خليجي API",
    description="Gulf-themed quiz game backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(AppError)
def app_error_handler(request, exc: AppError):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(admin_questions.router)
app.include_router(admin_media.router)
app.include_router(matches.router)
app.include_router(wallet.router)
app.include_router(products.router)
app.include_router(purchases.router)


@app.get("/health")
def health():
    return {"status": "ok"}
