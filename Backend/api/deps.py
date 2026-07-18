from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_roles(allowed_roles: list):

    def role_checker(user=Depends(get_current_user)):

        role = user.get("role")

        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Not authorized"
            )

        return user

    return role_checker