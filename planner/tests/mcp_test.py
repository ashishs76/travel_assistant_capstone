from planner.tools import interest_mcp_client

def test_mcp_poi_roundtrip():
    results = interest_mcp_client.call_search_pois("Cancun, Mexico", limit=5)
    print(results)
    assert len(results) > 0
    assert all("name" in p for p in results)