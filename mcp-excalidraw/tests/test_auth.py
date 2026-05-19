"""Test auth bearer token (H.6)"""

import asyncio
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

SERVER_URL = "http://127.0.0.1:8000/mcp"
TOKEN = "r0EPfQ4FAJBYhD5WZvzctkh9Xq3fgxR0q4i5kAUDn-s"


async def test_with_token():
    """Test MCP endpoint avec token valide"""
    print("\n" + "="*80)
    print("TEST AUTH : MCP endpoint avec bearer token valide")
    print("="*80)

    # Transport avec bearer token dans les headers
    headers = {"Authorization": f"Bearer {TOKEN}"}
    transport = StreamableHttpTransport(url=SERVER_URL, headers=headers)

    async with Client(transport) as client:
        print(f"\n✅ Connexion MCP établie avec auth")

        # Test list_tools
        tools = await client.list_tools()
        print(f"\n📋 Outils reçus : {len(tools)}")

        for tool in tools[:3]:
            print(f"   • {tool.name}")

        print(f"\n✅ Auth bearer token : FONCTIONNEL")


async def test_without_token():
    """Test MCP endpoint SANS token (doit échouer)"""
    print("\n" + "="*80)
    print("TEST AUTH : MCP endpoint SANS bearer token (doit échouer)")
    print("="*80)

    transport = StreamableHttpTransport(url=SERVER_URL)

    try:
        async with Client(transport) as client:
            await client.list_tools()
            print("\n❌ ERREUR : La connexion a réussi sans token !")
    except Exception as e:
        print(f"\n✅ Connexion refusée comme attendu : {type(e).__name__}")
        print(f"   Message : {str(e)[:100]}")


async def main():
    await test_without_token()
    await test_with_token()

    print("\n" + "="*80)
    print("✅ Tests auth terminés")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
