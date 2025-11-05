import os
import tempfile
from typing import Optional
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global variable for code interpreter session
_code_context = None


class CodeContext:
    def __init__(self):
        self.region = os.getenv('DSQL_REGION', 'us-east-1')
        self._client = boto3.client('bedrock-agentcore', region_name=self.region)
        self._session_id: Optional[str] = None
    
    async def __aenter__(self):
        """Start code interpreter session"""
        response = self._client.start_code_interpreter_session(
            codeInterpreterIdentifier="aws.codeinterpreter.v1",
            name="churn-agent-session",
            sessionTimeoutSeconds=3600
        )
        self._session_id = response["sessionId"]
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop code interpreter session"""
        if self._session_id:
            self._client.stop_code_interpreter_session(
                codeInterpreterIdentifier="aws.codeinterpreter.v1",
                sessionId=self._session_id
            )
            self._session_id = None
    
    def execute_code(self, code: str, language: str = "python") -> str:
        """Execute code and return formatted results"""
        if not self._session_id:
            return "ERROR: Code interpreter session not started"
        
        try:
            response = self._client.invoke_code_interpreter(
                codeInterpreterIdentifier="aws.codeinterpreter.v1",
                sessionId=self._session_id,
                name="executeCode",
                arguments={
                    "language": language,
                    "code": code
                }
            )
            
            # Extract text output from stream
            output_parts = []
            for event in response["stream"]:
                if "result" in event:
                    result = event["result"]
                    if "content" in result:
                        for content_item in result["content"]:
                            if content_item["type"] == "text":
                                output_parts.append(content_item["text"])
            
            return "\n".join(output_parts) if output_parts else "Code executed successfully (no output)"
            
        except Exception as e:
            return f"Code execution error: {str(e)}"
    
    def upload_file(self, filename: str, content: str) -> str:
        """Upload file to code interpreter session using writeFiles"""
        if not self._session_id:
            return "ERROR: Code interpreter session not started"
        
        try:
            response = self._client.invoke_code_interpreter(
                codeInterpreterIdentifier="aws.codeinterpreter.v1",
                sessionId=self._session_id,
                name="writeFiles",
                arguments={
                    "content": [{"path": filename, "text": content}]
                }
            )
            
            # Extract response
            for event in response["stream"]:
                if "result" in event:
                    return f"File '{filename}' uploaded successfully"
            
            return f"File '{filename}' uploaded"
            
        except Exception as e:
            return f"File upload error: {str(e)}"


def get_code_context() -> CodeContext:
    """Get the current code context"""
    if _code_context is None:
        raise RuntimeError("Code context not set. Initialize with set_code_context() first.")
    return _code_context


def set_code_context(ctx: CodeContext):
    """Set the code context"""
    global _code_context
    _code_context = ctx
