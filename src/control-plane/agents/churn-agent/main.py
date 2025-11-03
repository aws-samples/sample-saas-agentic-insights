from bedrock_agentcore import BedrockAgentCoreApp
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from agent import agent
from transport import stream_agent_response
from db_context import DbContext, set_db_context
from code_context import CodeContext, set_code_context
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app):
    # Startup
    try:
        db_ctx = DbContext()
        set_db_context(db_ctx)
        logger.info("Database context initialized")

        async with CodeContext() as code_ctx:
            set_code_context(code_ctx)
            logger.info("Code interpreter context initialized")

            yield

            logger.info("Code interpreter context cleaned up")
    except Exception as e:
        logger.error(f"Context initialization failed: {e}")
        yield


app = BedrockAgentCoreApp(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.entrypoint
async def invoke(payload):
    """Your AI agent function"""
    logger.debug(f"PAYLOAD STRUCTURE: {payload}")

    # Extract the latest user message from messages array
    messages = payload.get("messages", [])
    if not messages:
        return {"error": "No messages provided"}

    # Get the last user message
    last_message = messages[-1]
    if last_message.get("role") != "user":
        return {"error": "Last message must be from user"}

    # Extract text from parts
    parts = last_message.get("parts", [])
    text_parts = [part.get("text", "") for part in parts if part.get("type") == "text"]
    user_message = " ".join(text_parts).strip()

    if not user_message:
        return {"error": "No text content found"}

    return stream_agent_response(agent, user_message)


if __name__ == "__main__":
    app.run()
