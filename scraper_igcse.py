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
        logging.FileHandler("scraper_igcse_debug.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def setup_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless=new')  # Disabled so USER can see
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1280,800')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Using cached driver if available
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

def download_file(session, url, filepath):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        r = session.get(url, timeout=30)
        if r.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(r.content)
            logging.info(f"Downloaded: {os.path.basename(filepath)}")
            return True
        else:
            logging.warning(f"Failed to download {url}: Status {r.status_code}")
    except Exception as e:
        logging.error(f"Download error for {url}: {e}")
    return False

def download_igcse_papers():
    logging.info("Starting IGCSE Mathematics Scraper...")
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)
    base_folder = "papers_igcse"
    
    subjects_to_download = ["Mathematics B"] # Already finished Mathematics A
    
    try:
        driver.get("https://qualifications.pearson.com/en/support/support-topics/exams/past-papers.html")
        logging.info("Page loaded")
        
        # Cookie banner
        try:
            cookie_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            cookie_btn.click()
            time.sleep(2)
        except: pass

        # Step 1: Select International GCSE
        logging.info("Step 1: Selecting International GCSE...")
        igcse_xpath = "//div[contains(@class, 'findpastpapers')]//*[contains(text(), 'International GCSE') and not(ancestor::select)]"
        igcse = wait.until(EC.visibility_of_element_located((By.XPATH, igcse_xpath)))
        safe_click(driver, igcse, "International GCSE")
        time.sleep(3)

        for target_subject in subjects_to_download:
            logging.info(f"--- Processing {target_subject} ---")
            
            # Refresh page to ensure clean state
            driver.get("https://qualifications.pearson.com/en/support/support-topics/exams/past-papers.html")
            
            # Re-select Step 1
            logging.info(f"Re-selecting Step 1 for {target_subject}...")
            igcse_xpath = "//div[contains(@class, 'findpastpapers')]//*[contains(text(), 'International GCSE') and not(ancestor::select)]"
            igcse = wait.until(EC.visibility_of_element_located((By.XPATH, igcse_xpath)))
            safe_click(driver, igcse, "International GCSE")
            time.sleep(3)

            # Step 2: Select 'M' and then Subject
            logging.info("Step 2: Selecting Subject...")
            
            m_xpath = "//div[contains(@class, 'findpastpapers')]//li[(text()='M' or normalize-space(.)='M')]"
            alphabet_m = wait.until(EC.presence_of_element_located((By.XPATH, m_xpath)))
            safe_click(driver, alphabet_m, "Alphabet M")
            
            # Give it time to load the subjects
            time.sleep(5)
            
            sub_xpath = f"//div[contains(@class, 'findpastpapers')]//a[contains(normalize-space(.), '{target_subject}')]"
            subject_link = wait.until(EC.visibility_of_element_located((By.XPATH, sub_xpath)))
            safe_click(driver, subject_link, target_subject)
            time.sleep(2)
            
            # Step 2.5: Handle Modal
            logging.info(f"Checking for specification modal for {target_subject}...")
            try:
                time.sleep(4)
                click_success = driver.execute_script("""
                    var targetText = '(2016)';
                    var headers = document.querySelectorAll('h3');
                    for (var i = 0; i < headers.length; i++) {
                        if (headers[i].textContent.includes(targetText)) {
                            var link = headers[i].closest('a');
                            if (link) {
                                link.style.border = '5px solid red';
                                link.style.backgroundColor = 'yellow';
                                link.click();
                                var clickEvent = new MouseEvent('click', {'view': window, 'bubbles': true, 'cancelable': true});
                                link.dispatchEvent(clickEvent);
                                return true;
                            }
                        }
                    }
                    return false;
                """)
                if click_success:
                    logging.info("Target link found and clicked via aggressive JS.")
                else:
                    logging.warning(f"Aggressive JS could not find (2016) link for {target_subject}.")
                time.sleep(5)
            except Exception as modal_err:
                logging.info(f"Modal handling error for {target_subject}: {modal_err}")

            # Step 3: Iterate through Exam Series
            logging.info("Step 3: Iterating through Exam Series...")
            time.sleep(5)
            
            series_data = []
            try:
                container = driver.find_element(By.ID, "step3")
                links = container.find_elements(By.TAG_NAME, "a")
                for l in links:
                    t = l.get_attribute("innerText").strip()
                    if not t: t = l.text.strip()
                    
                    if re.search(r'(June|January|November|Summer|Winter)\s*20\d{2}', t, re.IGNORECASE):
                        if "2024" in t or "2025" in t:
                            continue
                        series_data.append(t)
            except Exception as e:
                logging.error(f"Error extracting series links: {e}")

            logging.info(f"Found {len(series_data)} target exam series: {series_data}")

            # Use session for downloads
            session = requests.Session()
            for cookie in driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

            for series_name in series_data:
                logging.info(f"--- Processing Series: {series_name} ---")
                try:
                    target_link = driver.find_element(By.XPATH, f"//div[@id='step3']//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{series_name.lower()}')]")
                    safe_click(driver, target_link, series_name)
                    time.sleep(5)
                    
                    # Step 4: Extract results
                    results_wait = WebDriverWait(driver, 15)
                    results_wait.until(EC.presence_of_element_located((By.ID, "resultsTable")))
                    
                    result_elements = driver.find_elements(By.XPATH, "//div[@id='resultsTable']//a[contains(@class, 'result-item')]")
                    paired_data = {}
                    
                    for res in result_elements:
                        href = res.get_attribute("href")
                        if not href or "javascript" in href.lower(): continue
                        
                        try:
                            title_el = res.find_element(By.CLASS_NAME, "doc-title")
                            title_text = title_el.get_attribute("innerText").strip()
                            logging.info(f"Link found: {title_text}")
                        except: continue
                        
                        clean_text = re.sub(r'\(PDF.*?\)','', title_text, flags=re.IGNORECASE).strip()
                        
                        # 1. Try to find the specific Paper Code (e.g. 4MA1/1F, 4MB1/01)
                        # We look for a code starting with 4 (IGCSE) or similar
                        code_match = re.search(r'([A-Z0-9]{4,}[-/][A-Z0-9]+)', clean_text)
                        paper_code = code_match.group(1).replace('/','-') if code_match else None
                        
                        # 2. Try to find "Paper X" (e.g. Paper 1F, Paper 2H, Paper 1)
                        paper_num_match = re.search(r'Paper\s*([A-Z0-9]+)', clean_text, re.IGNORECASE)
                        paper_num = paper_num_match.group(1) if paper_num_match else None
                        
                        if not paper_num and paper_code:
                            # Use the last part of the code if paper num is missing
                            paper_num = paper_code.split('-')[-1]
                        
                        if not paper_num:
                            paper_num = "Unknown"
                            
                        if not paper_code:
                            prefix = "4MA1" if "Mathematics A" in target_subject else "4MB1"
                            paper_code = f"{prefix}-{paper_num}" # Use correct prefix if missing

                        if paper_num not in paired_data:
                            paired_data[paper_num] = {'qp': [], 'ms': [], 'code': paper_code}

                        if any(term in title_text.lower() for term in ["question paper", "qp"]):
                            paired_data[paper_num]['qp'].append({'href': href, 'title': title_text})
                        elif any(term in title_text.lower() for term in ["marking scheme", "mark scheme", "ms"]):
                            paired_data[paper_num]['ms'].append({'href': href, 'title': title_text})

                    logging.info(f"Paired {len(paired_data)} papers for {series_name}: {list(paired_data.keys())}")
                    
                    for p_num, info in paired_data.items():
                        # Rel path: Subject -> Series -> Paper Number -> paper/marking_scheme
                        rel_path = os.path.join(base_folder, target_subject, series_name, f"Paper {p_num}")
                        
                        for i, qp_item in enumerate(info['qp']):
                            suffix = f"_{i+1}" if len(info['qp']) > 1 else ""
                            # Extract R if exists (e.g. 1R, 2R)
                            r_match = re.search(r'\b(\d+R)\b', qp_item['title'])
                            r_suffix = f"_{r_match.group(1)}" if r_match else ""
                            fname = f"Question_Paper_{info['code']}{r_suffix}{suffix}.pdf"
                            download_file(session, qp_item['href'], os.path.join(rel_path, "paper", fname))
                        
                        for i, ms_item in enumerate(info['ms']):
                            suffix = f"_{i+1}" if len(info['ms']) > 1 else ""
                            r_match = re.search(r'\b(\d+R)\b', ms_item['title'])
                            r_suffix = f"_{r_match.group(1)}" if r_match else ""
                            fname = f"Marking_Scheme_{info['code']}{r_suffix}{suffix}.pdf"
                            download_file(session, ms_item['href'], os.path.join(rel_path, "marking_scheme", fname))
                            
                except Exception as e:
                    logging.error(f"Error processing series {series_name}: {e}")
                
                # Go back to Step 3 for next series
                try:
                    step3_header = driver.find_element(By.XPATH, "//div[@id='step3']//h3")
                    safe_click(driver, step3_header, "Step 3 Header to Reset")
                    time.sleep(2)
                except: pass

    except Exception as e:
        logging.error(f"Critical error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    download_igcse_papers()
