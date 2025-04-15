

Host = "https://www.oaktreecapital.com"
ListPageUrl = "https://www.oaktreecapital.com/insights/memos"

"""
after analyzing the page, it could be solved by requests + lxml. 
"""

import requests
from lxml import html

from typing import List

def get_list_page(url):
    """
    Get the list page of Oaktree Capital Management's memos.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error for bad responses
    page_content = response.content
    return page_content


def parse_list_page(page_content: str, begin_year=2020, end_year=2020) -> List[dict]:
    """
    Parse the list page content and extract memo links and titles.
    """
        
    tree = html.fromstring(page_content)

    # Select memo links for years between {begin_year} and {end_year}.
    # The XPath looks for div elements with class "tab" where the button text (as a number) is in the desired range,
    years_xpath = f'//div[@class="tab"][number(button/text()) >= {begin_year} and number(button/text()) <= {end_year}]'
    years = tree.xpath(years_xpath)
    
    memos = []
    
    for year in years:
        memo_rows_xpath = './/div[@class="row"]/div[contains(@class, "my-4")]'
        memo_rows = year.xpath(memo_rows_xpath)
        for row in memo_rows:
            # Extract the title and link for each memo
            links = row.xpath('.//a[@class="oc-title-link"]')
            if links:
                # Extract the href attribute of the anchor tag with class "oc-title-link".
                #href = links[0].xpath('@href')[0]
                href = links[0].get('href')
                #title = links[0].xpath('text()')[0]
                title = links[0].text_content().strip()
                #print(f"Title: {title}, Link: {href}")
            else:
                continue
            datetime = row.xpath(".//time[@class='embedded-date d-block']/@datetime")[0] \
                if row.xpath(".//time[@class='embedded-date d-block']/@datetime") else None
            #print(f"Date: {datetime}, Title: {title}, Link: {href}")
            
            memos.append({
                "title": title,
                "link": href,
                "date": datetime
            })
            #test only, remove it later.
            #if len(memos) >= 2:
            #    break
        logging.debug(f"Found {len(memos)} memos in year {year.xpath('button/text()')[0]}")
    logging.debug(f"Found {len(memos)} memos in total.")
    return memos


from detail_page_handler import parse_detail_page
import re
import os
from datetime import datetime
import random, time

pdf_extract_pattern = r"javascript:openPDF\('[^']+','(?P<pdf_url>[^']+)'\)"
pdf_extract_pattern_obj = re.compile(pdf_extract_pattern)


def on_each_memo(memos: List[dict]):
    """
    """
    
    for memo in memos:
        # Get the detail page content
        link = memo['link']
        pdf_link = None
        
        if link.startswith("/"):
            # likes: /insights/memo/coming-into-focus
            detail_link = f"https://www.oaktreecapital.com{link}"        
            # Parse the detail page content
            # get link like: javascript:openPDF('Nobody Knows (Yet Again)','https://www.oaktreecapital.com/docs/default-source/memos/nobody-knows-yet-again.pdf?sfvrsn=af392b66_6')
            link = parse_detail_page(detail_link)
            
        # likes: javascript:openPDF('Time for Thinking','https://www.oaktreecapital.com/docs/default-source/memos/timeforthinking.pdf?sfvrsn=17818c65_8')
        # earse openPDF...
        match = pdf_extract_pattern_obj.search(link)
        if not match:
            raise ValueError(f"Invalid link format: {link}")
        pdf_link = match.group("pdf_url")
        
        memo['link'] = pdf_link
        
        # >2020-03-19T07:00:00.0000000Z
        _date = memo['date']
        _date = _date.split("T")[0]
        try:
            memo['date'] = datetime.strptime(_date, ">%Y-%m-%d").date()
        except ValueError as e:
            logging.error(f"Invalid date format: {_date} with parsing error: {e}")
            continue
        
        # now try to download the pdf
        if pdf_link is not None:
            # Download the memo
            time.sleep(random.randint(5, 10))
            local_file_path = download_memo(pdf_link)
            # Update the memo dictionary with the local file path
            memo['local_file_path'] = local_file_path
            
        print(memo)       
    
    return memos
    

def download_memo(pdf_link: str) -> str:
    """
    download pdf to local directory
    """
    local_file_path = pdf_link.split("/")[-1]
    if not local_file_path.endswith(".pdf"):
        local_file_path = local_file_path.split("?")[0]
    
    if os.path.exists(local_file_path):
        logging.debug(f"{local_file_path} already exists, skip download.")
        return local_file_path
    
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    
    response = requests.get(pdf_link, headers=headers)
    response.raise_for_status()  # Raise an error for bad responses
    
    # Save the PDF to a local file
    with open(local_file_path, 'wb') as f:
        f.write(response.content)
    
    return local_file_path
    
from PyPDF2 import PdfWriter, PdfReader

def merge_memos(memos: List[dict]):
    """
    merge memos to a single pdf file
    """
    sorted_memos = sorted(memos, key=lambda x: x['date'])
    
    writer = PdfWriter()
    current_pos = 0
    for memo in sorted_memos:
        local_file_path = memo.get('local_file_path')
        date_str = memo.get('date').strftime("%Y-%m-%d")
        toc_title = f"{date_str} {memo['title']}"
        if not local_file_path or os.path.exists(local_file_path) == False:
            logging.warning(f"File {local_file_path} does not exist, skip.")
            continue
        with open(local_file_path, "rb") as f:
            reader =  PdfReader(f)
            start_pos = current_pos
            for page in reader.pages:
                writer.add_page(page)
                current_pos += 1
            writer.add_outline_item(toc_title, start_pos)
    
     # create a new pdf file
    merged_pdf_path = "merged_memos.pdf"
    if os.path.exists(merged_pdf_path):
        os.remove(merged_pdf_path)
    # create a new pdf file
    with open(merged_pdf_path, "wb") as f_out:
        writer.write(f_out)
        # close the writer
    writer.close()
                    
    
    # use PyPDF2 or similar library to merge pdf files
    # ...
    
    logging.debug(f"Merged memos saved to {merged_pdf_path}")
    
    return merged_pdf_path


def main():
    # Get the list page content
    page_content = get_list_page(ListPageUrl)
    
    # Parse the list page content
    memos = parse_list_page(page_content, begin_year=2008, end_year=2025)
    #for memo in memos:
    #    print(f"Title: {memo['title']}, Link: {memo['link']}, Date: {memo['date']}")        
        
    on_each_memo(memos)
    merge_memos(memos)
    
        
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()