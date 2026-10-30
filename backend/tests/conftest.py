import asyncio
import os
import pytest
import pytest_asyncio
from typing import Any, List, Optional
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.core.database import Base, get_db
from app.db.init_db import init_models, seed_data
from app.main import app
from app.core.security import create_access_token
from app.db.models import User, Organization, OrganizationMember
from app.providers.base import BaseAIProvider, AgentTurnResult, ToolCallProposal
from app.providers.factory import set_ai_provider
from app.services.document_intelligence import PropertyInquiryExtractionSchema, ExtractedFieldDetail

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

class MockAIProvider(BaseAIProvider):
    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None, temperature: float = 0.2) -> str:
        return "CONFIRMED Mock response"

    async def generate_structured_response(self, prompt: str, response_schema: Any, system_instruction: Optional[str] = None, temperature: float = 0.1) -> Any:
        if response_schema == PropertyInquiryExtractionSchema:
            return PropertyInquiryExtractionSchema(
                customer_name=ExtractedFieldDetail(value="David Miller", supporting_text_snippet="From: David Miller", confidence_heuristic=0.95),
                email=ExtractedFieldDetail(value="david.miller@example.com", supporting_text_snippet="david.miller@example.com", confidence_heuristic=0.95),
                phone=ExtractedFieldDetail(value="+1-415-555-0199", supporting_text_snippet="Tel: 415-555-0199", confidence_heuristic=0.9),
                preferred_location=ExtractedFieldDetail(value="San Francisco Marina", supporting_text_snippet="looking in Marina district", confidence_heuristic=0.9),
                budget=ExtractedFieldDetail(value="$2,500,000", supporting_text_snippet="Budget around $2.5M", confidence_heuristic=0.9),
                bedrooms=ExtractedFieldDetail(value=3, supporting_text_snippet="3 bedrooms needed", confidence_heuristic=0.95),
                property_type=ExtractedFieldDetail(value="Penthouse", supporting_text_snippet="penthouse or luxury condo", confidence_heuristic=0.9),
                requirements=ExtractedFieldDetail(value="Waterfront view with terrace", supporting_text_snippet="waterfront terrace", confidence_heuristic=0.85)
            )
        if hasattr(response_schema, "model_validate"):
            return response_schema.model_validate({
                "client_name": "Alice Walker",
                "budget": "$2.5M",
                "property_type": "Villa"
            })
        return {}

    async def execute_agent_turn(self, contents: Any, tools: List[Any], system_instruction: Optional[str] = None) -> AgentTurnResult:
        has_tool_results = any("Tool " in str(c) for c in (contents if isinstance(contents, list) else []))
        if has_tool_results:
            return AgentTurnResult(
                text_response="I have proposed the CRM update and scheduled a follow-up task.",
                tool_calls=[],
                finish_reason="stop",
                model_name="mock-gemini"
            )
        return AgentTurnResult(
            text_response=None,
            tool_calls=[
                ToolCallProposal(
                    tool_name="request_approval",
                    arguments={
                        "proposed_action": "create_lead",
                        "target_resource_type": "lead",
                        "proposed_payload": {
                            "contact_name": "Sarah Connor",
                            "budget_range": "$3,000,000",
                            "preferred_location": "Modern Penthouse",
                            "property_type": "Penthouse"
                        },
                        "risk_category": "medium"
                    }
                )
            ],
            finish_reason="tool_call",
            model_name="mock-gemini"
        )

    async def provider_health(self) -> dict:
        return {"status": "healthy", "provider": "google_gemini", "model": "gemini-2.5-flash", "verified": True}

@pytest.fixture(autouse=True)
def default_mock_ai(request):
    # If the test is in test_gemini_provider, do NOT mock by default so it tests real SDK
    if "test_gemini_provider" in request.node.nodeid:
        set_ai_provider(None)
        yield
    else:
        mock = MockAIProvider()
        set_ai_provider(mock)
        yield mock
        set_ai_provider(None)

@pytest_asyncio.fixture(scope="session")
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        await seed_data(session)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(prepare_database):
    async with TestSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def client(prepare_database):
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def auth_headers(db_session: AsyncSession):
    from sqlalchemy import select
    res = await db_session.execute(select(User).where(User.email == "admin@docuflow.ai"))
    user = res.scalar_one()

    m_res = await db_session.execute(select(OrganizationMember).where(OrganizationMember.user_id == user.id))
    member = m_res.scalar_one()

    token = create_access_token({"sub": user.id, "email": user.email})
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": member.organization_id
    }
