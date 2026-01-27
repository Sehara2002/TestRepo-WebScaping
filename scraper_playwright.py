import os
import logging
import re
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_debug.log", mode='w'),
        logging.StreamHandler()
    ]
)

def download_papers():
    """Main function to scrape and download past papers using Playwright"""
    
    with sync_playwright() as p:
        # Launch browser (headless=False to see what's happening)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        try:
            logging.info("Starting scraper...")
            
            # Navigate to the page with increased timeout
            page.goto("https://qualifications.pearson.com/en/support/support-topics/exams/past-papers.html", timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            logging.info("Page loaded (DOM content loaded)")
            
            # Handle cookie banner
            try:
                page.click("#onetrust-accept-btn-handler", timeout=5000)
                logging.info("Cookies accepted")
                page.wait_for_timeout(2000)
            except:
                logging.info("No cookie banner found or already accepted")
            
            # Find the findpastpapers section
            logging.info("Looking for findpastpapers section...")
            # Use a broader wait
            page.wait_for_selector(".findpastpapers", timeout=30000)
            findpastpapers = page.locator(".findpastpapers")
            logging.info("Found findpastpapers section")
            
            # Scroll to it
            findpastpapers.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            page.screenshot(path="playwright_initial.png")
            
            # Step 1: Select A Level
            logging.info("Step 1: Selecting A Level...")
            alevel = page.get_by_text("A Level", exact=True).filter(visible=True).first
            alevel.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            alevel.click(force=True)
                
            logging.info("Clicked A Level")
            page.wait_for_timeout(3000)
            page.screenshot(path="playwright_after_alevel.png")
            
            # Step 2: Select Mathematics
            logging.info("Step 2: Selecting Mathematics...")
            page.wait_for_timeout(2000)
            
            # 2a: Switch to Current qualifications
            try:
                current_tab = page.get_by_text("Current qualifications").filter(visible=True).first
                if current_tab.count() > 0:
                    current_tab.click(force=True)
                    logging.info("Switched to Current qualifications tab")
                    page.wait_for_timeout(1000)
            except: pass
            
            # 2b: Click 'M'
            try:
                alphabet_m = page.get_by_text("M", exact=True).filter(visible=True).first
                if alphabet_m.count() > 0:
                    alphabet_m.click(force=True)
                    logging.info("Clicked 'M' in alphabet grid")
                    page.wait_for_timeout(2000)
                    page.screenshot(path="playwright_after_m.png")
            except: pass
            
            # 2c: Finally click Mathematics
            logging.info("Step 2c: Looking for Mathematics link...")
            try:
                # Use a more flexible regex to handle potential suffixes or spacing
                math = page.get_by_role("link").filter(has_text=re.compile(r"Mathematics", re.I)).filter(visible=True).first
                math.wait_for(state="visible", timeout=15000)
                link_text = math.text_content().strip()
                logging.info(f"Found Mathematics link: {link_text}")
                math.click(force=True)
                logging.info(f"Successfully clicked {link_text}")
                page.wait_for_timeout(3000)
                page.screenshot(path="playwright_after_math.png")
            except Exception as e:
                logging.error(f"Failed to click Mathematics: {e}")
                # Fallback to any element with the text
                try:
                    page.get_by_text("Mathematics", exact=False).filter(visible=True).first.click(force=True)
                    logging.info("Fallback Mathematics click successful")
                except:
                    page.screenshot(path="playwright_math_error.png")
                    raise
            
            # Step 3: Select Exam Series
            logging.info("Step 3: Selecting Exam Series...")
            try:
                # Wait for interaction
                page.wait_for_timeout(3000)
                
                # Check for any "June" text
                june_elements = page.get_by_text("June", exact=False).filter(visible=True).all()
                logging.info(f"Found {len(june_elements)} visible elements with 'June'")
                for el in june_elements:
                    text = el.text_content().strip()
                    logging.info(f"Found June candidate: {text}")
                
                series_found = False
                for year in ['2024', '2023', '2022', '2021', '2025']:
                    series_opt = page.get_by_text(re.compile(f"June {year}"), exact=False).filter(visible=True).first
                    if series_opt.count() > 0:
                        series_name = series_opt.text_content().strip()
                        logging.info(f"Clicking series: {series_name}")
                        series_opt.click(force=True)
                        logging.info(f"Selected Series: {series_name}")
                        series_found = True
                        break
                
                if not series_found and len(june_elements) > 0:
                    logging.info("Clicking first available June series as fallback")
                    june_elements[0].click(force=True)
                    series_found = True
                
                if series_found:
                    page.wait_for_timeout(5000)
                    page.screenshot(path="playwright_after_series.png")
                else:
                    logging.warning("No June series found to click")
            except Exception as e:
                logging.warning(f"Error during series selection: {e}")
            
            # Step 4: Content Type and Results
            logging.info("Step 4: Checking for Question paper filter...")
            try:
                page.wait_for_timeout(3000)
                qp_filter = page.get_by_text("Question paper", exact=False).filter(visible=True).first
                if qp_filter.count() > 0:
                    qp_filter.click(force=True)
                    logging.info("Selected Question paper filter")
                    page.wait_for_timeout(5000)
            except: pass
            
            # Final capture
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            page.screenshot(path="playwright_results.png")
            
            # Extract PDF links
            logging.info("Looking for PDF links...")
            links = page.locator("a[href*='.pdf']").all()
            logging.info(f"Found {len(links)} total PDF links")
            
            if links:
                download_dir = "papers/mathematics2"
                os.makedirs(download_dir, exist_ok=True)
                count = 0
                # Use a session for potentially better performance/cookie handling if needed
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                
                for link in links:
                    try:
                        text = link.text_content().strip()
                        href = link.get_attribute("href")
                        
                        if not href: continue
                        
                        # Resolve relative URLs if any
                        if href.startswith("/"):
                            href = "https://qualifications.pearson.com" + href
                        
                        # Filter for question papers
                        if any(term in text.lower() for term in ["question paper", "qp"]):
                            filename = "".join([c for c in f"{text[:50]}.pdf" if c.isalnum() or c in (' ', '-', '_', '.')]).strip()
                            
                            logging.info(f"Downloading via requests: {filename} from {href}")
                            try:
                                response = session.get(href, timeout=30)
                                if response.status_code == 200:
                                    with open(os.path.join(download_dir, filename), "wb") as f:
                                        f.write(response.content)
                                    count += 1
                                    logging.info(f"Successfully downloaded {filename}")
                                else:
                                    logging.error(f"Failed to download {filename}: Status {response.status_code}")
                            except Exception as dl_err:
                                logging.error(f"Request failed for {filename}: {dl_err}")
                    except: pass
                logging.info(f"Downloaded {count} papers successfully")
            else:
                logging.warning("No PDF links found!")
                with open("playwright_no_results.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
            
        except Exception as e:
            logging.error(f"Error: {e}")
            page.screenshot(path="playwright_error.png")
            
        finally:
            browser.close()
            logging.info("Browser closed")

if __name__ == "__main__":
    download_papers()
