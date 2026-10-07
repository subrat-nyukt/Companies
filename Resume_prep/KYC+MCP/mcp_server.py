from fastmcp import FastMCP
from kyc_logic import extract_identity_info, run_sanction_screening, verify_liveness

# Initialize the MCP Server
mcp = FastMCP("KYC_Agent_Server")

@mcp.tool()
def extract_id_data(image_path: str) -> dict:
    """
    Extracts PII and Identity Data from an ID document image (Passport, License, etc.).
    
    Args:
        image_path: The local path or URL to the identity document image.
    """
    return extract_identity_info(image_path)

@mcp.tool()
def screen_user_aml(name: str) -> dict:
    """
    Checks the provided full name against Anti-Money Laundering (AML) and Sanctions watchlists.
    
    Args:
        name: The full legal name of the user to check.
    """
    return run_sanction_screening(name)

@mcp.tool()
def check_liveness(video_path: str) -> dict:
    """
    Verifies that the user in the video is a live person to prevent spoofing.
    
    Args:
        video_path: Path to the user's selfie video.
    """
    return verify_liveness(video_path)

if __name__ == "__main__":
    # fastmcp uses purely stdio by default for secure local connections, 
    # but can be configured for SSE over http if connecting remotely.
    print("Starting KYC MCP Server...", flush=True)
    mcp.run()
