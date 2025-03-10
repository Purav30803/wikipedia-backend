from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from db.connect_db import get_db
from schema.wikipedia_schema import SearchModel
from service.wikipedia_service import search_in_model_service,get_on_this_day_data
from loguru import logger
from fastapi import Header
from typing import Optional

wikipedia_router = APIRouter()

@wikipedia_router.post("/search", summary="Search in a model")
async def search_in_model(
    search: SearchModel,
    db: Session = Depends(get_db),
    request: Request = None,    
    user_agent: Optional[str] = Header(None)
):
    # Extract client's IP address
    ip_address = request.headers.get('X-Forwarded-For', request.client.host)
    if isinstance(ip_address, str) and ',' in ip_address:
        ip_address = ip_address.split(',')[0]
    
    # Log the search query, IP address, and User-Agent
    logger.info(f"Received search query: '{search.search}' from IP: {ip_address} using User-Agent: {user_agent}")
    
    try:
        # Perform the search and store the result
        result = search_in_model_service(search.search, db, ip_address, user_agent)
        return result
    except Exception as e:
        logger.error(f"Failed to process search: {e}")
        return {"error": str(e)}


@wikipedia_router.get("/on-this-day", summary="Get search history")
def on_this_day():
    logger.info("Received request for on this day data.")
    try:
        result = get_on_this_day_data()
        return result
    except Exception as e:
        logger.error(f"Failed to get on this day data: {e}")
        return {"error": str(e)}