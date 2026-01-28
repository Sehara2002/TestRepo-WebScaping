import os
import time
import re
import requests
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_ms_debug.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Use cached driver path to bypass network issues as seen in previous runs
    driver_path = r"C:\Users\sheha\.wdm\drivers\chromedriver\win64\144.0.7559.96\chromedriver-win32\chromedriver.exe"
    if not os.path.exists(driver_path):
        service = Service(ChromeDriverManager().install())
    else:
        service = Service(driver_path)
    return webdriver.Chrome(service=service, options=options)

def safe_click(driver, element, name="Element"):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(element))
        element.click()
        logging.info(f"Clicked {name}")
        return True
    except:
        try:
            driver.execute_script("arguments[0].click();", element)
            logging.info(f"Clicked {name} (JS)")
            return True
        except Exception as e:
            logging.error(f"Failed to click {name}: {e}")
            return False

def download_paired_papers():
    logging.info("Starting Selenium Scraper (Paired QP + MS)...")
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)
    
    try:
        driver.get("https://qualifications.pearson.com/en/support/support-topics/exams/past-papers.html")
        logging.info("Page loaded")
        
        # Cookie banner
        try:
            cookie_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            cookie_btn.click()
            time.sleep(1)
        except: pass

        # Step 1: Select A Level
        logging.info("Step 1: Selecting A Level...")
        alevel_xpath = "//div[contains(@class, 'findpastpapers')]//*[contains(text(), 'A Level') and not(ancestor::select)]"
        alevel = wait.until(EC.visibility_of_element_located((By.XPATH, alevel_xpath)))
        safe_click(driver, alevel, "A Level")
        time.sleep(3)
        
        # Step 2: Select Mathematics
        logging.info("Step 2: Selecting Mathematics...")
        # Switch to Current qualifications
        try:
            current_tab = driver.find_element(By.XPATH, "//div[contains(@class, 'findpastpapers')]//a[contains(text(), 'Current qualifications')]")
            if current_tab.is_displayed():
                safe_click(driver, current_tab, "Current qualifications tab")
                time.sleep(2)
        except: pass
        
        # Click 'M'
        m_xpath = "//div[contains(@class, 'findpastpapers')]//li[(text()='M' or normalize-space(.)='M')]"
        alphabet_m = wait.until(EC.presence_of_element_located((By.XPATH, m_xpath)))
        safe_click(driver, alphabet_m, "Alphabet M")
        time.sleep(2)
        
        # Click Mathematics
        logging.info("Step 2c: Looking for Mathematics link...")
        math_xpath = "//div[contains(@class, 'findpastpapers')]//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mathematics')]"
        
        def math_finder(d):
            # Try specific container first
            try:
                container = d.find_element(By.CLASS_NAME, "findpastpapers")
                links = container.find_elements(By.XPATH, ".//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mathematics')]")
                for l in links:
                    if l.is_displayed(): return l
            except: pass
            
            # Global fallback
            links = d.find_elements(By.XPATH, math_xpath)
            for l in links:
                if l.is_displayed(): return l
            return False
            
        math_link = wait.until(math_finder)
        logging.info(f"Found Mathematics link: {math_link.text}")
        safe_click(driver, math_link, "Mathematics")
        time.sleep(3)
        
        # Step 3: Select Exam Series
        logging.info("Step 3: Selecting Exam Series...")
        time.sleep(2) # Base wait for accordion
        
        series_found = False
        # Wait for the series list to be present (any June link)
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'June')]")))
        except:
            logging.warning("Initial wait for series links timed out.")
            driver.save_screenshot("ms_series_missing.png")

        for year in ['2024', '2023', '2022', '2021']:
            try:
                xpath = f"//a[contains(text(), 'June {year}')]"
                series_opt = driver.find_element(By.XPATH, xpath)
                if series_opt.is_displayed():
                    logging.info(f"Clicking series: {series_opt.text}")
                    safe_click(driver, series_opt, series_opt.text)
                    series_found = True
                    break
            except: continue
        
        if not series_found:
            # Try any June link as fallback
            try:
                fallback_june = driver.find_element(By.XPATH, "//a[contains(text(), 'June')]")
                logging.info(f"Using fallback series: {fallback_june.text}")
                safe_click(driver, fallback_june, fallback_june.text)
                series_found = True
            except:
                logging.error("No suitable June series link found.")
                driver.save_screenshot("ms_no_series_found.png")
                return

        time.sleep(5)

        # Extract links for both Question Papers and Marking Schemes
        logging.info("Extracting all PDF links...")
        # Scroll to ensure all links load if lazy
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        all_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
        logging.info(f"Found {len(all_links)} total PDF links")
        
        paired_data = {} # { paper_id: { 'qp': link, 'ms': link, 'name': name } }
        
        for link in all_links:
            text = link.text.strip()
            href = link.get_attribute("href")
            if not href or not text: continue
            
            # 1. Clean the text: remove file size labels and normalize
            clean_text = re.sub(r'\(PDF.*?\)', '', text, flags=re.IGNORECASE).strip()
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            # 2. Extract strictly the Paper Code (e.g. 9MA0/01, WMA11/01, 8FM0-01)
            # This is our key for pairing.
            code_match = re.search(r'([A-Z0-9]{4,}(?:[-/][0-9]{2})?)', clean_text)
            paper_code = code_match.group(1).replace('/', '-') if code_match else None
            
            if not paper_code:
                # Fallback if no code: use a truncated name
                paper_code = clean_text[:30].replace(' ', '_')

            # 3. Create a clean folder name (Subject + Code)
            # Remove "Question paper" or "Marking scheme" from the start/end
            subject_name = re.sub(r'^(Question paper|Marking scheme|Mark scheme|QP|MS)\s*[-:]*\s*', '', clean_text, flags=re.IGNORECASE).strip()
            subject_name = re.sub(r'\s*[-:]*\s*(Question paper|Marking scheme|Mark scheme|QP|MS)$', '', subject_name, flags=re.IGNORECASE).strip()
            
            # Ensure paper_code is in the folder name
            folder_name = f"{subject_name} ({paper_code})" if paper_code not in subject_name else subject_name
            
            if paper_code not in paired_data:
                paired_data[paper_code] = {'qp': None, 'ms': None, 'folder': folder_name}
            
            if "question paper" in text.lower() or "qp" in text.lower():
                paired_data[paper_code]['qp'] = href
            elif any(term in text.lower() for term in ["marking scheme", "mark scheme", "ms"]):
                paired_data[paper_code]['ms'] = href

        results = {k: v for k, v in paired_data.items() if v['qp'] or v['ms']}
        logging.info(f"Grouped into {len(results)} paper entries.")

        # Download Logic
        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])
        session.headers.update({'User-Agent': driver.execute_script("return navigator.userAgent")})

        base_dir = "papers_paired"
        os.makedirs(base_dir, exist_ok=True)

        for paper_id, data in results.items():
            folder_name = "".join([c for c in data['folder'] if c.isalnum() or c in (' ', '-', '_', '(', ')')]).strip()
            paper_path = os.path.join(base_dir, folder_name)
            
            # Create subfolders
            qp_folder = os.path.join(paper_path, "paper")
            ms_folder = os.path.join(paper_path, "marking_scheme")
            
            # Download QP if exists
            if data['qp']:
                os.makedirs(qp_folder, exist_ok=True)
                qp_filename = os.path.basename(data['qp']).split('?')[0]
                logging.info(f"Downloading QP for {folder_name}...")
                try:
                    r = session.get(data['qp'], timeout=30)
                    if r.status_code == 200:
                        with open(os.path.join(qp_folder, qp_filename), "wb") as f:
                            f.write(r.content)
                except Exception as e: logging.error(f"QP Download error: {e}")

            # Download MS if exists
            if data['ms']:
                os.makedirs(ms_folder, exist_ok=True)
                ms_filename = os.path.basename(data['ms']).split('?')[0]
                logging.info(f"Downloading MS for {folder_name}...")
                try:
                    r = session.get(data['ms'], timeout=30)
                    if r.status_code == 200:
                        with open(os.path.join(ms_folder, ms_filename), "wb") as f:
                            f.write(r.content)
                except Exception as e: logging.error(f"MS Download error: {e}")
            else:
                logging.warning(f"No Marking Scheme found for {folder_name}")

        logging.info("All downloads completed.")
            
    except Exception as e:
        logging.error(f"Critical error: {e}")
        driver.save_screenshot("ms_scraper_error.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    download_paired_papers()
