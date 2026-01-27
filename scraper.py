import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
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
        # 1. Try standard click
        element.click()
        print(f"Clicked {name} (Standard)")
        return True
    except Exception as e1:
        # print(f"Standard click failed for {name}: {e1}")
        try:
            # 2. JS Click
            driver.execute_script("arguments[0].click();", element)
            print(f"Clicked {name} (JS)")
            return True
        except Exception as e2:
            try:
                # 3. Action Chains
                actions = ActionChains(driver)
                actions.move_to_element(element).click().perform()
                print(f"Clicked {name} (ActionChains)")
                return True
            except Exception as e3:
                print(f"Failed to click {name}: {e3}")
                return False

def download_file(url, folder, filename, driver_cookies):
    if not os.path.exists(folder): os.makedirs(folder)
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath): return
    try:
        s = requests.Session()
        for c in driver_cookies: s.cookies.set(c['name'], c['value'])
        r = s.get(url, stream=True)
        if 'application/pdf' in r.headers.get('Content-Type', '').lower():
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(8192): f.write(chunk)
            print(f"Downloaded: {filename}")
    except Exception as e:
        print(f"DL Error {filename}: {e}")

def run():
    print("V13 Robust Scraper")
    driver = setup_driver()
    try:
        driver.get("https://qualifications.pearson.com/en/support/support-topics/exams/past-papers.html")
        time.sleep(5)

        # Cookie
        try:
            btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            btn.click()
            print("Cookies accepted")
            time.sleep(2)
        except: pass

        # 1. A Level
        print("Step 1: A Level")
        qf = driver.find_element(By.ID, "qfSearchField")
        safe_click(driver, qf, "QF Dropdown")
        time.sleep(1)
        
        alevel = driver.find_element(By.XPATH, "//*[contains(text(), 'A Level')]")
        safe_click(driver, alevel, "A Level Option")
        time.sleep(3)

        # 2. Subject
        print("Step 2: Subject")
        # Find M
        m_els = driver.find_elements(By.XPATH, "//*[translate(normalize-space(text()), ' ', '') = 'M']")
        for m in m_els:
            if m.is_displayed():
                safe_click(driver, m, "M Block")
                break
        time.sleep(2)
        
        # Find Math
        math_els = driver.find_elements(By.XPATH, "//*[normalize-space(text()) = 'Mathematics']")
        for m in math_els:
            if m.is_displayed():
                safe_click(driver, m, "Mathematics Link")
                break
        time.sleep(3)

        # 3. Series
        print("Step 3: Series")
        es = driver.find_element(By.ID, "esSearchField")
        safe_click(driver, es, "Series Dropdown")
        time.sleep(1)
        es.send_keys("June")
        time.sleep(2)
        
        # Select recent
        series_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'June')]")
        target = None
        for s in series_els:
            if s.is_displayed() and ("2023" in s.text or "2022" in s.text):
                target = s
                break
        if not target:
             # Fallback
             for s in series_els:
                 if s.is_displayed(): target = s; break
        
        if target:
            txt = target.text
            print(f"Selecting Series: {txt}")
            safe_click(driver, target, "Series Option")
            print("Waiting 30s for auto-load...")
            time.sleep(30)
            
            # Check results
            links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Question paper')]")
            print(f"Found {len(links)} Question Paper links.")
            
            if len(links) > 0:
                cookies = driver.get_cookies()
                folder = f"papers/{txt.strip().replace(' ', '_')}"
                for l in links[:3]:
                    if l.is_displayed():
                        url = l.get_attribute("href")
                        name = l.text.strip()[:50] + ".pdf"
                        download_file(url, folder, name, cookies)
            else:
                print("No links found.")
        else:
            print("No series found")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run()
