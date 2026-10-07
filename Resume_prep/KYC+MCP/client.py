import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_kyc_agent_flow():
    """
    A simulated Agent Client that connects to the KYC MCP server via stdio 
    and requests tool executions.
    """
    # 1. Define how to start the MCP server
    # We use python to run mcp_server.py in the standard system process
    server_params = StdioServerParameters(
        command=sys.executable, # Use the current python interpreter
        args=["mcp_server.py"],
    )

    print("Connecting to KYC MCP Server...")
    
    # 2. Connect client to server via stdio
    async with stdio_client(server_params) as (read, write):
        # 3. Create an MCP session
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Session initialized successfully.\n")
            
            # --- AGENT LOGIC SIMULATION ---
            
            # Agent discovers tools
            tools_response = await session.list_tools()
            print("Agent Discovered Available KYC Tools:")
            for tool in tools_response.tools:
                print(f"- {tool.name}: {tool.description}")
            print("-" * 40)
            
            # Agent step 1: Extract Document data
            print("\n[Agent] Executing tool: extract_id_data...")
            id_result = await session.call_tool(
                "extract_id_data", 
                arguments={"image_path": "/uploads/user123_passport.jpg"}
            )
            # The result is returned as an array of structured text/media blocks
            extracted_data = id_result.content[0].text
            print(f"Result: {extracted_data}")

            # Agent step 2: From the Extracted Data, the agent calls Sanction Screening
            print("\n[Agent] Executing tool: screen_user_aml...")
            aml_result = await session.call_tool(
                "screen_user_aml", 
                arguments={"name": "John Doe"}
            )
            print(f"Result: {aml_result.content[0].text}")
            
            print("\n[Agent] KYC Flow Completed.")

if __name__ == "__main__":
    asyncio.run(run_kyc_agent_flow())
