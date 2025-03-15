import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, BrowserConnectError

# ======================
# 扩展配置（兼容4.1.x版本）
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "Turnstile Helper",
    "version": "1.0",
    "content_scripts": [{
        "js": ["content.js"],
        "matches": ["<all_urls>"],
        "run_at": "document_start",
        "all_frames": True,
        "world": "MAIN"
    }]
}

SCRIPT_CONTENT = """
// 基础反检测逻辑
Object.defineProperties(MouseEvent.prototype, {
    'screenX': { value: Math.floor(Math.random() * 1200 + 800) },
    'screenY': { value: Math.floor(Math.random() * 600 + 400) }
});
"""

# ======================
# 浏览器初始化（兼容4.1.x）
# ======================
def create_extension():
    """创建临时扩展目录"""
    temp_dir = tempfile.mkdtemp(prefix='cf_ext_')
    with open(os.path.join(temp_dir, 'manifest.json'), 'w') as f:
        json.dump(MANIFEST_CONTENT, f)
    with open(os.path.join(temp_dir, 'content.js'), 'w') as f:
        f.write(SCRIPT_CONTENT)
    return temp_dir

def get_browser(headless=True):
    """配置浏览器实例"""
    co = ChromiumOptions()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    
    if headless:
        co.headless()
    
    ext_dir = create_extension()
    co.add_extension(ext_dir)
    
    try:
        browser = ChromiumPage(addr_or_opts=co)
        browser._temp_dirs = [ext_dir]
        return browser
    except Exception as e:
        shutil.rmtree(ext_dir, ignore_errors=True)
        raise

# ======================
# 验证码处理（兼容4.1.x）
# ======================
def bypass_turnstile(page, max_retry=3):
    """验证码处理流程"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n尝试第 {retry} 次")
            
            # 定位验证组件
            container = page.ele('.cf-turnstile', timeout=30)
            
            # 处理iframe
            iframe = container.run_js('return this.shadowRoot.querySelector("iframe")')
            page.switch_to.frame(iframe)
            
            # 点击复选框
            checkbox = page.ele('input[type="checkbox"]', timeout=20)
            checkbox.click()
            
            # 验证结果
            if page.ele('.verifybox-success', timeout=15):
                print("验证成功")
                return True
            
        except ElementNotFoundError as e:
            print(f"元素未找到: {str(e)[:50]}")
            page.refresh()
            time.sleep(3)
        except Exception as e:
            print(f"错误: {str(e)}")
            if retry == max_retry:
                page.get_screenshot('error.png')
                raise

    return False

# ======================
# 主流程
# ======================
if __name__ == "__main__":
    browser = None
    try:
        browser = get_browser(headless=True)
        browser.get('https://www.serv00.com/offer/create_new_account')
        
        if bypass_turnstile(browser):
            print("\n成功获取Cookies:")
            cookies = browser.get_cookies()
            print(json.dumps(cookies, indent=2))
            
            with open("cookies.json", 'w') as f:
                json.dump(cookies, f, indent=2)
        else:
            print("\n验证失败")
            
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        if browser:
            for d in getattr(browser, '_temp_dirs', []):
                shutil.rmtree(d, ignore_errors=True)
            browser.quit()
