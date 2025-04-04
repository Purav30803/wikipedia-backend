import requests
from sqlalchemy.orm import Session
from loguru import logger
from typing import Optional
from models.search import SearchHistory
from datetime import timedelta
from datetime import datetime as dt
from config.env import Env
from utils.wikipedia_helper import get_region_from_ip, get_wikipedia_features, extract_article_title, get_past_week_views, predict_future_views
import joblib
import numpy as np
import random
import pytz


# Global model variable
loaded_sklearn_model = None

def load_sklearn_model_once():
    global loaded_sklearn_model
    try:
        # Load your scikit-learn model (adjust path as needed)
        loaded_sklearn_model = joblib.load("service/logistic_regression_model.pkl")
        print("✅ scikit-learn model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load scikit-learn model: {e}")
        loaded_sklearn_model = None

# Load the scikit-learn model at startup
load_sklearn_model_once()

def preprocess_input(data: dict):
    # Ensure all necessary keys are present
    required_keys = ["title_length", "article_length", "num_categories", "num_links", "zero_pageviews_days", "recent_edit_days", "pageview_trend"]
    if not all(key in data for key in required_keys):
        raise ValueError(f"Missing one of the required keys: {required_keys}")
    
    features = [
        data["title_length"],
        data["article_length"],
        data["num_categories"],
        data["num_links"],
        data["zero_pageviews_days"],
        data["recent_edit_days"],
        data["pageview_trend"],
    ]
    
    print(f"Preprocessed input: {features}")
    return np.array([features])

def search_in_model_service(search: str, db: Session, ip_address: str, user_agent: Optional[str]):
    global loaded_sklearn_model
    logger.info(f"Received search query: '{search}' from IP: {ip_address} using User-Agent: {user_agent}")
    
    if not search:
        return {"error": "Search query cannot be empty"}
    
    if not search.startswith("https://en.wikipedia.org/wiki/") and not search.startswith("https://en.m.wikipedia.org/wiki/")  and not search.startswith("en.wikipedia.org/wiki/") and not search.startswith("en.m.wikipedia.org/wiki/"):
        return {"error": "Search query must be a valid Wikipedia URL"}
    
    # Check if the model is loaded
    if not loaded_sklearn_model:
        return {"error": "Model is not loaded. Please check the model path and ensure it is properly trained."}

    try:
        # Fetch Wikipedia data (you need to implement get_wikipedia_features)
        data = get_wikipedia_features(search)
        if data["article_length"] == 0:
            return {"error": "No data found for the given URL. Please try another Wikipedia article."}
        input_data = preprocess_input(data)
        
        # Predict using the scikit-learn model
        prediction = loaded_sklearn_model.predict(input_data)[0]
        
        # Interpret prediction (Adjust threshold if necessary)
        search_result = "positive" if prediction == 1 else "negative"
        print(f"Prediction: {prediction} => {search_result}")
        
        # Optional: Get region from IP address if needed
        ip = Env.ALLOW_IP or "No"
        region_data = get_region_from_ip(ip_address) if ip == "Yes" else "DUMMY REGION"
        
        # Log search history in DB
        search_history = SearchHistory(
            ip_address=ip_address,
            search_query=search,
            result=search_result,
            user_agent=user_agent,
            region=region_data,
            wikipedia_data=data
        )
        
        db.add(search_history)
        db.commit()
        db.refresh(search_history)
        
        logger.info(f"Search result stored for query '{search}' from IP: {ip_address}")
        
        return {
            "search_results": search_result,
            "ip_address": ip_address,
            "region": region_data,
            "user_agent": user_agent,
            "data": data
        }
    except Exception as e:
        logger.error(f"Error occurred while processing search '{search}': {e}")
        db.rollback()
        return {"error": f"Failed to perform search: {e}"}

  

def get_on_this_day_data(timezone="UTC"):
    try:
        # Get the current date based on the user's timezone
        tz = pytz.timezone(timezone)
        date = dt.now(tz)
        
        # Extract the month and day
        formatted_month = f"{date.month:02d}"
        formatted_day = f"{date.day:02d}"
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    
        # Construct the API URL
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/all/{formatted_month}/{formatted_day}"
        print(url)
        
        # Fetch data from the API with a timeout
        response = requests.get(url, timeout=10, headers=headers)
        
        if response.status_code == 200:
            raw_data = response.json()
            
            # Shuffle categories for randomness
            shuffled_categories = list(raw_data.items())
            random.shuffle(shuffled_categories)
            
            data = []
            seen_years = set()  # Track distinct years

            # Process each section of the API response
            for category, items in shuffled_categories:
                if isinstance(items, list):
                    random.shuffle(items)  # Shuffle items in each category

                    for item in items:
                        year = item.get("year", "")
                        if not year or year in seen_years:
                            continue  # Skip duplicate years

                        if "pages" in item and len(item["pages"]) > 0:
                            random.shuffle(item["pages"])  # Shuffle pages within each item

                            for page in item["pages"]:
                                event = {
                                    "title": page.get("title", ""),
                                    "displayTitle": page.get("displaytitle", "").replace("<span class=\"mw-page-title-main\">", "").replace("</span>", ""),
                                    "year": year,
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
                                    seen_years.add(year)  # Mark this year as used

                                    # Stop once we have 5 unique years
                                    if len(data) >= 5:
                                        return data

            return data  # Ensure we return at most 5 unique year items
        else:
            print(f"Error fetching data: {response.status_code}")
            return []
    
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return []


def get_yesterdays_date():
    # Get yesterday's date
    yesterday = dt.now() - timedelta(days=1)
    return yesterday.strftime('%Y/%m/%d')

def get_top_trending_articles():
    # Get yesterday's date dynamically
    yesterday_date = get_yesterdays_date()
    
    print(f"Yesterday's date: {yesterday_date}")
    
    # Construct the URL for the API request
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{yesterday_date}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        # Extract exactly 4 valid articles, skipping "Special:Search"
        top_articles = []
        articles = data.get("items", [])[0].get("articles", [])
        total_count = 0
        for article_data in articles[2:]:  # Start from index 2 as before
            if isinstance(article_data, dict):
                title = article_data.get("article", "Unknown Title").replace("_", " ")
                
                if title == "Special:Search" or title == "Wikipedia:Featured pictures":
                    continue
                
                total_count += 1
                top_articles.append({
                    "title": title,
                    "pageviews": article_data.get("views", 0),
                    "rank": total_count or "Unknown Rank",
                    "article_url": f"https://en.wikipedia.org/wiki/{article_data.get('article', 'Unknown')}"
                })

            if len(top_articles) == 4:
                break

        return top_articles
    else:
        return f"Error: {response.status_code}"



def article_engagement(wiki_url):
    article_title = extract_article_title(wiki_url)
    past_data = get_past_week_views(article_title)
    if len(past_data) == 0:
        return {
            "error": f"No pageviews data found for article {article_title}"
        }
    future_data = predict_future_views(past_data)
    
    return {
        "article": article_title,
        "past": past_data,
        "future": future_data
    }