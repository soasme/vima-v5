#!/usr/bin/env python3
import json
import sys
import os
import subprocess
from typing import Dict, List, Optional, Any, Union, TypedDict, Literal

# Define schema types
class ToolInputSchema(TypedDict):
    type: str
    properties: Dict[str, Any]
    required: List[str]

class Tool(TypedDict):
    name: str
    description: str
    inputSchema: ToolInputSchema

class ChatGPTArgs(TypedDict, total=False):
    operation: Literal["ask", "get_conversations"]
    prompt: Optional[str]
    conversation_id: Optional[str]

class TextContent(TypedDict):
    type: str
    text: str

class ToolResponse(TypedDict):
    content: List[TextContent]
    isError: bool

# Define the ChatGPT tool
CHATGPT_TOOL: Tool = {
    "name": "chatgpt",
    "description": "Interact with the ChatGPT desktop app on macOS",
    "inputSchema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Operation to perform: 'ask' or 'get_conversations'",
                "enum": ["ask", "get_conversations"]
            },
            "prompt": {
                "type": "string",
                "description": "The prompt to send to ChatGPT (required for ask operation)"
            },
            "conversation_id": {
                "type": "string",
                "description": "Optional conversation ID to continue a specific conversation"
            }
        },
        "required": ["operation"]
    }
}

# Model Context Protocol Server implementation
class Server:
    def __init__(self, metadata: Dict[str, str], config: Dict[str, Any]):
        self.metadata = metadata
        self.config = config
        self.request_handlers = {}
    
    def set_request_handler(self, schema_type: str, handler):
        self.request_handlers[schema_type] = handler
    
    async def handle_request(self, request_str: str) -> str:
        request = json.loads(request_str)
        method = request.get("method")
        
        if method == "listTools":
            handler = self.request_handlers.get("listTools")
            if handler:
                result = await handler(request)
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result
                })
                
        elif method == "callTool":
            handler = self.request_handlers.get("callTool")
            if handler:
                result = await handler(request)
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result
                })
        
        return json.dumps({
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {"message": f"Unknown method: {method}"}
        })
    
    async def connect(self, transport):
        return await transport.start(self)

class StdioServerTransport:
    async def start(self, server):
        print("ChatGPT MCP Server running on stdio", file=sys.stderr)
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                # Process the request
                response = await server.handle_request(line.strip())
                
                # Write response with content length header
                content_length = len(response.encode('utf-8'))
                print(f"Content-Length: {content_length}", flush=True)
                print("", flush=True)  # Empty line
                print(response, flush=True)
                
            except Exception as e:
                print(f"Error processing request: {str(e)}", file=sys.stderr)

# Helper functions for interacting with ChatGPT app
def run_apple_script(script: str) -> str:
    """Run an AppleScript and return the result."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"AppleScript error: {e.stderr}", file=sys.stderr)
        raise RuntimeError(f"AppleScript execution failed: {e.stderr}")

async def check_chatgpt_access() -> bool:
    """Check if ChatGPT app is installed and running."""
    try:
        is_running = run_apple_script("""
            tell application "System Events"
                return application process "ChatGPT" exists
            end tell
        """)
        
        if is_running != "true":
            print("ChatGPT app is not running, attempting to launch...", file=sys.stderr)
            try:
                run_apple_script("""
                    tell application "ChatGPT" to activate
                    delay 2
                """)
            except Exception as e:
                print(f"Error activating ChatGPT app: {str(e)}", file=sys.stderr)
                raise RuntimeError("Could not activate ChatGPT app. Please start it manually.")
        
        return True
    except Exception as e:
        print(f"ChatGPT access check failed: {str(e)}", file=sys.stderr)
        raise RuntimeError(
            f"Cannot access ChatGPT app. Please make sure ChatGPT is installed and properly configured. Error: {str(e)}"
        )

async def ask_chatgpt(prompt: str, conversation_id: Optional[str] = None) -> str:
    """Send a prompt to ChatGPT and get the response."""
    await check_chatgpt_access()
    
    try:
        # Escape double quotes in the prompt for AppleScript
        safe_prompt = prompt.replace('"', '\\"')
        
        conversation_script = ""
        if conversation_id:
            conversation_script = f"""
            -- Try to find and click the specified conversation
            try
              click button "{conversation_id}" of group 1 of group 1 of window 1
              delay 1
            end try
            """
        
        result = run_apple_script(f"""
            tell application "ChatGPT"
                activate
                delay 1
                
                tell application "System Events"
                    tell process "ChatGPT"
                        {conversation_script}
                        
                        -- Type in the prompt
                        keystroke "{safe_prompt}"
                        delay 0.5
                        keystroke return
                        delay 5  -- Wait for response, adjust as needed
                        
                        -- Try to get the response (this is approximate and may need adjustments)
                        set responseText to ""
                        try
                            set responseText to value of text area 2 of group 1 of group 1 of window 1
                        on error
                            set responseText to "Could not retrieve the response from ChatGPT."
                        end try
                        
                        return responseText
                    end tell
                end tell
            end tell
        """)
        
        return result
    except Exception as e:
        print(f"Error interacting with ChatGPT: {str(e)}", file=sys.stderr)
        raise RuntimeError(f"Failed to get response from ChatGPT: {str(e)}")

async def get_conversations() -> List[str]:
    """Get list of available conversations in ChatGPT."""
    await check_chatgpt_access()
    
    try:
        result = run_apple_script("""
            tell application "ChatGPT"
                activate
                delay 1
                
                tell application "System Events"
                    tell process "ChatGPT"
                        -- Try to get conversation titles
                        set conversationsList to {}
                        
                        try
                            set chatButtons to buttons of group 1 of group 1 of window 1
                            repeat with chatButton in chatButtons
                                set buttonName to name of chatButton
                                if buttonName is not "New chat" then
                                    set end of conversationsList to buttonName
                                end if
                            end repeat
                        on error errStr number errorNumber
                            set conversationsList to errStr
                        end try
                        
                        return conversationsList
                    end tell
                end tell
            end tell
        """)
        
        # Parse the AppleScript result into a list
        if result:
            conversations = [conv.strip() for conv in result.split(",")]
            return conversations
        return ["No conversations found"]
    except Exception as e:
        print(f"Error getting ChatGPT conversations: {str(e)}", file=sys.stderr)
        return ["Error retrieving conversations"]

def is_chatgpt_args(args: Any) -> bool:
    """Validate arguments for the ChatGPT tool."""
    if not isinstance(args, dict):
        return False
    
    operation = args.get("operation")
    prompt = args.get("prompt")
    conversation_id = args.get("conversation_id")
    
    if not operation or operation not in ["ask", "get_conversations"]:
        return False
    
    # Validate required fields based on operation
    if operation == "ask" and not prompt:
        return False
    
    # Validate field types if present
    if prompt is not None and not isinstance(prompt, str):
        return False
    if conversation_id is not None and not isinstance(conversation_id, str):
        return False
    
    return True

async def main():
    # Initialize the server
    server = Server(
        metadata={"name": "ChatGPT MCP Tool", "version": "1.0.0"},
        config={"capabilities": {"tools": {}}}
    )
    
    # Set up request handlers
    server.set_request_handler("listTools", lambda _: {"tools": [CHATGPT_TOOL]})
    
    async def handle_call_tool(request):
        try:
            params = request.get("params", {})
            name = params.get("name")
            args = params.get("arguments")
            
            if not args:
                raise ValueError("No arguments provided")
            
            if name == "chatgpt":
                if not is_chatgpt_args(args):
                    raise ValueError("Invalid arguments for ChatGPT tool")
                
                operation = args.get("operation")
                
                if operation == "ask":
                    prompt = args.get("prompt")
                    if not prompt:
                        raise ValueError("Prompt is required for ask operation")
                    
                    conversation_id = args.get("conversation_id")
                    response = await ask_chatgpt(prompt, conversation_id)
                    
                    return {
                        "content": [{"type": "text", "text": response or "No response received from ChatGPT."}],
                        "isError": False
                    }
                
                elif operation == "get_conversations":
                    conversations = await get_conversations()
                    
                    return {
                        "content": [{
                            "type": "text",
                            "text": (
                                f"Found {len(conversations)} conversation(s):\n\n{chr(10).join(conversations)}"
                                if conversations else "No conversations found in ChatGPT."
                            )
                        }],
                        "isError": False
                    }
                
                else:
                    raise ValueError(f"Unknown operation: {operation}")
            
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True
            }
        
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }
    
    server.set_request_handler("callTool", handle_call_tool)
    
    # Start the server with stdio transport
    transport = StdioServerTransport()
    await server.connect(transport)

# Use asyncio to run the async main function
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
