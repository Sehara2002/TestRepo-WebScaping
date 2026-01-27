import os
import time
import requests
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_debug.log", mode='w'),
        logging.StreamHandler()
    ]
)

def setup_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless=new') # Disabled for user showcase
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver_path = r"C:/Users/sheha/.wdm/drivers/chromedriver/win64/144.0.7559.96/chromedriver-win32/chromedriver.exe"
    service = Service(executable_path=driver_path)
    return webdriver.Chrome(service=service, options=options)

def safe_click(driver, element, name="Element"):
    """Tries multiple ways to click an element."""
    try:
        element.click()
        logging.info(f"Clicked {name} (Standard)")
        return True
    except Exception as e1:
        try:
            driver.execute_script("arguments[0].click();", element)
            logging.info(f"Clicked {name} (JS)")
            return True
        except Exception as e2:
            try:
                actions = ActionChains(driver)
                actions.move_to_element(element).click().perform()
                logging.info(f"Clicked {name} (ActionChains)")
                return True
            except Exception as e3:
                logging.error(f"Failed to click {name}: {e3}")
                return False

def download_file(url, folder, filename, driver_cookies):
    if not os.path.exists(folder): os.makedirs(folder)
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath): 
        logging.info(f"Skipping {filename}, exists.")
        return
    try:
        s = requests.Session()
        for c in driver_cookies: s.cookies.set(c['name'], c['value'])
        r = s.get(url, stream=True)
        content_type = r.headers.get('Content-Type', '').lower()
        
        if 'application/pdf' in content_type:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(8192): f.write(chunk)
            logging.info(f"Downloaded: {filename}")
        else:
            logging.warning(f"File {filename} is not PDF (Type: {content_type})")

    except Exception as e:
        logging.error(f"DL Error {filename}: {e}")

def run():
    logging.info("Starting Scraper Run...")
    driver = setup_driver()
    try:
        driver.get("https://qualifications.pearson.com/en/support/support-topics/exams/past-papers.html")
        time.sleep(5)

        # Cookie
        try:
            btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            btn.click()
            logging.info("Cookies accepted")
            time.sleep(2)
        except: 
            logging.info("Cookie banner not found or skipped")

        # Navigate to the correct section
        logging.info("Looking for findpastpapers section...")
        time.sleep(2)
        
        # Find the findpastpapers section
        try:
            findpastpapers = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "findpastpapers"))
            )
            logging.info("Found findpastpapers section")
            
            # Scroll to it
            driver.execute_script("arguments[0].scrollIntoView(true);", findpastpapers)
            time.sleep(1)
            driver.save_screenshot("findpastpapers_section.png")
            
            # Find the inner container - try multiple approaches
            inner_container = None
            try:
                # Try specific class pattern first
                inner_container = findpastpapers.find_element(By.XPATH, ".//*[contains(@class, 'findpastpapers_')]")
                logging.info(f"Found inner container: {inner_container.get_attribute('class')}")
            except:
                # Fallback: just use findpastpapers itself
                logging.info("Using findpastpapers section directly")
                inner_container = findpastpapers
            
            # Look for the step sections directly
            # Step 1: Select a qualification
            logging.info("Step 1: Selecting Qualification Family (A Level)")
            time.sleep(1)
            
            # Find A Level - it should be in a list or dropdown
            alevel_option = inner_container.find_element(By.XPATH, ".//*[contains(text(), 'A Level') and not(ancestor::select)]")
            safe_click(driver, alevel_option, "A Level")
            time.sleep(2)
            driver.save_screenshot("after_alevel.png")
            
            # Step 2: Subjects
            logging.info("Step 2: Selecting Subject (Mathematics)")
            time.sleep(1)
            
            # Find Mathematics
            math_option = inner_container.find_element(By.XPATH, ".//*[contains(text(), 'Mathematics') and not(contains(text(), 'Further'))]")
            safe_click(driver, math_option, "Mathematics")
            time.sleep(2)
            driver.save_screenshot("after_math.png")
            
            # Step 3: Exam Series
            logging.info("Step 3: Selecting Exam Series")
            time.sleep(1)
            
            # Find June series
            series_options = inner_container.find_elements(By.XPATH, ".//*[contains(text(), 'June')]")
            series_target = None
            for opt in series_options:
                if opt.is_displayed() and any(year in opt.text for year in ['2024', '2023', '2022']):
                    series_target = opt
                    break
            
            if series_target:
                series_name = series_target.text.strip()
                safe_click(driver, series_target, f"Series: {series_name}")
                time.sleep(3)
                driver.save_screenshot("after_series.png")
            else:
                logging.warning("No recent June series found")
            
            # Step 4: Content Type (if needed)
            logging.info("Step 4: Checking for content type filter")
            try:
                qp_option = inner_container.find_element(By.XPATH, ".//*[contains(text(), 'Question paper')]")
                safe_click(driver, qp_option, "Question Papers")
                time.sleep(2)
            except:
                logging.info("No content type filter found or needed")
            
            # Wait for results to load
            logging.info("Waiting for results to load...")
            time.sleep(5)
            driver.save_screenshot("results_page.png")
            
            # Look for PDF links
            pdf_links = driver.find_elements(By.XPATH, 
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'question paper')] | //a[contains(@href, '.pdf')]")
            
            visible_links = [link for link in pdf_links if link.is_displayed()]
            logging.info(f"Found {len(visible_links)} PDF links")
            
            if visible_links:
                cookies = driver.get_cookies()
                folder = "papers/mathematics"
                
                for i, link in enumerate(visible_links[:10]):  # Download up to 10
                    url = link.get_attribute("href")
                    text = link.text.strip()
                    filename = f"{text[:50] if text else f'paper_{i}'}.pdf"
                    filename = "".join([c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')]).strip()
                    
                    logging.info(f"Downloading: {filename}")
                    download_file(url, folder, filename, cookies)
                    
                logging.info(f"Successfully downloaded {min(len(visible_links), 10)} papers")
            else:
                logging.warning("No PDF links found!")
                with open("no_results.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                    
        except Exception as e:
            logging.error(f"Error navigating sections: {e}")
            driver.save_screenshot("section_error.png")

    except Exception as e:
        logging.error(f"Global Error: {e}")
        driver.save_screenshot("error_screenshot.png")
    finally:
        driver.quit()
        logging.info("Driver Closed")



if __name__ == "__main__":
    run()
