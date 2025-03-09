from typing import Optional
import requests
from loguru import logger
import datetime
from config.env import Env


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
