"""Gemini chat with tool calling. Runs a bounded tool-call loop and returns the final reply plus
a trace of which tools were used so the frontend can display tool-chip badges."""
import json
import logging
from typing import Any

import google.generativeai as genai
from google.generativeai.types import content_types
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.ai_tools import TOOL_SCHEMAS, dispatch_tool

log = logging.getLogger(__name__)
settings = get_settings()

MAX_TOOL_ITERATIONS = 6

SYSTEM_PROMPT = (
    "You are the SmartStore AI Assistant for a multi-warehouse grocery / FMCG retailer.\n"
    "Always answer using DATA returned by tools. NEVER invent SKUs, stock numbers, prices, "
    "supplier names, or PO ids. If a tool returns no matching rows, say so plainly.\n"
    "When the user asks about low stock, expiring items, or specific products, CALL THE APPROPRIATE TOOL FIRST.\n"
    "When the user asks to draft / create / place a purchase order, call create_draft_po. "
    "Before calling create_draft_po, make sure you know the supplier_id and concrete product ids — "
    "call get_low_stock_products or get_product_detail first if needed.\n"
    "Reply concisely. Use bullets for lists of products. Always include SKUs alongside names so the user can act on the answer."
)


def _configured() -> bool:
    return bool(settings.GEMINI_API_KEY)


def _build_model() -> Any:
    if not _configured():
        return None
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(
        settings.GEMINI_CHAT_MODEL,
        tools=[{"function_declarations": TOOL_SCHEMAS}],
        system_instruction=SYSTEM_PROMPT,
    )


def _to_gemini_history(messages: list[dict]) -> list[dict]:
    history: list[dict] = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        history.append({"role": role, "parts": [{"text": m["content"]}]})
    return history


async def chat(messages: list[dict], db: AsyncSession, tenant_id: int, user_id: int) -> dict:
    """Run a tool-calling chat loop and return {reply, tool_calls[]}.

    `messages` is the conversation history coming from the frontend (user + assistant turns).
    """
    if not _configured():
        return {
            "reply": (
                "[Gemini key not configured] I would normally answer using live store data via tool "
                "calls. Set GEMINI_API_KEY in the backend env to enable me."
            ),
            "tool_calls": [],
        }

    model = _build_model()
    history = _to_gemini_history(messages[:-1]) if messages else []
    chat_session = model.start_chat(history=history)
    last_user = messages[-1]["content"] if messages else ""

    tool_trace: list[dict] = []
    response = chat_session.send_message(last_user)

    for _ in range(MAX_TOOL_ITERATIONS):
        function_calls = []
        try:
            for cand in (response.candidates or []):
                for part in cand.content.parts:
                    fc = getattr(part, "function_call", None)
                    if fc and fc.name:
                        function_calls.append(fc)
        except Exception:
            log.exception("error inspecting Gemini response")
            break

        if not function_calls:
            break

        tool_response_parts = []
        for fc in function_calls:
            args = dict(fc.args) if fc.args else {}
            log.info("AI tool call: %s args=%s", fc.name, args)
            try:
                result = await dispatch_tool(fc.name, args, db, tenant_id, user_id)
            except Exception as e:
                log.exception("tool %s failed", fc.name)
                result = {"error": str(e)}
            preview = json.dumps(result)[:300]
            tool_trace.append({"name": fc.name, "args": args, "result_preview": preview})
            tool_response_parts.append(
                content_types.to_part({
                    "function_response": {"name": fc.name, "response": {"result": result}}
                })
            )
        response = chat_session.send_message(tool_response_parts)

    final_text = ""
    try:
        final_text = response.text
    except Exception:
        # response.text raises if there is no plain text part
        try:
            final_text = "".join(
                p.text for cand in (response.candidates or [])
                for p in cand.content.parts if getattr(p, "text", None)
            )
        except Exception:
            final_text = ""
    if not final_text:
        final_text = "I gathered the data but couldn't compose a reply. Please try rephrasing."
    return {"reply": final_text, "tool_calls": tool_trace}
