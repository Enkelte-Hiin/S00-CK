from DrissionPage import Chromium, ChromiumOptions
import time
import os
import tempfile
import shutil
import json
import sys

# 设置 UTF-8 编码以支持中文（可选）
sys.stdout.reconfigure(encoding='utf-8')

def close_existing_browsers():
    try:
        result = os.system("taskkill /f /im msedge.exe")
        if result == 0:
            print("Closed all existing Edge browser processes")
        else:
            print("No Edge processes were found to close")
    except Exception as e:
        print(f"Error while closing browser processes: {e}")
    time.sleep(1)

# 检查 Edge 是否存在
edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge_path):
    print(f"Edge not found at default path: {edge_path}")
    # 尝试使用环境变量路径
    edge_path = os.getenv("ProgramFiles(x86)") + r"\Microsoft\Edge\Application\msedge.exe"
    print(f"Trying fallback path: {edge_path}")

close_existing_browsers()
temp_dir = tempfile.mkdtemp()
print(f"Using temporary user data directory: {temp_dir}")

options = ChromiumOptions()
options.set_paths(browser_path=edge_path)
options.set_argument("--window-size=1024,768")
options.set_argument("--window-position=0,0")
options.set_argument("--incognito")
options.set_argument(f"--user-data-dir={temp_dir}")
options.set_argument("--headless")  # 启用无头模式
options.set_argument("--no-sandbox")
options.set_argument("--disable-gpu")

try:
    browser = Chromium(options)
    tab = browser.latest_tab
    print("Successfully connected to Edge browser (incognito + new user data directory)!")
except Exception as e:
    print(f"Failed to connect to browser: {e}")
    shutil.rmtree(temp_dir, ignore_errors=True)
    exit()

try:
    tab.get("https://www.serv00.com/offer/create_new_account")
    tab.wait(10)
except Exception as e:
    print(f"Failed to navigate to target website: {e}")
    browser.quit()
    shutil.rmtree(temp_dir, ignore_errors=True)
    exit()

max_attempts = 20
attempt = 0
while attempt < max_attempts:
    try:
        iframe = tab.get_frame('@src:contains("challenges.cloudflare.com")')
        if iframe:
            checkbox = iframe.ele('@class:ctp-checkbox-label')
            if checkbox:
                checkbox.click()
                print(f"Attempt {attempt + 1}: Clicked checkbox via element locator")
            else:
                print(f"Attempt {attempt + 1}: Checkbox not found, falling back to coordinates")
                tab.actions.move_to((64, 290)).click()
        else:
            print(f"Attempt {attempt + 1}: iframe not found, falling back to coordinates")
            tab.actions.move_to((64, 290)).click()
    except Exception as e:
        print(f"Click failed: {e}")
        tab.actions.move_to((64, 290)).click()

    time.sleep(5)
    title = tab.title.lower()
    if "serv00.com" in title:
        print("Website title contains 'serv00.com', CAPTCHA passed")
        break
    elif "just a" in title:
        print("Website title contains 'just a', still verifying")
    else:
        print("Website title does not match, continuing attempts")
    attempt += 1

if attempt < max_attempts:
    cookies = tab.cookies()
    cf_clearance = next((cookie for cookie in cookies if cookie['name'] == 'cf_clearance'), None)
    if cf_clearance:
        print("Retrieved cf_clearance Cookie:", cf_clearance)
        with open("cf_clearance.json", "w") as f:
            json.dump({"cf_clearance": cf_clearance['value']}, f)
        print("Saved cf_clearance to cf_clearance.json")
    else:
        print("cf_clearance Cookie not found")
else:
    print("Reached maximum attempts, failed to pass CAPTCHA")

browser.quit()
shutil.rmtree(temp_dir, ignore_errors=True)
print("Cleaned up temporary user data directory")
