import json
import os
import re
import time
import requests


class LLMService:

    # =========================
    # Language Detection
    # =========================
    @staticmethod
    def detect_language(text: str) -> str:
        arabic_chars = re.findall(r'[\u0600-\u06FF]', text)
        english_chars = re.findall(r'[a-zA-Z]', text)

        return "ar" if len(arabic_chars) > len(english_chars) else "en"

    # =========================
    # Intent Extraction (Gemini)
    # =========================
    @staticmethod
    def extract_intent(message: str):
        lang = LLMService.detect_language(message)

        if lang == "ar":
            prompt = f"""
            أنت مساعد لنظام عيادة.
            مهمتك فقط تحديد نية المستخدم.

            لو المستخدم يسأل عن أعراض أو معلومات صحية → intent = medical_query
            لو المستخدم يريد حجز → intent = book_appointment

            أرجع JSON فقط:
            {{
                "intent": "book_appointment|cancel|reschedule|availability|medical_query|general",
                "specialization": "dermatologist|cardiologist|neurologist|other",
                "date": "YYYY-MM-DD أو today أو tomorrow أو فارغ",
                "time": "HH:MM أو فارغ"
            }}

            رسالة المستخدم: "{message}"
            """
        else:
            prompt = f"""
            You are an assistant for a clinic system.

            Your ONLY job is to classify intent.

            If user asks about symptoms or health → medical_query
            If user wants booking → book_appointment

            Return ONLY JSON:
            {{
                "intent": "book_appointment|cancel|reschedule|availability|medical_query|general",
                "specialization": "dermatologist|cardiologist|neurologist|other",
                "date": "YYYY-MM-DD or today or tomorrow or empty",
                "time": "HH:MM or empty"
            }}

            User message: "{message}"
            """

        API_KEY = os.getenv("GEMINI_API_KEY")

        if not API_KEY:
            return LLMService._fallback_intent(message)

        for attempt in range(2):
            try:
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}",
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=10
                )

                if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                    time.sleep(1)
                    continue

                response.raise_for_status()
                result = response.json()

                return LLMService._parse_response(result)

            except Exception:
                if attempt == 0:
                    time.sleep(1)
                    continue
                return LLMService._fallback_intent(message)

    # =========================
    # Decision Layer
    # =========================
    @staticmethod
    def process_message(message: str):
        intent_data = LLMService.extract_intent(message)
        intent = intent_data.get("intent")

        # 🎯 backend intents
        backend_intents = {
            "book_appointment",
            "cancel",
            "reschedule",
            "availability"
        }

        if intent in backend_intents:
            return {
                "action": "backend",
                "intent_data": intent_data
            }

        # 🎯 medical → RAG API
        if intent == "medical_query":
            return {
                "action": "rag_api",
                "query": message
            }

        # 🎯 default
        return {
            "action": "general",
            "intent_data": intent_data
        }

    # =========================
    # Helpers
    # =========================
    @staticmethod
    def _parse_response(result):
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()

        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(text)

        parsed.setdefault("intent", "general")
        parsed.setdefault("specialization", None)
        parsed.setdefault("date", None)
        parsed.setdefault("time", None)

        return parsed

    @staticmethod
    def _fallback_intent(message: str):
        msg = message.lower()

        if any(k in msg for k in ["book", "appointment", "حجز", "موعد"]):
            intent = "book_appointment"
        elif any(k in msg for k in ["صداع", "ألم", "pain", "symptom"]):
            intent = "medical_query"
        else:
            intent = "general"

        return {
            "intent": intent,
            "specialization": None,
            "date": None,
            "time": None
        }
        
    @staticmethod
    def _infer_specialization(message: str, lang: str = None):
        if lang is None:
            lang = LLMService.detect_language(message)

        lower_message = message.lower()

        # Arabic
        if lang == "ar":
            if any(k in lower_message for k in ["جلد", "حكة", "طفح", "حب الشباب", "احمرار"]):
                return "dermatologist"
            if any(k in lower_message for k in ["قلب", "ضغط", "خفقان", "صدر"]):
                return "cardiologist"
            if any(k in lower_message for k in ["صداع", "دوخة", "تنميل"]):
                return "neurologist"

        # English
        else:
            if any(k in lower_message for k in ["skin", "rash", "acne", "itch"]):
                return "dermatologist"
            if any(k in lower_message for k in ["heart", "chest pain", "pressure"]):
                return "cardiologist"
            if any(k in lower_message for k in ["headache", "dizziness", "numb"]):
                return "neurologist"

        return None