import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.db.models import WorkflowExecution, WorkflowStep, Skill
from app.providers.factory import get_ai_provider
from app.tools.registry import tool_registry
from app.services.audit import audit_service
from app.skills.property_intake import property_intake_agent

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Enterprise Agent Runtime orchestrating instructions, tools, approvals, and audit trails.
    """

    async def run_workflow(
        self,
        organization_id: str,
        actor_id: Optional[str],
        instruction: str,
        skill_id: Optional[str] = None,
        document_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        session: AsyncSession = None
    ) -> Dict[str, Any]:
        # 1. Resolve skill
        selected_skill_id = skill_id or "property_intake_agent"
        skill_stmt = select(Skill).where(Skill.skill_id == selected_skill_id)
        skill_res = await session.execute(skill_stmt)
        skill = skill_res.scalar_one_or_none()

        allowed_tools = skill.allowed_tools_json if skill else None

        # 2. Create Workflow record
        workflow = WorkflowExecution(
            organization_id=organization_id,
            initiated_by_id=actor_id,
            skill_id=selected_skill_id,
            status="running",
            initial_instruction=instruction,
            context_data_json={
                "document_id": document_id,
                **(context_data or {})
            }
        )
        session.add(workflow)
        await session.commit()
        await session.refresh(workflow)

        # 3. If Property Intake Agent and document_id is present, run signature skill
        if selected_skill_id == "property_intake_agent" and document_id:
            result = await property_intake_agent.execute(
                workflow=workflow,
                document_id=document_id,
                session=session
            )
            return result

        # 4. Otherwise, run conversational / multi-turn agent with Gemini tool calling
        ai_provider = get_ai_provider()
        declarations = tool_registry.get_gemini_declarations(allowed_tools)

        step_counter = 1
        contents = [
            f"User Instruction: {instruction}\n"
            f"Context: {context_data or {}}\n"
            f"Available Tools: {allowed_tools}\n"
            f"You are the DocuFlow Agent. Use the provided tools when appropriate. "
            f"If you need to create or modify CRM data, propose the action using create_lead, update_lead, or request_approval."
        ]

        turns = 0
        final_text = ""

        while turns < settings.MAX_AGENT_TURNS:
            turns += 1

            turn_result = await ai_provider.execute_agent_turn(
                contents=contents,
                tools=declarations,
                system_instruction="You are the DocuFlow AI Agent OS assistant managing real estate workflows."
            )

            # If model produced text, capture it
            if turn_result.text_response:
                final_text = turn_result.text_response

            # If no tool calls, workflow turn completed
            if not turn_result.tool_calls:
                step = WorkflowStep(
                    workflow_id=workflow.id,
                    step_number=step_counter,
                    step_type="model_proposal",
                    status="completed",
                    input_data_json={"turn": turns},
                    output_data_json={"response": turn_result.text_response}
                )
                session.add(step)
                step_counter += 1
                break

            # Process tool proposals
            tool_executed = False
            for proposal in turn_result.tool_calls:
                # Check tool definition
                tool_def = tool_registry.get_tool(proposal.tool_name)

                # Record proposal step
                prop_step = WorkflowStep(
                    workflow_id=workflow.id,
                    step_number=step_counter,
                    step_type="model_proposal",
                    status="completed",
                    input_data_json={"tool": proposal.tool_name, "args": proposal.arguments},
                    output_data_json={"status": "proposed"}
                )
                session.add(prop_step)
                step_counter += 1

                # If tool requires approval or is write action under strict policy
                if proposal.tool_name == "request_approval":
                    approval_args = dict(proposal.arguments)
                    approval_args["workflow_id"] = workflow.id
                    approval_res = await tool_registry.execute_tool(
                        tool_name="request_approval",
                        arguments=approval_args,
                        organization_id=organization_id,
                        actor_id=actor_id,
                        workflow_id=workflow.id,
                        session=session
                    )
                    workflow.status = "paused_for_approval"
                    workflow.final_summary = f"Workflow paused. Proposed {approval_args.get('proposed_action', 'action')} requires human approval."
                    await session.commit()
                    return {
                        "status": "paused_for_approval",
                        "workflow_id": workflow.id,
                        "approval_id": approval_res.get("approval_id"),
                        "message": "Approval required before write execution."
                    }

                elif tool_def and (tool_def.requires_approval or (tool_def.is_write_action and settings.REQUIRE_APPROVAL_FOR_WRITES)):
                    # Model proposed direct write (e.g. create_lead), intercept and create approval
                    approval_res = await tool_registry.execute_tool(
                        tool_name="request_approval",
                        arguments={
                            "workflow_id": workflow.id,
                            "proposed_action": proposal.tool_name,
                            "target_resource_type": "crm_resource",
                            "proposed_payload": proposal.arguments,
                            "risk_category": "medium",
                            "reasoning": f"Model proposed {proposal.tool_name}"
                        },
                        organization_id=organization_id,
                        actor_id=actor_id,
                        workflow_id=workflow.id,
                        session=session
                    )
                    workflow.status = "paused_for_approval"
                    workflow.final_summary = f"Workflow paused. Proposed {proposal.tool_name} requires human approval."
                    await session.commit()
                    return {
                        "status": "paused_for_approval",
                        "workflow_id": workflow.id,
                        "approval_id": approval_res.get("approval_id"),
                        "message": "Approval required before write execution."
                    }

                # Otherwise execute permitted read/write tool
                try:
                    tool_output = await tool_registry.execute_tool(
                        tool_name=proposal.tool_name,
                        arguments=proposal.arguments,
                        organization_id=organization_id,
                        actor_id=actor_id,
                        workflow_id=workflow.id,
                        session=session
                    )

                    exec_step = WorkflowStep(
                        workflow_id=workflow.id,
                        step_number=step_counter,
                        step_type="tool_result",
                        status="completed",
                        input_data_json={"tool": proposal.tool_name, "args": proposal.arguments},
                        output_data_json=tool_output
                    )
                    session.add(exec_step)
                    step_counter += 1

                    # Append observation to contents for next turn
                    contents.append(f"Tool {proposal.tool_name} returned: {tool_output}")
                    tool_executed = True

                except Exception as e:
                    error_step = WorkflowStep(
                        workflow_id=workflow.id,
                        step_number=step_counter,
                        step_type="tool_result",
                        status="failed",
                        input_data_json={"tool": proposal.tool_name, "args": proposal.arguments},
                        output_data_json={"error": str(e)}
                    )
                    session.add(error_step)
                    step_counter += 1
                    contents.append(f"Tool {proposal.tool_name} failed with error: {str(e)}")

        workflow.status = "completed"
        workflow.final_summary = final_text or "Agent workflow completed all turns successfully."
        await session.commit()

        return {
            "status": "completed",
            "workflow_id": workflow.id,
            "final_summary": workflow.final_summary
        }

agent_orchestrator = AgentOrchestrator()

