"""
Portier MCP AFFiNE - Proxy HTTP avec auth OIDC/Keycloak
Proxifie toutes les requêtes MCP vers DAWNCR0W après validation OAuth.
"""
import os
import hashlib
import base64
import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet
import uvicorn

# Configuration
CONFIG_URL           = os.environ["OIDC_CONFIG_URL"]
CLIENT_ID            = os.environ["OIDC_CLIENT_ID"]
CLIENT_SECRET        = os.environ["OIDC_CLIENT_SECRET"]
BASE_URL             = os.environ["MCP_BASE_URL"]
REDIS_URL            = os.environ["REDIS_URL"]
JWT_KEY              = os.environ["JWT_SIGNING_KEY"]
FERNET_SECRET        = os.environ["FERNET_SECRET"]
DAWNCROW_BACKEND_URL = os.environ["DAWNCROW_BACKEND_URL"]
DAWNCROW_BEARER_TOKEN = os.environ["DAWNCROW_BEARER_TOKEN"]
MCP_HOST             = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT             = int(os.environ.get("MCP_PORT", "8000"))

def derive_fernet_key(s: str) -> bytes:
    """Dérive une clé Fernet 32-byte URL-safe depuis une string."""
    return base64.urlsafe_b64encode(hashlib.sha256(s.encode()).digest())

# Setup storage chiffré
fernet = Fernet(derive_fernet_key(FERNET_SECRET))
store = RedisStore(url=REDIS_URL)
encrypted_store = FernetEncryptionWrapper(
    key_value=store,
    fernet=fernet,
    raise_on_decryption_error=False,
)

# Setup OIDCProxy
auth = OIDCProxy(
    config_url=CONFIG_URL,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    base_url=BASE_URL,
    redirect_path="/auth/callback",
    required_scopes=["openid", "mcp:execute"],
    jwt_signing_key=JWT_KEY,
    client_storage=encrypted_store,
)

# Client HTTP réutilisable
http_client = httpx.AsyncClient(timeout=300.0)

async def health_check(request: Request):
    """Healthcheck non protégé pour Coolify."""
    return JSONResponse({"status": "ok"})

async def proxy_to_dawncrow(request: Request):
    """
    Proxifie toutes les requêtes MCP vers DAWNCR0W.
    L'auth OAuth est déjà validée par OIDCProxy middleware.
    """
    # Lire le body
    body = await request.body()

    # Headers pour DAWNCR0W (remplace auth OAuth par bearer token)
    headers = {
        "Authorization": f"Bearer {DAWNCROW_BEARER_TOKEN}",
        "Content-Type": request.headers.get("Content-Type", "application/json"),
    }

    # Proxifier vers DAWNCR0W avec streaming
    async with http_client.stream(
        method=request.method,
        url=DAWNCROW_BACKEND_URL,
        headers=headers,
        content=body,
    ) as response:
        # Copier headers (sauf certains)
        response_headers = dict(response.headers)
        for key in ["content-encoding", "content-length", "transfer-encoding"]:
            response_headers.pop(key, None)

        # Stream la réponse
        async def stream_response():
            async for chunk in response.aiter_bytes():
                yield chunk

        return StreamingResponse(
            stream_response(),
            status_code=response.status_code,
            headers=response_headers,
        )

# Routes
routes = [
    Route("/health", health_check, methods=["GET"]),
    Route("/mcp", proxy_to_dawncrow, methods=["GET", "POST"]),
]

# Application Starlette avec OIDCProxy middleware
app = Starlette(
    routes=routes,
    middleware=[Middleware(auth.middleware_class)],
)

if __name__ == "__main__":
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
