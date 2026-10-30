import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register new user
    reg_resp = await client.post(
        "/api/auth/register",
        json={
            "email": "agent_jordan@example.com",
            "full_name": "Jordan Bell",
            "password": "Password123!",
            "organization_name": "Jordan Realty"
        }
    )
    assert reg_resp.status_code == 200
    data = reg_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "agent_jordan@example.com"
    token = data["access_token"]
    org_id = data["active_organization_id"]

    # Access /api/auth/me
    me_resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["user"]["email"] == "agent_jordan@example.com"

@pytest.mark.asyncio
async def test_cross_tenant_isolation(client: AsyncClient, auth_headers: dict):
    # Register a different tenant
    tenant2_resp = await client.post(
        "/api/auth/register",
        json={
            "email": "tenant2@example.com",
            "full_name": "Tenant Two",
            "password": "Password123!",
            "organization_name": "Tenant Two Corp"
        }
    )
    tenant2_data = tenant2_resp.json()
    tenant2_token = tenant2_data["access_token"]
    tenant2_org = tenant2_data["active_organization_id"]

    # Tenant 2 creates a private lead
    create_resp = await client.post(
        "/api/crm/leads",
        json={
            "contact_name": "Confidential Buyer",
            "budget_range": "$10,000,000"
        },
        headers={"Authorization": f"Bearer {tenant2_token}", "X-Organization-Id": tenant2_org}
    )
    assert create_resp.status_code == 200
    tenant2_lead_id = create_resp.json()["id"]

    # Tenant 1 attempts to access Tenant 2's lead using Tenant 1's token and org header
    unauthorized_resp = await client.get(
        f"/api/crm/leads/{tenant2_lead_id}",
        headers=auth_headers
    )
    # Must be 404 (or 403) - cross-tenant resource is completely blocked
    assert unauthorized_resp.status_code == 404

