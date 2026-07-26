import os
from pathlib import Path
from fastmcp.client import Client, PythonStdioTransport
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from config import gemini_client

# Configuration
SERVER_SCRIPT = str(Path(__file__).parent / "server.py")
SYSTEM_PROMPT = """Your name is Connoisseir Companion.
You have access to the database of california restaurants.
You can do the following:
 -use get_restaurant_info to look up specific restaurants by name
 -use recommend_by_vibe to find restaurants matching a mood or atmosphere
 -use get_review to retrieve detailed reviews of restaurants
"""

# MCP Host — ReAct Agent Loop
async def chat_with_agent(user_message: str, history: list) -> str:
    """Connect to the MCP server, discover tools, and run a ReAct loop.
    The LLM decides which tools to call, calls them via the MCP server,
    and repeats until it produces a final text response."""
    transport = PythonStdioTransport(script_path=SERVER_SCRIPT)

    async with Client(transport) as client:
        # Discover available tools from the MCP server
        mcp_tools = await client.list_tools()

        # Convert MCP tool schemas to OpenAI-style tool definitions for the LLM
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema,
                },
            }
            for t in mcp_tools
        ]



        # Build the message list from chat history and the new user message
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user" and content:
                messages.append(HumanMessage(content=content))
            elif role == "assistant" and content:
                messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=user_message))

        # ReAct loop — call tools until the LLM returns a plain text reply
        for _ in range(10):
            #response = await gemini_client.ainvoke(messages)
            response = gemini_client.chat.completions.create(
                    model="gemini-2.5-flash",
                    messages=messages,
                )
            messages.append(response.choices[0].message.content)

            # No tool calls means the LLM is done — return the final response
            if not response.tool_calls:
                raw = response.content
                if isinstance(raw, list): #if llm response is a list of dict, get item["text"] and convert to string by joining the values, else just convert the response.content to string type. Essentially, if no tool call is there, return llm response with strict type string
                    return " ".join(
                        b.get("text", "") if isinstance(b, dict) else str(b)
                        for b in raw
                    )
                return str(raw)

            # Execute each tool call via the MCP server and feed results back
            for tool_call in response.tool_calls:
                result = await client.call_tool(tool_call["name"], tool_call["args"])
                tool_output = " ".join(
                    item.text if hasattr(item, "text") else str(item)
                    for item in result.content
                ) if result.content else "(no result)"
                messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))
                #append the toolMessage in the message history as well

        return "I wasn't able to complete that request. Please try again."
