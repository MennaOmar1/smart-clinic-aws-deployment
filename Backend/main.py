from dotenv import load_dotenv
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from services.llm_service import LLMService
load_dotenv()
import os
from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from api.routes import (
    auth, google_auth, admin, appointments,
    protected, doctor, auth_refresh, chatbot, elevenlabs
)
from core.database import Base, engine
from core.scheduler import start_scheduler
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from core.database import Base, engine

#Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_SECRET_KEY = os.getenv(
    "SESSION_SECRET_KEY",
    "supersecretkey123456"
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    same_site="lax",
    https_only=False
)

# =========================
# DATABASE INIT (SAFE)
# =========================
@app.on_event("startup")
def startup_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database connected & tables created")
    except Exception as e:
        print("❌ Database connection failed:", e)


# ensure optional column exists for existing DBs
with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS google_token TEXT"
    ))
    conn.commit()

from api.routes.google_auth import router as google_router

app.include_router(google_router)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
#app.include_router(google_auth.router, prefix="/auth", tags=["Google Auth"])
app.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(protected.router)
app.include_router(doctor.router, prefix="/doctor")
app.include_router(auth_refresh.router)
app.include_router(chatbot.router, prefix="/chatbot")
app.include_router(elevenlabs.router)

# =========================
# HOME
# =========================
@app.get("/")
def home():
    return {"message": "API running"}


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
    
# =========================
# SCHEDULER (SAFE START)
# =========================
scheduler = BackgroundScheduler()

@app.on_event("startup")
def startup():

    start_scheduler()

# =========================
# ENV VARS
# =========================
API_KEY = os.getenv("GEMINI_API_KEY")

if os.getenv("ENV") == "dev":
    print("Gemini key loaded (dev mode)")
    
