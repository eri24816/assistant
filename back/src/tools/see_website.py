from back.src.util import MyBeautifulSoup
import requests


def see_website(url: str) -> str:
    """See a website.
    
    Args:
        url: The URL of the website
    
    Returns:
        The content of the website as a string
    """
    soup = MyBeautifulSoup(requests.get(url).text, 'html.parser')
    
    return soup.get_text()

print(see_website("https://www.google.com"))