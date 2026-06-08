import logging
import json

logger = logging.getLogger("AgentHooks")

def before_tool_callback(**kwargs) -> None:
    """Webhook called before a tool is executed by the agent.
    Used for audit logging and strict parameter validation.
    """
    tool = kwargs.get("tool")
    tool_args = kwargs.get("args", {})
    tool_name = getattr(tool, "name", "unknown_tool")
    
    logger.info(f"🔍 ADK Webhook [BEFORE_TOOL]: Executing '{tool_name}' with args: {json.dumps(tool_args)}")
    
    # Active Validation: Enforce security policies before allowing external API calls
    if tool_args:
        for key, value in tool_args.items():
            if isinstance(value, str):
                val_lower = value.lower()
                # Example policy: block attempts to search for restricted/unsafe content
                if any(blocked in val_lower for blocked in ["illegal", "hack", "bypass", "banned"]):
                    logger.warning(f"🚨 Security block triggered in '{tool_name}' for argument '{key}': {value}")
                    raise ValueError(f"Security Policy Violation: Blocked unsafe argument '{value}' in tool '{tool_name}'.")

def after_tool_callback(**kwargs) -> None:
    """Webhook called after a tool has successfully returned a result.
    Used for observability, metrics, and payload monitoring.
    """
    tool = kwargs.get("tool")
    tool_result = kwargs.get("tool_result")
    tool_name = getattr(tool, "name", "unknown_tool")
    
    result_str = str(tool_result)
    
    # Active Monitoring: Track payload sizes to prevent LLM context window overflow
    if len(result_str) > 10000:
        logger.warning(f"⚠️ ADK Webhook [AFTER_TOOL]: HUGE payload from '{tool_name}' ({len(result_str)} chars). This may impact LLM performance.")
    
    # Truncate for the log output to keep terminal clean
    log_safe_result = result_str[:300] + "..." if len(result_str) > 300 else result_str
    logger.info(f"✅ ADK Webhook [AFTER_TOOL]: '{tool_name}' completed safely. (Size: {len(result_str)} chars). Preview: {log_safe_result}")

def on_tool_error_callback(**kwargs) -> str:
    """Webhook called when a tool execution fails.
    Returns a safe string that is passed back to the LLM to prevent the agent loop from crashing.
    """
    tool = kwargs.get("tool")
    error = kwargs.get("error")
    tool_name = getattr(tool, "name", "unknown_tool")
    
    logger.error(f"❌ ADK Webhook [TOOL_ERROR]: '{tool_name}' failed with error: {error}")
    return json.dumps({
        "error": f"The external tool '{tool_name}' failed.",
        "details": str(error),
        "instruction": "Do not attempt to use this tool again. Please continue planning using your general knowledge."
    })
