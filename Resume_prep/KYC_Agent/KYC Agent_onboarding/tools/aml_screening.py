import asyncio
import logging

logger = logging.getLogger(__name__)

async def check_aml_database(name: str, id_number: str) -> dict:
    """
    Mock function representing an API call to an AML screening service
    (like Refinitiv World-Check, OFAC, UAE Central Bank).
    """
    logger.info(f"[AML Tool] Checking AML database for name='{name}', id_number='{id_number}'")
    
    # In a real scenario, this would be an aiohttp.ClientSession().post() to the AML provider.
    await asyncio.sleep(0.5) # Simulate API latency
    
    # Mock hardcoded hits (for interview demonstration purposes)
    if name and "osama" in name.lower():
        return {
            "is_match": True,
            "match_score": 0.99,
            "match_detail": "Osama Bin Laden (Alias)",
            "list": "UN Consolidated Sanctions",
            "checked": True
        }
    elif id_number and "999" in id_number:
        return {
            "is_match": True,
            "match_score": 0.85,
            "match_detail": "Watchlist ID Hit",
            "list": "UAE Central Bank Local Watchlist",
            "checked": True
        }
        
    # Default clean response
    return {
        "is_match": False,
        "match_score": 0.0,
        "match_detail": "No match found",
        "checked": True
    }
