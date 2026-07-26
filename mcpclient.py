# Libraries for MCP client, LLM handling, and async operations
import asyncio
import json
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import (
    Root,
    TextContent,
    CreateMessageResult,
    CreateMessageRequestParams,
)
from config import gemini_client

# Configuration
SERVER_SCRIPT = str(Path(__file__).parent / "server.py")
PROJECT_DIR = Path(__file__).parent.resolve()


# StdioServerParameters launches "python server.py" via stdin/stdout
#to establish connection with server
server_params = StdioServerParameters(
    command="python",
    args=[SERVER_SCRIPT],
)


# ROOTS — Tell the server which directories it can access
def list_roots() -> list[Root]:
    """Limit the server's file access to this project directory."""
    return [Root(uri=f"file://{PROJECT_DIR}", name=PROJECT_DIR.name)]


# SAMPLING — Handle LLM requests delegated from the server
async def handle_sampling(params: CreateMessageRequestParams) -> CreateMessageResult:
    """Run a Gemini LLM call on behalf of the server and return the result."""
    
    # 1. Safely extract prompt text from the messages sequence
    first_message = params.messages[0]
    
    # Handle whether content comes in as a string or an object list
    if isinstance(first_message.content, str):
        prompt = first_message.content
    elif isinstance(first_message.content, list):
        prompt = first_message.content[0].text
    else:
        prompt = getattr(first_message.content, "text", str(first_message.content))

    print(f"\n[Sampling] Server requested LLM task:")
    print(f"  Prompt preview: {prompt[:150]}...")

    # 2. Call Gemini (Using your configuration instance)
    response = gemini_client.messages.create(
        model="gemini-2.5-flash",
        max_tokens=params.maxTokens or 200,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text
    print(f"  LLM Response: {response_text[:100]}...")

    # 3. Return structural response compliant with the low-level MCP SDK schema
    return CreateMessageResult(
        role="assistant",
        content=[  # MUST be an array/list
            TextContent(
                type="text", 
                text=response_text
            )
        ],
        model="gemini-2.5-flash",
        stopReason="endTurn"  # Add to satisfy required schema validation
    )


# HELPER — Open a session, call a tool, and return the parsed JSON result
async def call_tool(tool_name: str, arguments: dict) -> dict:
    """Connect to the server, call a tool, and return the parsed JSON result."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read,
            write,
            sampling_callback=handle_sampling,
            list_roots_callback=list_roots,
        ) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            # The server always returns a single TextContent item
            return json.loads(result.content[0].text)


# CONNECTION & DISCOVERY
async def verify_connection():
    """Connect to the server and verify all expected tools and resources exist."""
    print("=" * 60)
    print("MCP Connection Verification")
    print("=" * 60)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read,
            write,
            sampling_callback=handle_sampling,
            list_roots_callback=list_roots,
        ) as session:
            await session.initialize()

            # list_tools() sends a "tools/list" JSON-RPC request to the server
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            print("--- START SCREENSHOT ---")
            print(f"\nDiscovered {len(tool_names)} tools:")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description[:80]}...")

            assert "get_restaurant_info" in tool_names, "FAIL: get_restaurant_info not found!"
            assert "recommend_by_vibe" in tool_names, "FAIL: recommend_by_vibe not found!"
            assert "get_review" in tool_names, "FAIL: get_review not found!"
            print("\nAll required tools verified!")

            # list_resources() discovers data endpoints the server exposes
            resources_result = await session.list_resources()
            print(f"\nDiscovered {len(resources_result.resources)} resources:")
            for resource in resources_result.resources:
                print(f"  - {resource.uri}: {resource.name}")

            roots = list_roots()
            print(f"\nConfigured {len(roots)} roots:")
            for root in roots:
                print(f"  - {root.name}: {root.uri}")



# DEMOS — Call each tool through the MCP protocol
async def demo_get_restaurant_info():
    """Demo: Look up a restaurant by name."""
    print("\n" + "-" * 60)
    print("Demo: get_restaurant_info('Iron & Embers')")
    print("-" * 60)

    data = await call_tool("get_restaurant_info", {"restaurant_name": "Iron & Embers"})
    print(json.dumps(data, indent=2))



async def demo_recommend_by_vibe():
    """Demo: Find restaurants by vibe keyword."""
    print("\n" + "-" * 60)
    print("Demo: recommend_by_vibe('moody')")
    print("-" * 60)

    data = await call_tool("recommend_by_vibe", {"vibe": "moody"})
    print(f"Vibe: {data['vibe_searched']}")
    print(f"Structured matches: {len(data['structured_matches'])}")
    for match in data["structured_matches"]:
        print(f"  - {match['name']} ({match['cuisine']}) - {match['rating']}/5")
    print(f"Raw text excerpts: {len(data['raw_text_excerpts'])}")



async def demo_get_review():
    """Demo: Retrieve a restaurant review."""
    print("\n" + "-" * 60)
    print("Demo: get_review('Iron & Embers')")
    print("-" * 60)

    data = await call_tool("get_review", {"restaurant_name": "Iron & Embers"})
    print(json.dumps(data, indent=2))



# Main Entry Point
async def main():
    """Run all demos sequentially."""
    await demo_get_restaurant_info() #TODO
    await demo_recommend_by_vibe() #TODO
    await demo_get_review() #TODO
    await verify_connection()

if __name__ == "__main__":
    asyncio.run(main())






