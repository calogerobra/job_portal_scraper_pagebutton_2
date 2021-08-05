# Import general libraries
import datetime
import pandas as pd
from bs4 import BeautifulSoup as soup
import time

# SQl packages
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy

import requests
requests.packages.urllib3.disable_warnings()
import random

# Improt Selenium packages
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException as NoSuchElementException
from selenium.common.exceptions import WebDriverException as WebDriverException
from selenium.common.exceptions import ElementNotVisibleException as ElementNotVisibleException
from selenium.common.exceptions import ElementNotInteractableException as ElementNotInteractableException
from selenium.webdriver.chrome.options import Options


def adjust_listings_pages(page, pagelist):
    """ Adjusts listings to restart properly after crash
    Args:
        Current page
        Amount of pages
        Parameter if query is set on repeat
    Returns:
        Jumps to page where last stopped
    """
    return pagelist[pagelist.index(page):len(pagelist)]


def request_page(url_string, verification, robust):
    """HTTP GET Request to URL.
    Args:
        url_string (str): The URL to request.
        verification: Boolean certificate is to be verified
        robust: If to be run in robust mode to recover blocking
    Returns:
        HTML code
    """
    if robust:
        loop = False
        first = True
        # Scrape contents in recovery mode
        c = 0
        while loop or first:
            first = False
            try:
                uclient = requests.get(url_string, timeout = 60, verify = verification)
                page_html = uclient.text
                loop = False
                return page_html
            except requests.exceptions.ConnectionError:
                c += 10
                print("Request blocked, .. waiting and continuing...")
                time.sleep(random.randint(10,60) + c)
                loop = True
                continue
            except (requests.exceptions.ReadTimeout,requests.exceptions.ConnectTimeout):
                print("Request timed out, .. waiting one minute and continuing...")
                time.sleep(60)
                loop = True
                continue
    else:
        uclient = requests.get(url_string, timeout = 60, verify = verification)
        page_html = uclient.text
        loop = False
        return page_html

def request_page_fromselenium(url_string, driver, robust):
    """ Request HTML source code from Selenium web driver to circumvent mechanisms
    active with HTTP requests
    Args:
        Selenium web driver
        URL string
    Returns:
        HTML code
    """
    if robust:
        loop = False
        first = True
        # Scrape contents in recovery mode
        c = 0
        while loop or first:
            first = False
            try:
                open_webpage(driver, url_string)
                time.sleep(5)
                page_html = driver.page_source
                loop = False
                return page_html
            except WebDriverException:
                c += 10
                print("Web Driver problem, .. waiting and continuing...")
                time.sleep(random.randint(10,60) + c)
                loop = True
                continue
    else:
        open_webpage(driver, url_string)
        time.sleep(5)
        page_html = driver.page_source
        loop = False
        return page_html

def set_driver(webdriverpath, headless):
    """Opens a webpage in Chrome.
    Args:
        url of webpage.
    Returns:
        open and maximized window of Chrome with webpage.
    """
    options = Options()
    if headless:

        options.add_argument("--headless")
    elif not headless:
        options.add_argument("--none")
    return webdriver.Chrome(webdriverpath, chrome_options = options)

def create_object_soup(object_link, verification, robust):
    """ Create page soup out of an object link for a product
    Args:
        Object link
        certificate verification parameter
        robustness parameter
    Returns:
        tuple of beautiful soup object and object_link
    """
    object_soup = soup(request_page(object_link, verification, robust), 'html.parser')
    return (object_soup, object_link)

def make_listings_soup(object_link, verification):
    """ Create soup of listing-specific webpage
    Args:
        object_id
    Returns:
        soup element containing listings-specific information
    """
    listing_url = object_link
    return soup(request_page(listing_url, verification), 'html.parser')

def reveal_all_items(driver):
    """ Reveal all items on the categroy web page of Albert Heijn by clicking "continue"
    Args:
        Selenium web driver
    Returns:
        Boolean if all items have been revealed
    """
    hidden = True
    try:
        driver.find_element_by_css_selector('section#jobify_widget_jobs-1 a > strong').click() # Accept cookies!
    except NoSuchElementException:
        pass
    while hidden:
        try:
           time.sleep(random.randint(5,7))
           driver.find_element_by_css_selector('section#jobify_widget_jobs-1 a > strong').click()
        except (NoSuchElementException, ElementNotVisibleException, ElementNotInteractableException):
           hidden = False
    return True

def open_webpage(driver, url):
    """Opens web page
    Args:
        web driver from previous fct and URL
    Returns:
        opened and maximized webpage
    """
    driver.set_page_load_timeout(60)
    driver.get(url)
    driver.maximize_window()

def make_jobs_list(base_url, robust, driver):
    """ Extract item URL links and return list of all item links on web page
    Args:
        Base URL
        Categroy tuples
        Certificate verification parameter
        Robustness parameter
        Selenium web driver
    Returns:
        Dictionary with item URLs
    """
    print("Start retrieving item links...")
    on_repeat = False
    first_run = True
    item_links = []
    while on_repeat or first_run:
        first_run = False
        open_webpage(driver, base_url)
        if reveal_all_items(driver):
            page_html = driver.page_source
            page_soup = soup(page_html, 'html.parser')
            link_containers = page_soup.findAll('div', {'class': 'job_listings'})[0].findAll('a', {'class': 'job_listing-clickbox'})
            item_links = item_links + [item['href'] for item in link_containers]
            # Check if links where extracted
            try:
                assert len(item_links) != 0
                print('Retrieved', len(item_links), 'item links!')
                on_repeat = False
            except AssertionError:
                print("No links extracted", "Repeating process...")
                on_repeat = True
                break
    return item_links


def create_elements(object_link, verification, robust):
    """Extracts the relevant information form the html container, i.e. object_id,
    Args:
        A container element + region, city, districts, url_string.
    Returns:
        A dictionary containing the information for one listing.
    """
    object_soup = create_object_soup(object_link, verification, robust)[0]
    # Parse contents
    try:
        company_name = object_soup.findAll('li', {'class': 'job-company'})[0].a.text
    except:
        company_name = ""
    try:
        job_city = object_soup.findAll('li', {'class': 'location'})[0].a.text
    except:
        job_city = ""
    try:
        job_title = object_soup.findAll('h1', {'class': 'page-title'})[0].text.strip('\n').strip('\t')
    except:
        job_title = ""
    try:
        posting_date = object_soup.findAll('li', {'class': 'date-posted'})[0].text
    except:
        posting_date = ""
    try:
        expiration_date = object_soup.findAll('li', {'class': 'application-deadline'})[0].text
    except:
        expiration_date = ""
    try:
        job_description = object_soup.findAll('div', {'class': 'job-overview-content row'})[0].text
    except:
        job_description = ""
    try:
        job_category = object_soup.findAll('div', {'class': 'job_listing-categories'})[0].text
    except:
        job_category = ""
    object_link = object_link
    # Create a dictionary as output
    return dict([("object_link", object_link),
                 ("job_title", job_title),
                 ("company_name", company_name),
                 ("job_city", job_city),
                 ("posting_date", posting_date),
                 ("expiration_date", expiration_date),
                 ("job_description", job_description),
                 ("job_category", job_category)])


def scrape_ofertapune_kosovajob(verification, robust, item_links):
    """Scraper for Ofertapune (Verison from Kosovajob) job portal based on specified parameters.
    In the following we would like to extract all the containers containing
    the information on one listing. For this purpose we try to parse through
    the html text and search for all elements of interest.
    Args:
        verification
        robust
        item_links
    Returns:
        Appended pandas dataframe with crawled content.
    """
    # Define dictionary for output
    input_dict = {}
    frames = []
    counter = 0
    #skipper = 0
    # Loop links
    for item_link in item_links:
        time.sleep(random.randint(1,3))
        print('Parsing URL', item_link)
        # Set scraping time
        now = datetime.datetime.now()
        try:
            input_dict.update(create_elements(item_link, verification, robust))
            time.sleep(0.5)
            # Create a dataframe
            df = pd.DataFrame(data = input_dict, index =[now])
            df.index.names = ['scraping_time']
            frames.append(df)
        except sqlalchemy.exc.DatabaseError or requests.exceptions.SSLError:
            break
        except requests.exceptions.ConnectionError:
            error_message = "Connection was interrupted, waiting a few moments before continuing..."
            print(error_message)
            time.sleep(random.randint(2,5) + counter)
            continue
    return pd.concat(frames).drop_duplicates(subset = 'object_link')

def main():
    """ Note: Set parameters in this function
    """
    # Set time stamp
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Set scraping parameters
    base_url = 'http://www.ofertapune.net'
    robust = True
    webdriverpath = r"C:\Users\Calogero\Documents\GitHub\job_portal_scraper_pagebutton_2\chromedriver.exe"

    # Set up a web driver
    driver = set_driver(webdriverpath, False)

    # Start timer
    start_time = time.time() # Capture start and end time for performance

    # Set verification setting for certifiates of webpage. Check later also certification
    verification = True

    # Execute functions for scraping
    start_time = time.time() # Capture start and end time for performance
    item_links = make_jobs_list(base_url, robust, driver)
    appended_data = scrape_ofertapune_kosovajob(verification, robust, item_links)

    # Write output to Excel
    print("Writing to Excel file...")
    time.sleep(1)
    file_name = '_'.join(['C:\\Users\\Calogero\\Documents\\GitHub\\job_portal_scraper_pagebutton_2\\data\\daily_scraping\\' +
    str(now_str), 'ofertapune_kosovajob.xlsx'])
    writer = pd.ExcelWriter(file_name, engine='xlsxwriter')
    appended_data.to_excel(writer, sheet_name = 'jobs')
    writer.save()
    workbook = writer.book
    worksheet = writer.sheets['jobs']
    format1 = workbook.add_format({'bold': False, "border" : True})
    worksheet.set_column('A:M', 15  , format1)
    writer.save()

    # Check end time
    end_time = time.time()
    duration = time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))

    # For interaction and error handling
    driver.close()
    final_text = "Your query was successful! Time elapsed:" + str(duration)
    print(final_text)
    time.sleep(0.5)

# Execute scraping
if __name__ == "__main__":
    main()





