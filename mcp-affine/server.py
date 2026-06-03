"""
Portier MCP AFFiNE - Proxy natif FastMCP vers DAWNCR0W
Auth OIDC/Keycloak → Proxy transparent vers DAWNCR0W
"""
import os
import hashlib
import base64
from fastmcp.server import create_proxy
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.client.transports.http import StreamableHttpTransport
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

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

# Transport HTTP vers DAWNCR0W avec bearer token
transport = StreamableHttpTransport(
    url=DAWNCROW_BACKEND_URL,
    headers={"Authorization": f"Bearer {DAWNCROW_BEARER_TOKEN}"},
)

# Proxy natif FastMCP avec auth OIDC
proxy = create_proxy(
    target=transport,
    auth=auth,
    name="MCP AFFiNE Proxy",
)

if __name__ == "__main__":
    proxy.run(transport="http", host=MCP_HOST, port=MCP_PORT)
