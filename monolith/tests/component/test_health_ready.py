import httpx


async def test_ready_is_ok_with_real_postgres(client: httpx.AsyncClient) -> None:
    r = await client.get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "checks": {"postgres": "up"}}
