
import json
from typing import List, Dict
import os
import requests
from dotenv import load_dotenv

load_dotenv()


def search_web(query: str) -> List[Dict[str, str]]:
    """Search the web for information.
    
    Args:
        query: The search query string
    
    Returns:
        Search results as a string

    example:
    curl -s --compressed "https://api.search.brave.com/res/v1/web/search?q=brave+search" \
      -H "Accept: application/json" \
      -H "Accept-Encoding: gzip" \
      -H "X-Subscription-Token: <YOUR_API_KEY>"
    """
    url = f"https://customsearch.googleapis.com/customsearch/v1?q={query}&key={os.getenv('GOOGLE_SEARCH_API_KEY')}&cx={os.getenv('GOOGLE_SEARCH_CX')}&num=10"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
    }
    response = requests.get(url, headers=headers)
    
    fields_to_retain = ['title', 'link', 'displayLink','snippet']
    items = []
    for item in json.loads(response.text)['items']:
        items.append({field: item.get(field, '') for field in fields_to_retain})
    return items
    # return json.loads(response.text)  