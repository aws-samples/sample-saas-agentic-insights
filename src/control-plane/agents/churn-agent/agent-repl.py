#!/usr/bin/env python3

import argparse
import ast
import asyncio
import importlib
import json
import logging
import os
import readline
import traceback
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
import agent as agent_module
from db_context import DbContext, set_db_context
from code_context import CodeContext, set_code_context

console = Console()


async def run_session(db_ctx: DbContext, code_ctx: CodeContext) -> bool:
    """Run REPL session. Returns True if session should restart, False to exit."""
    set_db_context(db_ctx)
    set_code_context(code_ctx)
    
    # Setup readline history
    history_file = os.path.expanduser("~/.churn_agent_history")
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass

    current_agent = agent_module.agent

    while True:
        try:
            user_input = input("\n>>> ").strip()

            if user_input.lower() in ["/quit", "/exit"]:
                readline.remove_history_item(readline.get_current_history_length() - 1)
                readline.write_history_file(history_file)
                print("Goodbye!")
                return False

            if user_input.lower() == "/clear":
                readline.remove_history_item(readline.get_current_history_length() - 1)
                print("Restarting session...")
                return True

            if user_input.lower() == "/reload":
                readline.remove_history_item(readline.get_current_history_length() - 1)
                importlib.reload(agent_module)
                current_agent = agent_module.agent
                print("Agent reloaded, restarting session...")
                return True

            if not user_input:
                continue

            with Live(
                renderable=Panel("Thinking...", title="Agent Response", title_align="right"),
                console=console,
                refresh_per_second=4,
            ) as live:
                try:
                    conversation = []

                    async for event in current_agent.stream_async(user_input):
                        # Track tool usage
                        if "current_tool_use" in event and event["current_tool_use"].get("name"):
                            tool_use = event["current_tool_use"]
                            tool_name = tool_use["name"]
                            tool_id = tool_use.get("toolUseId", "")
                            tool_input = tool_use.get("input", {})

                            # Special formatting for execute_python tool
                            if tool_name == "execute_python" and isinstance(tool_input, dict) and "code" in tool_input and tool_input["code"]:
                                input_str = f"```python\n{tool_input['code']}\n```"
                            elif tool_name == "execute_python":
                                # Show other parameters normally for execute_python
                                if isinstance(tool_input, dict):
                                    input_str = ", ".join(
                                        [f'{k}={v}' for k, v in tool_input.items()]
                                    )
                                else:
                                    input_str = str(tool_input)
                            else:
                                # Format input parameters normally for other tools
                                if isinstance(tool_input, dict):
                                    input_str = ", ".join(
                                        [f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}" for k, v in tool_input.items()]
                                    )
                                else:
                                    input_str = str(tool_input)

                            # Check if last item is same tool call, update or add new
                            if (
                                conversation
                                and conversation[-1].get("type") == "tool_call"
                                and conversation[-1].get("id") == tool_id
                            ):
                                conversation[-1]["input"] = input_str
                            else:
                                conversation.append(
                                    {"type": "tool_call", "tool_name": tool_name, "id": tool_id, "input": input_str}
                                )

                        # Handle text data
                        if "data" in event:
                            # Check if last item is text, update or add new
                            if conversation and conversation[-1].get("type") == "text":
                                conversation[-1]["content"] += event["data"]
                            else:
                                conversation.append({"type": "text", "content": event["data"]})

                        # Synthesize content from conversation array
                        renderables = []
                        for item in conversation:
                            if item["type"] == "text":
                                renderables.append(Markdown(item["content"]))
                            elif item["type"] == "tool_call":
                                # Check if this is a complete execute_python call with valid JSON
                                if (item["tool_name"] == "execute_python" and 
                                    item["input"].startswith('{"') and 
                                    item["input"].endswith('"}') and
                                    '"code":' in item["input"]):
                                    
                                    try:
                                        input_dict = json.loads(item["input"])
                                        if "code" in input_dict and input_dict["code"]:
                                            # Render as code block
                                            tool_header = Text()
                                            tool_header.append(f"\n\nTool Call: ")
                                            tool_header.append(item["tool_name"], style="bold")
                                            tool_header.append(f" ({item['id']})\nInput:\n")
                                            renderables.append(tool_header)
                                            
                                            code = input_dict["code"].replace("\\n", "\n").replace("\\t", "\t")
                                            code_block = f"```python{code}\n```"
                                            renderables.append(Markdown(code_block))
                                            renderables.append(Text("\n"))
                                            continue
                                    except:
                                        pass
                                
                                # Regular tool call formatting (including incomplete execute_python)
                                tool_text = Text()
                                tool_text.append(f"\n\nTool Call: ")
                                tool_text.append(item["tool_name"], style="bold")
                                tool_text.append(f" ({item['id']})\nInput: ")
                                tool_text.append(f"{item['input']}\n\n", style="yellow")
                                renderables.append(tool_text)

                        # Update the panel
                        live.update(
                            Panel(
                                Group(*renderables) if renderables else "Thinking...",
                                title="Agent Response",
                                title_align="right",
                            )
                        )

                except Exception as e:
                    live.update(
                        Panel(
                            f"Error: {str(e)}\n\n{traceback.format_exc()}",
                            title="Error",
                            title_align="right",
                        )
                    )

        except KeyboardInterrupt:
            readline.write_history_file(history_file)
            print("\nGoodbye!")
            return False
        except EOFError:
            readline.write_history_file(history_file)
            print("\nGoodbye!")
            return False
        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())
            continue


async def main():
    parser = argparse.ArgumentParser(description="Churn Agent REPL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        logging.getLogger("strands").setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARN, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("Churn Agent REPL - Type '/quit', '/exit', '/clear', or '/reload'")
    print("-" * 50)

    # Initialize database context once
    try:
        db_ctx = DbContext()
        print("✓ Database context initialized")
    except Exception as e:
        print(f"✗ Database context initialization failed: {e}")
        return

    # Main session loop
    while True:
        code_ctx = CodeContext()
        async with code_ctx:
            print("✓ Code interpreter session started")
            
            should_restart = await run_session(db_ctx, code_ctx)
            if not should_restart:
                break
    
    print("REPL session ended")


if __name__ == "__main__":
    asyncio.run(main())
