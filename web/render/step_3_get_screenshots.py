import math
import os
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import tempfile


chrome_path = os.environ.get("CHROME", "./chrome/chrome-linux64/chrome")
chrome_driver_path = os.environ.get("CHROME_DRIVER", "./chrome/chromedriver-linux64/chromedriver")

def make_driver(width: int = 1024, height: int = 768, user_data_dir: str = "chrome_data") -> webdriver.Chrome:
    """Create a headless Chrome WebDriver with a fixed viewport."""
    opts = Options()
    opts.add_argument("--headless=new")        # Chrome 109+ run a process in the background without displaying images 
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")          # Required for running as root
    opts.add_argument(f"--window-size={width},{height}")
    
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir, exist_ok=True)
    opts.add_argument(f"--user-data-dir={user_data_dir}")
    
    opts.binary_location = chrome_path
    service = Service(executable_path=chrome_driver_path)
    
    return webdriver.Chrome(service=service, options=opts) 


def capture_scroll_screenshots(url: str,
                               out_dir: str = "shots",
                               user_data_dir: str = "chrome_data",
                               max_shots: int = 3,
                               pause: float = 0.4,
                               viewport_height: int = 768) -> None:
    """Scroll the page, saving at most `max_shots` screenshots."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    driver = make_driver(height=viewport_height, user_data_dir=user_data_dir)
    try:
        driver.get(url)
    except Exception as e:
        # print(f"Error loading page: {e}")
        driver.quit()
        return

    # Give the page a moment to settle.
    time.sleep(pause)

    total_height = driver.execute_script("return document.body.scrollHeight")
    n_required   = math.ceil(total_height / viewport_height) 
    n_to_take    = min(max_shots, max(n_required, 1)) 

    for idx in range(n_to_take):
        time.sleep(pause)  # wait for lazy‑loaded images, JS, etc.
        
        # File names: shot_1.png, shot_2.png, …
        fname = os.path.join(out_dir, f"shot_{idx + 1}.png")
        driver.save_screenshot(fname)
        # print(f"Saved {fname}")

        # Break early if we're already at (or past) the bottom.
        if (idx + 1) == n_to_take:
            break

        # Scroll down exactly one viewport height.
        driver.execute_script("window.scrollBy(0, arguments[0]);", viewport_height)

    driver.quit()
    return out_dir
    