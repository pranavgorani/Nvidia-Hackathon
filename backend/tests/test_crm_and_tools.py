import pytest
from httpx import AsyncClient
from app.tools.registry import tool_registry

@pytest.mark.asyncio
async def test_tool_allowlist_unknown_tool_rejection(db_session):
    with pytest.raises(ValueError, match="not in the approved tool allowlist"):
        await tool_registry.execute_tool(
            tool_name="unapproved_system_shell_exec",
            arguments={"cmd": "whoami"},
            organization_id="org_1",
            actor_id="user_1",
            workflow_id="wf_1",
            session=db_session
        )

@pytest.mark.asyncio
async def test_tool_argument_validation_failure(db_session):
    # Pass invalid argument type (string for required int)
    with pytest.raises(ValueError, match="Argument validation failed"):
        await tool_registry.execute_tool(
            tool_name="list_documents",
            arguments={"limit": "not_an_integer"},
            organization_id="org_1",
            actor_id="user_1",
            workflow_id="wf_1",
            session=db_session
        )

@pytest.mark.asyncio
async def test_crm_contact_duplicate_matching(client: AsyncClient, auth_headers: dict):
    # Create contact
    await client.post(
        "/api/crm/leads",
        json={
            "contact_name": "Eleanor Vance",
            "email": "eleanor.vance@hillhouse.com",
            "phone": "+1-555-019-2834",
            "budget_range": "$1,500,000",
            "preferred_location": "Palo Alto"
        },
        headers=auth_headers
    )

    # Search leads with exact email
    search_res = await client.get(
        "/api/crm/leads?search=eleanor.vance@hillhouse.com",
        headers=auth_headers
    )
    assert search_res.status_code == 200
    leads = search_res.json()
    assert len(leads) >= 1
    assert leads[0]["contact_name"] == "Eleanor Vance"

