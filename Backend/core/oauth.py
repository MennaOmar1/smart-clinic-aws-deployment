from authlib.integrations.starlette_client import OAuth
import os
from dotenv import load_dotenv

load_dotenv()

oauth = OAuth()

oauth.register(
    name="google",

    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),

    access_token_url="https://oauth2.googleapis.com/token",
    authorize_url="https://accounts.google.com/o/oauth2/auth",

    api_base_url="https://www.googleapis.com/oauth2/v1/",

    client_kwargs={
        "scope": (
            "email "
            "profile "
            "https://www.googleapis.com/auth/calendar "
            "https://www.googleapis.com/auth/gmail.send"
        )
    },

    access_type="offline",
    prompt="consent",
)