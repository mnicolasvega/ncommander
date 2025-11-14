from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from task.BaseTask import BaseTask
from typing import Any, Dict
from webdriver_manager.chrome import ChromeDriverManager
import os
import time

load_dotenv()
CHROME_LOCATION = os.getenv('CHROME_PATH')
DRIVER_PATH = os.getenv('DRIVER_PATH')
CAPTURE_SCREENSHOT = False
CAPTURE_HTML = True

class BaseSeleniumTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()

    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        try:
            dir_root = carry.get('outdir')
            date_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            url = self._get_mandatory(carry, 'url')
            script = self._get_mandatory(carry, 'script')
            sleep_seconds = self._get_optional(carry, 'sleep_seconds', 0)
            hidden = self._get_optional(carry, 'hidden', True)
            scroll_down = self._get_optional(carry, 'scroll_down', False)

            chrome_options = Options()
            if CHROME_LOCATION:
                chrome_options.binary_location = CHROME_LOCATION
            if hidden:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-setuid-sandbox")
            chrome_options.add_argument("--remote-debugging-port=9222")
            self._print(f"opening url: {url}")
            if DRIVER_PATH and os.path.exists(DRIVER_PATH):
                service = Service(DRIVER_PATH)
            else:
                service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get(url)
            if sleep_seconds:
                self._print(f"sleeping {sleep_seconds} secs")
                time.sleep(sleep_seconds)
            if scroll_down:
                self._print("scrolling down")
                self._scroll_down(driver, 2)

            screenshot_path = None
            if CAPTURE_SCREENSHOT:
                screenshot_path = f"{dir_root}/{script} {date_time} .png"
                self._print(f"taking screenshot: '{screenshot_path}'")
                driver.save_screenshot(screenshot_path)

            html = driver.page_source
            driver.quit()
            log_path = ''
            if CAPTURE_HTML:
                log_path = self._get_task_log_dir(dir_root, f"{date_time} {script}.html")
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(html)
            return {
                "url": url,
                "script": script,
                "screenshot_path": screenshot_path,
                'html': html,
                "html_log_path": log_path,
                "html_length": len(html) if html else 0,
            }
        except Exception as e:
            self._print(f"error while scraping: {e}")
            self._print(f"error cause: {e.__cause__}")
            return {}

    def text_output(self, data: Dict[str, Any]) -> str:
        html = data.get('html', '')
        if not html:
            return ''
        soup = BeautifulSoup(html, 'html.parser')
        body = soup.find('body')
        return body.text

    def html_output(self, data: Dict[str, Any]) -> str:
        html = data.get('html', '')
        if not html:
            return ''
        soup = BeautifulSoup(html, 'html.parser')
        body = soup.find('body')
        return body.html

    def interval(self) -> int:
        return 2 * 60

    def name(self) -> str:
        return "selenium_scrap_script"

    def dependencies(self) -> Dict[str, Any]:
        return {
            "pip": [
                "selenium",
                "webdriver-manager",
                "python-dotenv",
                "beautifulsoup4",
            ],
            "other": [
                "chromium",
                "chromium-driver",
                "fonts-liberation",
                "libnss3",
                "libxss1",
                "libasound2",
                "libgbm1"
            ],
            "env": [
                "CHROME_PATH=/usr/bin/chromium",
                "DRIVER_PATH=/usr/bin/chromedriver",
                "PYTHONUNBUFFERED=1",
                "PYTHONDONTWRITEBYTECODE=1"
            ]
        }   

    def requires_connection(self) -> bool:
        return True

    def max_time_expected(self) -> float | None:
        return 60.0

    def _get_mandatory(self, parameters: Dict[str, Any], key: str):
        if key not in parameters.keys():
            raise Exception(f"Missing parameter: '{key}'")
        return parameters[key]

    def _get_optional(self, parameters: Dict[str, Any], key: str, default):
        if key in parameters.keys():
            return parameters[key]
        else:
            return default

    def _scroll_down(self, driver, sleep_seconds: int) -> None:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_seconds)
