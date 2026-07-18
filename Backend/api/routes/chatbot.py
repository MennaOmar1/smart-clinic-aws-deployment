from fastapi import APIRouter, Request, Response
import uuid
import httpx
import asyncio

from services.session_service import SessionService
from schemas.chatbot import ChatRequest

router = APIRouter(tags=["Chatbot"])

RAG_URL = "https://egypt-medical-api-production.up.railway.app/chat"


# =========================
# RAG CALL WITH RETRY
# =========================
async def call_rag(payload):
    retries = 3
    timeout = 60.0
    print("RAG REQUEST:", payload)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(retries):
            try:
                response = await client.post(
                    RAG_URL,
                    json=payload
                )
                
                print("RAG STATUS:", response.status_code)
                print("RAG BODY:", response.text)
                
                
                response.raise_for_status()

                return response.json()

            except (httpx.ReadTimeout, httpx.ConnectError) as e:
                print(f"RAG ERROR (attempt {attempt + 1}): {e}")

            except Exception as e:
                print(f"RAG UNKNOWN ERROR: {e}")
                break

            await asyncio.sleep(1)

    return None


# =========================
# MEDICAL CHATBOT
# =========================
@router.post("/")
async def chat(
    request: Request,
    response: Response,
    payload: ChatRequest
):
    try:

        message = payload.message.strip()

        user_id = (
            payload.user_id
            or request.cookies.get("chatbot_user_id")
            or str(uuid.uuid4())
        )

        # =========================
        # SESSION
        # =========================
        session = SessionService.get_or_create(user_id)

        session.setdefault("history", [])
        session.setdefault("current_complaint", None)
        session.setdefault("state", "medical_assessment")

        history = session["history"][-6:]


        # =========================
        # NEW MEDICAL COMPLAINT
        # =========================

        current_complaint = session.get("current_complaint")

        if current_complaint is None:

            # أول شكوى
            session["current_complaint"] = message
        else:
            complaint_keywords = [
                "pain",
                "headache",
                "eye",
                "stomach",
                "chest",
                "rash",
                "itch",

                "ألم",
                "وجع",
                "صداع",
                "عين",
                "بطن",
                "صدر",
                "حكة"
            ]

            is_new_complaint = (
                len(message.split()) >= 4
                and any(
                    word in message.lower()
                    for word in complaint_keywords
                )
                and message.lower() != current_complaint.lower()
            )

            if is_new_complaint:
                print("NEW MEDICAL COMPLAINT DETECTED")

                history = []

                session["history"] = []

                session["current_complaint"] = message
        # =========================
        # RESET
        # =========================
        if message.lower() in [
            "reset",
            "restart",
            "start over",
            "new"
        ]:

            session["history"] = []
            session["current_complaint"] = None

            SessionService.update(
                user_id,
                session
            )

            return {
                "user_id": user_id,
                "reply": "Session restarted.",
                "data": None
            }

        # =========================
        # SAVE USER MESSAGE
        # =========================
        history.append({
            "role": "user",
            "content": message
        })

        # =========================
        # RAG
        # =========================
        rag_data = await call_rag({
            "message": message,
            "history": history
        })

        if not rag_data:

            result = {
                "reply": "Medical service is currently unavailable.",
                "data": None
            }

        else:
            rag_response = rag_data.get("response")
            result = {
                "reply": "Medical assessment:",
                "data": rag_response
            }

            
        # =========================
        # SAVE RESPONSE
        # =========================
        
        history.append({
            "role": "assistant",
            "content": result.get("data") or result["reply"]
        })

        session["history"] = history

        SessionService.update(
            user_id,
            session
        )

        # =========================
        # COOKIE
        # =========================
        response.set_cookie(
            key="chatbot_user_id",
            value=user_id,
            httponly=True,
            max_age=60 * 60 * 24 * 7
        )

        return {
            "user_id": user_id,
            **result
        }

    except Exception as e:

        print("CHATBOT ERROR:", str(e))

        return {
            "error": str(e)
        }