import os
import hashlib
import base64
from fastmcp import FastMCP
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.dependencies import get_access_token
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

CONFIG_URL    = os.environ["OIDC_CONFIG_URL"]
CLIENT_ID     = os.environ["OIDC_CLIENT_ID"]
CLIENT_SECRET = os.environ["OIDC_CLIENT_SECRET"]
BASE_URL      = os.environ["MCP_BASE_URL"]
REDIS_URL     = os.environ["REDIS_URL"]
JWT_KEY       = os.environ["JWT_SIGNING_KEY"]
FERNET_SECRET = os.environ["FERNET_SECRET"]

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
    audience=BASE_URL,  # Recommended for production (Keycloak best practice)
    base_url=BASE_URL,
    redirect_path="/auth/callback",
    required_scopes=["openid", "mcp:execute"],
    jwt_signing_key=JWT_KEY,
    client_storage=encrypted_store,
)

mcp = FastMCP("MCP Postgres OPEPARTNER", auth=auth)

@mcp.tool
async def hello_world(name: str = "monde") -> str:
    """Outil de test : renvoie un salut avec l'utilisateur authentifié."""
    token = get_access_token()
    user_id = token.claims.get("sub", "anonyme")
    scopes = token.claims.get("scope", "")
    return f"Bonjour {name} ! Le MCP Postgres fonctionne. Utilisateur: {user_id}, Scopes: {scopes}"

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8080)
