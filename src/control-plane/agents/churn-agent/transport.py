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
    active_tools = {}  # Track active tool calls by ID

    try:
        yield transport.start_stream()

        async for event in agent.stream_async(user_message):
            # Handle message events
            if "message" in event:
                message = event["message"]
                content = message.get("content", [])

                for item in content:
                    # Handle tool use
                    # logger.info(f"Agent event: {event}")

                    if "toolUse" in item:
                        tool_use = item["toolUse"]
                        tool_name = tool_use["name"]
                        tool_id = tool_use["toolUseId"]
                        tool_input = tool_use.get("input", {})

                        logger.info(f"Tool use: {tool_name}, ID: {tool_id}, input: {tool_input}")

                        # End text block if active before starting tool
                        if text_started:
                            yield transport.end_text_block()
                            text_started = False

                        # New tool call
                        active_tools[tool_id] = {"name": tool_name, "input_dict": tool_input}
                        yield {"type": "tool-input-start", "toolCallId": tool_id, "toolName": tool_name}

                        # Send the complete input as delta
                        input_text = json.dumps(tool_input)
                        yield {"type": "tool-input-delta", "toolCallId": tool_id, "inputTextDelta": input_text}
                        yield {
                            "type": "tool-input-available",
                            "toolCallId": tool_id,
                            "toolName": tool_name,
                            "input": tool_input,
                        }

                    # Handle tool result
                    elif "toolResult" in item:
                        tool_result = item["toolResult"]
                        tool_id = tool_result["toolUseId"]
                        result_content = tool_result.get("content", [])

                        logger.info(f"Tool result: ID: {tool_id}, content: {result_content}")

                        # Extract text from result content
                        result_text = ""
                        for result_item in result_content:
                            if "text" in result_item:
                                result_text += result_item["text"]

                        yield {"type": "tool-output-available", "toolCallId": tool_id, "output": result_text}

                    # Handle text content
                    elif "text" in item:
                        if not text_started:
                            yield transport.start_text_block()
                            text_started = True

                        yield transport.stream_text_delta(item["text"])

        if text_started:
            yield transport.end_text_block()

        yield transport.end_stream()

    except Exception as e:
        yield transport.stream_error(str(e))
        yield transport.end_stream()
