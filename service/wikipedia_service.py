import requests
from sqlalchemy.orm import Session
from loguru import logger
from typing import Optional
from models.search import SearchHistory
import datetime
from datetime import datetime
from config.env import Env
from utils.wikipedia_helper import get_region_from_ip, get_wikipedia_features

# Function to handle search query and store it in the database
def search_in_model_service(search: str, db: Session, ip_address: str, user_agent: Optional[str]):
    logger.info(f"Received search query: '{search}' from IP: {ip_address} using User-Agent: {user_agent}")
    
    # check if the search query is empty
    if not search:
        return {"error": "Search query cannot be empty"}
    
    # check if search query is wikepedia url (https is optional)
    if not search.startswith("https://en.wikipedia.org/wiki/") and not search.startswith("en.wikipedia.org/wiki/"):
        return {"error": "Search query must be a valid Wikipedia URL"}
    
    try:
        # Placeholder search logic: assuming the search result is "positive"
        search_result = "positive"
        data = get_wikipedia_features(search)
        ip=Env.ALLOW_IP or "No"
        # Get region based on the IP address
        if ip=="Yes":
            region_data = get_region_from_ip(ip_address)
        else:
            region_data = 'DUMMY REGION'
        
        # Create a new SearchHistory record to store the search information in the database
        search_history = SearchHistory(
            ip_address=ip_address,
            search_query=search,
            result=search_result,
            user_agent=user_agent,
            region=region_data,
            wikipedia_data=data
        )
        
        # Add the search history record to the session and commit to the database
        db.add(search_history)
        db.commit()
        db.refresh(search_history)
        
        # Log success and return a response with the result
        logger.info(f"Search result stored for query '{search}' from IP: {ip_address}")
        return {
            "search_results": search_result,
            "ip_address": ip_address,
            "region": region_data,
            "user_agent": user_agent,
            "data": data
        }
    except Exception as e:
        # Log error and rollback in case of any failure
        logger.error(f"Error occurred while processing search '{search}': {e}")
        db.rollback()
        return {"error": f"Failed to perform search: {e}"}
  

def get_on_this_day_data():
    # Get the current date
    today = datetime.today()
    
    # Get the current month and day
    month = today.month
    day = today.day
    
    # Format the month and day to two digits (e.g., "03" for March)
    formatted_month = f"{month:02d}"
    formatted_day = f"{day:02d}"
    
    # Construct the API URL with the formatted month and day
    url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{formatted_month}/{formatted_day}"
    
    # Send the request to the Wikipedia API
    response = requests.get(url)
    
    if response.status_code == 200:
        raw_data = response.json()
        
        # Process and extract important data for frontend
        data = []
        
        # Process each section of the API response
        for category, items in raw_data.items():
            if isinstance(items, list):
                for item in items:
                    if "pages" in item and len(item["pages"]) > 0:
                        for page in item["pages"]:
                            event = {
                                "title": page.get("title", ""),
                                "displayTitle": page.get("displaytitle", "").replace("<span class=\"mw-page-title-main\">", "").replace("</span>", ""),
                                "year": item.get("year", ""),
                                "date": f"{formatted_month}/{formatted_day}",
                                "text": item.get("text", ""),
                                "extract": page.get("extract", ""),
                                "category": category,
                                "url": page.get("content_urls", {}).get("desktop", {}).get("page", ""),
                                "description": page.get("description", ""),
                                "image": None  # Default to None
                            }
                            
                            # Add thumbnail image if available
                            if "thumbnail" in page:
                                event["image"] = {
                                    "source": page["thumbnail"].get("source", ""),
                                    "width": page["thumbnail"].get("width", ""),
                                    "height": page["thumbnail"].get("height", "")
                                }
                            # If no thumbnail but original image exists
                            elif "originalimage" in page:
                                event["image"] = {
                                    "source": page["originalimage"].get("source", ""),
                                    "width": page["originalimage"].get("width", ""),
                                    "height": page["originalimage"].get("height", "")
                                }
                            
                            # Only add events that have images
                            if event["image"] is not None:
                                data.append(event)
                                
                                # Stop once we have 5 items
                                if len(data) >= 5:
                                    return data
        
        return data  # Ensure we return at most 5 items
    else:
        print(f"Error fetching data: {response.status_code}")
        return []