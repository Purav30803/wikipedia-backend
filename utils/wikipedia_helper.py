from typing import Optional
import requests
from loguru import logger
import datetime
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import numpy as np
from urllib.parse import urlparse, unquote



def get_region_from_ip(ip_address: str) -> Optional[str]:
    try:
        # Use ipstack API to get location data
        access_key = '07eab0c8a7e57efaaaa21261e17817c6'  # Replace with your ipstack API key
        url = f"http://api.ipstack.com/{ip_address}?access_key={access_key}"
        response = requests.get(url)
        response.raise_for_status()  # Ensure we get a valid response

        data = response.json()

        # Extract region
        return data
    
    except requests.exceptions.RequestException as e:
        # Log error if the API request fails
        logger.error(f"Failed to retrieve region for IP {ip_address}: {e}")
        return None
    

def get_wikipedia_features(article_url):
    # Extract article title from URL
    title = article_url.split("/wiki/")[-1].replace("_", " ")

    # Wikipedia API Base URL
    api_url = "https://en.wikipedia.org/w/api.php"

    # Get article metadata
    params = {
        "action": "query",
        "titles": title,
        "prop": "info|categories|links",
        "format": "json"
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    # Extract page ID (Wikipedia API returns data in a nested structure)
    page_id = list(data["query"]["pages"].keys())[0]
    page_info = data["query"]["pages"][page_id]

    # Get features
    title_length = len(title)
    article_length = page_info.get("length", 0)  # Article content length
    num_categories = len(page_info.get("categories", []))
    num_links = len(page_info.get("links", []))

    # Get last edited timestamp
    last_edit = page_info.get("touched", "2025-01-01T00:00:00Z")
    last_edit_date = datetime.datetime.strptime(last_edit, "%Y-%m-%dT%H:%M:%SZ")
    recent_edit_days = (datetime.datetime.utcnow() - last_edit_date).days

    # Get Page Views (last 20 days)
    today = datetime.datetime.today().strftime('%Y%m%d')
    start_date = (datetime.datetime.today() - datetime.timedelta(days=10)).strftime('%Y%m%d')

    pageviews_url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{title}/daily/{start_date}/{today}"
    pageviews_response = requests.get(pageviews_url,headers={"User-Agent": "Mozilla/5.0"})
    if pageviews_response.status_code == 200:
        pageviews_data = pageviews_response.json()
        if "items" not in pageviews_data:
            logger.error(f"No pageviews data for article {title}")
            pageviews = [0] * 1
        else:
            pageviews = [entry["views"] for entry in pageviews_data["items"]]
    else:
        logger.error(f"Error fetching pageviews for {title}: {pageviews_response.status_code}")
        pageviews = [0] * 1

    zero_pageviews_days = pageviews.count(0)

    # Calculate pageview trend
# Calculate pageview trend
    if sum(pageviews[:10]) > 0:
        recent_trend = sum(pageviews[-10:]) / sum(pageviews[:10])
    else:
        recent_trend = 0  # Avoid division by zero, or handle based on your preference


    return {
        "title": title,
        "title_length": title_length,
        "article_length": article_length,
        "num_categories": num_categories,
        "num_links": num_links,
        "zero_pageviews_days": zero_pageviews_days,
        "recent_edit_days": recent_edit_days,
        "pageview_trend": recent_trend,
        "pageviews": pageviews
    }


def extract_article_title(wiki_url: str):
    """Extract the article title from a Wikipedia link."""
    path = urlparse(wiki_url).path
    title = path.split("/")[-1]  # Get the last part of the URL
    return unquote(title.replace("_", " "))  # Convert URL encoding to normal text

def get_past_week_views(article_title: str):
    """Fetch past 7 days of views for a given Wikipedia article."""
    base_url = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{}/daily/{}/{}"
    historical_data = []
    
    for i in range(7):
        date = (datetime.now() - timedelta(days=i+1)).strftime('%Y%m%d')
        url = base_url.format(article_title, date, date)
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        
        if response.status_code == 200:
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                views = data["items"][0]["views"]
                # put - beween date
                date = date[:4] + "-" + date[4:6] + "-" + date[6:]
                historical_data.append({"date": date, "views": views})
    
    return historical_data

def predict_future_views(past_data):
    """Predict engagement for the next 7 days using Linear Regression."""
    df = pd.DataFrame(past_data)
    df['date'] = pd.to_datetime(df['date'])
    df['days_ago'] = (df['date'].max() - df['date']).dt.days  # Convert date to numeric

    if len(df) < 2:
        return []  # Not enough data for prediction

    X = df[['days_ago']].values
    y = np.log1p(df['views'].values)  # Apply log transformation to stabilize

    model = LinearRegression().fit(X, y)

    future_days = np.array([df['days_ago'].max() + i for i in range(1, 3)]).reshape(-1, 1)
    predicted_views = model.predict(future_days)

    future_data = []
    for i, views in enumerate(predicted_views):
        future_data.append({
            "date": (df['date'].max() + timedelta(days=i+1)).strftime('%Y-%m-%d'),
            "views": max(int(np.expm1(views)), 0)  # Convert back and prevent negatives
        })
    
    return future_data