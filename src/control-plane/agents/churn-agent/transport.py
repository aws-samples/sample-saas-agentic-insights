import json
import uuid
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class DataStreamTransport:
    """Real-time streaming transport for AI SDK data stream protocol."""

    def __init__(self):
        self.message_id = str(uuid.uuid4())
        self.current_text_id = None
        self.current_tool_id = None

    def start_stream(self) -> dict:
        return {"type": "start", "messageId": self.message_id}

    def start_text_block(self) -> dict:
        self.current_text_id = str(uuid.uuid4())
        return {"type": "text-start", "id": self.current_text_id}

    def stream_text_delta(self, delta: str) -> dict:
        return {"type": "text-delta", "id": self.current_text_id, "delta": delta}

    def end_text_block(self) -> dict:
        result = {"type": "text-end", "id": self.current_text_id}
        self.current_text_id = None
        return result

    def start_tool_input(self, tool_name: str) -> dict:
        self.current_tool_id = str(uuid.uuid4())
        return {"type": "tool-input-start", "toolCallId": self.current_tool_id, "toolName": tool_name}

    def stream_tool_input_delta(self, delta: str) -> dict:
        return {"type": "tool-input-delta", "toolCallId": self.current_tool_id, "inputTextDelta": delta}

    def tool_input_available(self, tool_name: str, input_data: dict) -> dict:
        return {
            "type": "tool-input-available",
            "toolCallId": self.current_tool_id,
            "toolName": tool_name,
            "input": input_data,
        }

    def tool_output_available(self, output: str) -> dict:
        return {"type": "tool-output-available", "toolCallId": self.current_tool_id, "output": output}

    def stream_error(self, error_text: str) -> dict:
        return {"type": "error", "errorText": error_text}

    def end_stream(self) -> dict:
        return {"type": "finish"}


async def stream_agent_response(agent, user_message: str) -> AsyncGenerator[dict, None]:
    """Stream agent response using data stream protocol."""
    transport = DataStreamTransport()
    text_started = False
    active_tools = {}

    try:
        yield transport.start_stream()

        async for event in agent.stream_async(user_message):
            # Handle text data
            if "data" in event:
                if not text_started:
                    yield transport.start_text_block()
                    text_started = True
                yield transport.stream_text_delta(event["data"])

            # Handle streaming tool use
            if "current_tool_use" in event:
                current_tool = event["current_tool_use"]
                tool_id = current_tool["toolUseId"]
                tool_name = current_tool["name"]
                
                # End text block if active before starting tool
                if text_started:
                    yield transport.end_text_block()
                    text_started = False

                # Start new tool if not already tracked
                if tool_id not in active_tools:
                    active_tools[tool_id] = {"name": tool_name, "started": True}
                    yield transport.start_tool_input(tool_name)

                # Stream tool input delta
                if "delta" in event and "toolUse" in event["delta"] and "input" in event["delta"]["toolUse"]:
                    delta_input = event["delta"]["toolUse"]["input"]
                    yield transport.stream_tool_input_delta(delta_input)

                # Check if tool input is complete
                tool_input = current_tool.get("input", "")
                if tool_input and tool_input.endswith("}"):
                    try:
                        input_data = json.loads(tool_input)
                        yield transport.tool_input_available(tool_name, input_data)
                    except json.JSONDecodeError:
                        pass

            # Handle tool results
            if "message" in event:
                message = event["message"]
                content = message.get("content", [])
                
                for item in content:
                    if "toolResult" in item:
                        tool_result = item["toolResult"]
                        tool_id = tool_result["toolUseId"]
                        result_content = tool_result.get("content", [])
                        
                        result_text = ""
                        for result_item in result_content:
                            if "text" in result_item:
                                result_text += result_item["text"]
                        
                        yield transport.tool_output_available(result_text)

        if text_started:
            yield transport.end_text_block()

        yield transport.end_stream()

    except Exception as e:
        yield transport.stream_error(str(e))
        yield transport.end_stream()
