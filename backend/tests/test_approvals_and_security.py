import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import ApprovalRequest, Lead
from app.services.approval import approval_service
from app.core.security import compute_payload_hash

@pytest.mark.asyncio
async def test_approval_tamper_detection(db_session: AsyncSession):
    # Create an approval request
    payload = {"contact_name": "Marcus Stone", "budget_range": "$1,200,000"}
    approval = await approval_service.create_approval_request(
        organization_id="org_test_1",
        workflow_id="wf_test_1",
        requesting_user_id="user_test_1",
        target_resource_type="lead",
        proposed_action="create_lead",
        proposed_payload=payload,
        session=db_session
    )
    assert approval.status == "pending"
    original_hash = approval.payload_hash

    # Simulate malicious actor altering payload in database
    approval.proposed_payload_json = {"contact_name": "Marcus Stone", "budget_range": "$99,999,999"}

    # Attempting to execute approved action must fail with tamper error
    with pytest.raises(ValueError, match="tampered with or modified"):
        await approval_service.execute_approved_action(
            approval=approval,
            actor_id="admin_1",
            session=db_session
        )

@pytest.mark.asyncio
async def test_approval_flow_via_api(client: AsyncClient, auth_headers: dict):
    # 1. Propose lead creation through approval
    wf_res = await client.post(
        "/api/agent/run",
        json={
            "instruction": "Add lead for Sarah Connor looking for Modern Penthouse with $3M budget",
            "skill_id": "property_intake_agent"
        },
        headers=auth_headers
    )
    assert wf_res.status_code == 200

    # 2. Check pending approvals list
    appr_list_res = await client.get("/api/approvals?status=pending", headers=auth_headers)
    assert appr_list_res.status_code == 200
    approvals = appr_list_res.json()
    assert len(approvals) >= 1

    target_appr = approvals[0]
    appr_id = target_appr["id"]
    assert target_appr["proposed_action"] == "create_lead"
    assert target_appr["status"] == "pending"

    # 3. Approve the action
    decide_res = await client.post(
        f"/api/approvals/{appr_id}/decide",
        json={"decision": "approve", "notes": "Approved by testing admin"},
        headers=auth_headers
    )
    assert decide_res.status_code == 200
    decide_data = decide_res.json()
    assert decide_data["status"] == "approved"
    assert "execution_result" in decide_data
    created_lead_id = decide_data["execution_result"]["lead_id"]

    # 4. Verify CRM lead was persisted
    lead_res = await client.get(f"/api/crm/leads/{created_lead_id}", headers=auth_headers)
    assert lead_res.status_code == 200
    lead_data = lead_res.json()["lead"]
    assert lead_data["id"] == created_lead_id

