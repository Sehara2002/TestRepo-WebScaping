import os
import time
import re
import requests
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_debug.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def dump_section(driver, selector, filename):
    try:
        element = driver.find_element(By.CSS_SELECTOR, selector)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(element.get_attribute("outerHTML"))
        logging.info(f"Dumped section {selector} to {filename}")
    except:
        logging.warning(f"Failed to dump section {selector}")

def setup_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless=new') # Enabled for faster execution if needed
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Hardcoded path to cached driver to bypass network issues
    driver_path = r"C:\Users\sheha\.wdm\drivers\chromedriver\win64\144.0.7559.96\chromedriver-win32\chromedriver.exe"
    service = Service(driver_path)
    return webdriver.Chrome(service=service, options=options)

def safe_click(driver, element, name="Element"):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(element))
        element.click()
        logging.info(f"Clicked {name} (Standard)")
        return True
    except:
        try:
            driver.execute_script("arguments[0].click();", element)
            logging.info(f"Clicked {name} (JS)")
            return True
        except Exception as e:
            logging.error(f"Failed to click {name}: {e}")
            return False

def download_papers():
    logging.info("Starting Selenium Scraper Proof of Concept...")
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)
    
    try:
        driver.get("https://qualifications.pearson.com/en/support/support-topics/exams/past-papers.html")
        logging.info(f"Page loaded: {driver.current_url}")
        
        # Cookie banner
        try:
            cookie_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            cookie_btn.click()
            logging.info("Cookies accepted")
            time.sleep(1)
        except:
            logging.info("No cookie banner found")

        # Find findpastpapers section
        findpastpapers = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "findpastpapers")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", findpastpapers)
        time.sleep(2)
        dump_section(driver, ".findpastpapers", "findpastpapers_initial.html")
        
        # Step 1: Select A Level
        logging.info("Step 1: Selecting A Level...")
        alevel_xpath = "//div[contains(@class, 'findpastpapers')]//*[contains(text(), 'A Level') and not(ancestor::select)]"
        alevel = wait.until(EC.visibility_of_element_located((By.XPATH, alevel_xpath)))
        safe_click(driver, alevel, "A Level")
        time.sleep(3)
        logging.info(f"After Step 1: {driver.current_url}")
        driver.save_screenshot("selenium_after_alevel.png")
        
        # Ensure we are still on the same page
        if "past-papers.html" not in driver.current_url:
            logging.warning("Navigated away from past-papers page! Reloading...")
            driver.get("https://qualifications.pearson.com/en/support/support-topics/exams/past-papers.html")
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "findpastpapers")))
            # Re-select A Level if needed (usually it remembers or we just try again)
        
        # Step 2: Select Mathematics
        logging.info("Step 2: Selecting Mathematics...")
        
        # 2a: Switch to Current qualifications
        try:
            current_tab = driver.find_element(By.XPATH, "//div[contains(@class, 'findpastpapers')]//a[contains(text(), 'Current qualifications')]")
            if current_tab.is_displayed():
                safe_click(driver, current_tab, "Current qualifications tab")
                time.sleep(2)
        except: pass
        
        # 2b: Click 'M'
        logging.info("Step 2b: Clicking 'M'...")
        try:
            # Try a very direct XPath for the 'M' in the alphabet grid
            m_xpath = "//div[contains(@class, 'findpastpapers')]//li[(text()='M' or normalize-space(.)='M')]"
            alphabet_m = wait.until(EC.presence_of_element_located((By.XPATH, m_xpath)))
            
            # Use JS to click if standard fails
            for _ in range(2):
                safe_click(driver, alphabet_m, "Alphabet M")
                time.sleep(1)
                # Check for Mathematics
                if "Mathematics" in driver.page_source:
                    break
            driver.save_screenshot("selenium_after_m.png")
        except Exception as e:
            logging.warning(f"Alphabet M click failed: {e}")
            dump_section(driver, ".findpastpapers", "findpastpapers_error.html")
        
        # 2c: Click Mathematics
        logging.info("Step 2c: Looking for Mathematics link...")
        try:
            # Flexible case-insensitive search
            math_xpath = "//div[contains(@class, 'findpastpapers')]//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mathematics')]"
            
            def math_finder(d):
                links = d.find_elements(By.XPATH, math_xpath)
                for l in links:
                    if l.is_displayed(): return l
                return False
                
            math_link = wait.until(math_finder)
            logging.info(f"Found Mathematics link: {math_link.text}")
            safe_click(driver, math_link, "Mathematics")
            time.sleep(3)
            driver.save_screenshot("selenium_after_math.png")
        except Exception as e:
            logging.error(f"Failed to find Mathematics: {e}")
            dump_section(driver, ".findpastpapers", "findpastpapers_no_math.html")
            # Try a very broad fallback
            try:
                math_fallback = driver.find_element(By.LINK_TEXT, "Mathematics")
                safe_click(driver, math_fallback, "Mathematics (Fallback)")
            except: pass
        
        # Step 3: Select Exam Series
        logging.info("Step 3: Selecting Exam Series...")
        time.sleep(2)
        
        series_found = False
        for year in ['2024', '2023', '2022', '2021', '2025']:
            try:
                series_xpath = f"//a[contains(text(), 'June {year}')]"
                series_opt = driver.find_element(By.XPATH, series_xpath)
                if series_opt.is_displayed():
                    series_name = series_opt.text.strip()
                    logging.info(f"Clicking series: {series_name}")
                    safe_click(driver, series_opt, series_name)
                    series_found = True
                    break
            except: continue
            
        if not series_found:
            try:
                fallback_june = driver.find_element(By.XPATH, "//a[contains(text(), 'June')]")
                safe_click(driver, fallback_june, "Fallback June")
                series_found = True
            except:
                logging.warning("No June series found")

        if series_found:
            time.sleep(5)
            driver.save_screenshot("selenium_after_series.png")
            
        # Step 4: Content Type
        logging.info("Step 4: Checking for Question paper filter...")
        try:
            qp_xpath = "//li[contains(., 'Question paper')] | //span[contains(text(), 'Question paper')]"
            qp_filter = driver.find_element(By.XPATH, qp_xpath)
            safe_click(driver, qp_filter, "Question paper filter")
            time.sleep(5)
        except:
            logging.info("No content type filter found")

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.save_screenshot("selenium_results.png")
        
        # Extract PDFs
        logging.info("Looking for PDF links...")
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
        logging.info(f"Found {len(links)} total PDF links")
        
        if links:
            download_dir = "papers/mathematics2"
            if not os.path.exists(download_dir): os.makedirs(download_dir)
            
            # Prepare session for requests
            session = requests.Session()
            for cookie in driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            user_agent = driver.execute_script("return navigator.userAgent")
            session.headers.update({'User-Agent': user_agent})

            count = 0
            for link in links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute("href")
                    if not href: continue
                    
                    if any(term in text.lower() for term in ["question paper", "qp"]):
                        filename = "".join([c for c in f"{text[:50]}.pdf" if c.isalnum() or c in (' ', '-', '_', '.')]).strip()
                        logging.info(f"Downloading: {filename} from {href}")
                        
                        try:
                            res = session.get(href, timeout=30)
                            if res.status_code == 200:
                                with open(os.path.join(download_dir, filename), "wb") as f:
                                    f.write(res.content)
                                count += 1
                                logging.info(f"Successfully downloaded {filename}")
                            else:
                                logging.error(f"Failed status: {res.status_code}")
                        except Exception as e:
                            logging.error(f"Download error: {e}")
                except: pass
            logging.info(f"Total downloaded: {count}")
        else:
            logging.warning("No PDF links found")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        driver.save_screenshot("selenium_error.png")
    finally:
        driver.quit()
        logging.info("Driver closed")

if __name__ == "__main__":
    download_papers()
