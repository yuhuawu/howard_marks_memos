from lxml import html
import requests
import logging
import time, random

def _get_detail_page(url):
    """
    Get the detail page content.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error for bad responses
    return response.content

def parse_detail_page(url: str) -> str | None:
    """
    get detail page content
    then parse the content
    return pdf link
    """
    time.sleep(random.randint(5, 10))
    content = _get_detail_page(url)
    tree = html.fromstring(content)
    
    link_element = tree.xpath("//a[normalize-space()='PDF (English)']")
    if link_element:
        pdf_link = link_element[0].get('href')
    else:
        pdf_link = None

    logging.debug(f"get {pdf_link} from {url}")
    
    return pdf_link