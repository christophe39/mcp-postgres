"""Test container Docker local (H.6)"""

import asyncio
import json
import subprocess
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

SERVER_URL = "http://localhost:8001/mcp"


def get_sample_scene_json():
    """Retourne un JSON Excalidraw minimal valide"""
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [
            {
                "type": "rectangle",
                "version": 1,
                "versionNonce": 1,
                "isDeleted": False,
                "id": "test-docker-rect-1",
                "fillStyle": "solid",
                "strokeWidth": 2,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "angle": 0,
                "x": 100,
                "y": 100,
                "strokeColor": "#1e1e1e",
                "backgroundColor": "#ffc9c9",
                "width": 200,
                "height": 100,
                "seed": 1,
                "groupIds": [],
                "frameId": None,
                "roundness": {"type": 3},
                "boundElements": [],
                "updated": 1,
                "link": None,
                "locked": False
            }
        ],
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": "#ffffff"
        },
        "files": {}
    }


def cleanup_sql():
    """Cleanup base PostgreSQL"""
    cmd = [
        "ssh", "root@69.62.110.207",
        'docker exec pk4s888o4wkc8ogokg0sg840 psql -U postgres -d opepartner -c "DELETE FROM schemas_excalidraw WHERE document_title LIKE \'TEST%\'; DELETE FROM clients WHERE nom_entreprise LIKE \'TEST%\';"'
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=10)
    except:
        pass


async def test_docker_container():
    """Test complet container Docker"""
    print("\n" + "="*80)
    print("TEST CONTAINER DOCKER — MCP Excalidraw H.6")
    print("="*80)

    # Cleanup avant test
    cleanup_sql()

    # Connexion MCP
    transport = StreamableHttpTransport(url=SERVER_URL)
    async with Client(transport) as client:
        print(f"\n✅ Connexion MCP établie : {SERVER_URL}")

        # Test 1 : list_tools
        tools = await client.list_tools()
        print(f"\n📋 Test 1 : list_tools → {len(tools)} outils")
        assert len(tools) == 6
        print(f"   ✅ 6 outils MCP exposés")

        # Test 2 : create_excalidraw_scene (orchestration)
        print(f"\n📤 Test 2 : create_excalidraw_scene (orchestration)")

        scene_json = get_sample_scene_json()
        arguments = {
            "scene_json": scene_json,
            "client_name": "TEST-DOCKER-CONTAINER",
            "document_type": "Test",
            "document_title": "TEST Container Docker H.6",
            "confidentiel": True,
            "tags": ["test", "docker"]
        }

        result = await client.call_tool("create_excalidraw_scene", arguments)
        response = json.loads(result.content[0].text)

        print(f"   Client ID : {response['client_id']}")
        print(f"   Scene ID : {response['scene_id']}")
        print(f"   Schema ID : {response['schema_id']}")
        print(f"   ✅ Orchestration réussie")

        # Cleanup
        cleanup_sql()
        print(f"\n🧹 Cleanup effectué")

    print("\n" + "="*80)
    print("✅ CONTAINER DOCKER VALIDÉ")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_docker_container())
