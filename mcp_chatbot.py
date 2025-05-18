from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List, Dict, TypedDict
from contextlib import AsyncExitStack
import json
import asyncio

load_dotenv()

class ToolDefinition(TypedDict):
    name: str
    description: str
    input_schema: dict

class PromptDefinition(TypedDict):
    name: str
    description: str
    input_schema: dict

class MCP_ChatBot:

    def __init__(self):
        self.sessions: List[ClientSession] = []
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.available_tools: List[ToolDefinition] = []
        self.tool_to_session: Dict[str, ClientSession] = {}
        self.resource_uris: Dict[str, ClientSession] = {}
        self.prompt_defs: Dict[str, Dict] = {}
        self.prompt_to_session: Dict[str, ClientSession] = {}

    async def connect_to_server(self, server_name: str, server_config: dict) -> None:
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.sessions.append(session)
            # List tools
            tools_response = await session.list_tools()
            tools = tools_response.tools
            print(f"\nConnected to {server_name} with tools:", [t.name for t in tools])
            for tool in tools:
                self.tool_to_session[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
            # List resources
            try:
                res = await session.list_resources()
                for r in res.resources:
                    self.resource_uris[r.uri] = session
            except Exception as e:
                print(f"Could not fetch resources from {server_name}: {e}")
            # List prompts
            try:
                prompts_resp = await session.list_prompts()
                for p in prompts_resp.prompts:
                    self.prompt_defs[p.name] = {
                        "description": p.description,
                        "input_schema": p.inputSchema
                    }
                    self.prompt_to_session[p.name] = session
            except Exception as e:
                print(f"Could not fetch prompts from {server_name}: {e}")
        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")

    async def connect_to_servers(self):
        try:
            with open("server_config.json", "r") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server configuration: {e}")
            raise

    async def get_resource(self, uri):
        session = self.resource_uris.get(uri)
        if not session:
            print(f"No session found for resource URI: {uri}")
            return
        response = await session.get_resource(uri)
        print(response.content)

    async def list_prompts(self):
        if not self.prompt_defs:
            print("No prompts available.")
        else:
            print("\nAvailable Prompts:")
            for name, info in self.prompt_defs.items():
                print(f"- {name}: {info['description']}")

    async def execute_prompt(self, prompt_name, args):
        session = self.prompt_to_session.get(prompt_name)
        if not session:
            print(f"No session found for prompt: {prompt_name}")
            return
        try:
            response = await session.call_prompt(prompt_name, arguments=args)
            print(f"\nPrompt [{prompt_name}] result:\n{response.content}")
        except Exception as e:
            print(f"Error executing prompt {prompt_name}: {e}")

    async def process_query(self, query):
        messages = [{'role': 'user', 'content': query}]
        response = self.anthropic.messages.create(
            max_tokens=2024,
            model='claude-3-7-sonnet-20250219',
            tools=self.available_tools,
            messages=messages
        )
        process_query = True
        while process_query:
            assistant_content = []
            for content in response.content:
                if content.type == 'text':
                    print(content.text)
                    assistant_content.append(content)
                    if (len(response.content) == 1):
                        process_query = False
                elif content.type == 'tool_use':
                    assistant_content.append(content)
                    messages.append({'role': 'assistant', 'content': assistant_content})
                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name
                    print(f"Calling tool {tool_name} with args {tool_args}")
                    session = self.tool_to_session[tool_name]
                    result = await session.call_tool(tool_name, arguments=tool_args)
                    messages.append({"role": "user",
                                     "content": [{
                                         "type": "tool_result",
                                         "tool_use_id": tool_id,
                                         "content": result.content
                                     }]
                                    })
                    response = self.anthropic.messages.create(
                        max_tokens=2024,
                        model='claude-3-7-sonnet-20250219',
                        tools=self.available_tools,
                        messages=messages
                    )
                    if (len(response.content) == 1 and response.content[0].type == "text"):
                        print(response.content[0].text)
                        process_query = False

    async def chat_loop(self):
        print("\nMCP Chatbot Started!")
        print("Type your queries, '@folders' or '@topic', '/prompts', '/prompt <name> <arg1=val1>' or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                elif query.startswith('@'):
                    # Resource
                    if query == '@folders':
                        await self.get_resource("papers://folders")
                    else:
                        topic = query[1:]
                        await self.get_resource(f"papers://{topic}")
                elif query.startswith('/prompts'):
                    await self.list_prompts()
                elif query.startswith('/prompt'):
                    tokens = query.split()
                    if len(tokens) >= 2:
                        prompt_name = tokens[1]
                        args = {}
                        for t in tokens[2:]:
                            if '=' in t:
                                k, v = t.split('=', 1)
                                try:
                                    v = int(v)
                                except ValueError:
                                    pass
                                args[k] = v
                        await self.execute_prompt(prompt_name, args)
                    else:
                        print("Usage: /prompt <name> <arg1=val1>")
                else:
                    await self.process_query(query)
                    print("\n")
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    chatbot = MCP_ChatBot()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
