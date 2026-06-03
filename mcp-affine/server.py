import os
import hashlib
import base64
import httpx
from fastmcp import FastMCP
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.dependencies import get_access_token
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

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

# Middleware pour /health (non protégé) et /mcp (proxy vers DAWNCR0W)
class ProxyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Route /health non protégée pour healthcheck Coolify
        if request.url.path == "/health" and request.method == "GET":
            return JSONResponse({"status": "ok"})

        # Route /mcp proxy vers DAWNCR0W (avec auth OAuth)
        if request.url.path == "/mcp" and request.method == "POST":
            # Validation OAuth via le handler normal (call_next)
            # mais on remplace ensuite par notre proxy
            try:
                # Lire le body avant de passer au handler
                body = await request.body()

                # Headers pour DAWNCR0W
                headers = {
                    "Authorization": f"Bearer {DAWNCROW_BEARER_TOKEN}",
                    "Content-Type": request.headers.get("Content-Type", "application/json"),
                }

                # Proxifier vers DAWNCR0W
                async with httpx.AsyncClient(timeout=300.0) as client:
                    async with client.stream(
                        method="POST",
                        url=DAWNCROW_BACKEND_URL,
                        headers=headers,
                        content=body,
                    ) as response:
                        # Copier les headers (sauf certains)
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
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        # Autres routes : passer au handler suivant
        return await call_next(request)

mcp = FastMCP("MCP AFFiNE Proxy", auth=auth, middleware=[ProxyMiddleware])

if __name__ == "__main__":
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)
