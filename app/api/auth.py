"""GitHub OAuth routes."""
from fastapi import APIRouter, HTTPException, Response, Cookie
from fastapi.responses import RedirectResponse
import httpx
import jwt
import time
from app.core.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

JWT_SECRET    = "codesense-secret-change-in-production"
JWT_ALGORITHM = "HS256"
GITHUB_AUTH_URL    = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL   = "https://github.com/login/oauth/access_token"
GITHUB_API         = "https://api.github.com"


def _make_jwt(github_token: str, user: dict) -> str:
    payload = {
        "github_token": github_token,
        "login":        user.get("login"),
        "avatar_url":   user.get("avatar_url"),
        "name":         user.get("name"),
        "exp":          int(time.time()) + 60 * 60 * 8,  # 8 hours
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")


def get_current_user(session: str | None = Cookie(default=None)) -> dict:
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_jwt(session)


# ── OAuth flow ────────────────────────────────────────────────────

@router.get("/github")
async def github_login():
    """Redirect to GitHub OAuth authorization page."""
    client_id = settings.github_client_id
    if not client_id:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID not configured")
    url = (
        f"{GITHUB_AUTH_URL}"
        f"?client_id={client_id}"
        f"&scope=repo,read:user"
    )
    return RedirectResponse(url)


@router.get("/callback")
async def github_callback(code: str, response: Response):
    """Exchange OAuth code for access token, set session cookie."""
    async with httpx.AsyncClient() as client:
        # Exchange code for token
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id":     settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code":          code,
            },
        )
        token_data    = token_resp.json()
        github_token  = token_data.get("access_token")
        if not github_token:
            raise HTTPException(status_code=400, detail="Failed to obtain GitHub token")

        # Get user info
        user_resp = await client.get(
            f"{GITHUB_API}/user",
            headers={"Authorization": f"Bearer {github_token}"},
        )
        user = user_resp.json()

    session_token = _make_jwt(github_token, user)
    redirect = RedirectResponse(url="http://localhost:5174")
    redirect.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return redirect


@router.get("/me")
async def get_me(session: str | None = Cookie(default=None)):
    """Return current authenticated user."""
    user = get_current_user(session)
    return {"login": user["login"], "avatar_url": user["avatar_url"], "name": user.get("name")}


@router.post("/logout")
async def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie("session")
    return {"message": "Logged out"}


# ── GitHub API proxy ──────────────────────────────────────────────

@router.get("/repos")
async def list_repos(session: str | None = Cookie(default=None)):
    """List authenticated user's GitHub repositories."""
    user = get_current_user(session)
    github_token = user["github_token"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_API}/user/repos",
            headers={"Authorization": f"Bearer {github_token}"},
            params={"per_page": 100, "sort": "updated", "type": "all"},
        )
        repos = resp.json()

    return [
        {
            "full_name":    r["full_name"],
            "name":         r["name"],
            "description":  r.get("description") or "",
            "language":     r.get("language") or "",
            "private":      r["private"],
            "url":          r["html_url"],
            "clone_url":    r["clone_url"],
            "updated_at":   r["updated_at"],
        }
        for r in repos
        if isinstance(r, dict)
    ]
