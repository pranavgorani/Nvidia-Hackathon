import io
import pytest
from httpx import AsyncClient

SAMPLE_PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<< /Title (Real Estate Inquiry) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"

@pytest.mark.asyncio
async def test_end_to_end_property_intake(client: AsyncClient, auth_headers: dict):
    # 1. Upload sample inquiry document
    files = {"file": ("inquiry_david_miller.pdf", io.BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
    upload_res = await client.post(
        "/api/documents/upload",
        files=files,
        headers=auth_headers
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    # 2. Trigger Property Intake Agent workflow with document
    run_res = await client.post(
        "/api/agent/run",
        json={
            "instruction": "Process this new property inquiry and prepare the CRM update.",
            "skill_id": "property_intake_agent",
            "document_id": doc_id
        },
        headers=auth_headers
    )
    assert run_res.status_code == 200
    wf_data = run_res.json()
    assert wf_data["status"] == "paused_for_approval"
    approval_id = wf_data["approval_id"]
    workflow_id = wf_data["workflow_id"]

    # 3. Verify workflow timeline steps
    wf_timeline_res = await client.get(
        f"/api/agent/workflows/{workflow_id}",
        headers=auth_headers
    )
    assert wf_timeline_res.status_code == 200
    steps = wf_timeline_res.json()["steps"]
    assert len(steps) >= 3
    step_types = [s["step_type"] for s in steps]
    assert "plan" in step_types
    assert "approval_request" in step_types

    # 4. Approve the pending action in Approval Center
    approve_res = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"decision": "approve", "notes": "Approved for CRM creation"},
        headers=auth_headers
    )
    assert approve_res.status_code == 200
    exec_result = approve_res.json()["execution_result"]
    assert exec_result["status"] == "success"
    lead_id = exec_result["lead_id"]

    # 5. Verify CRM Lead exists
    lead_res = await client.get(f"/api/crm/leads/{lead_id}", headers=auth_headers)
    assert lead_res.status_code == 200
    assert lead_res.json()["lead"]["id"] == lead_id

    # 6. Verify Audit Logs captured the full lifecycle
    audit_res = await client.get("/api/audit/logs", headers=auth_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    action_types = [log["action_type"] for log in logs]
    assert "approval_requested" in action_types
    assert "action_executed_after_approval" in action_types

