import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, BrowserConnectError

# ======================
# 扩展配置（保持相同）
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "CF Bypass Pro",
    "version": "2.1",
    "content_scripts": [{
        "js": ["content.js"],
        "matches": ["<all_urls>"],
        "run_at": "document_start",
        "all_frames": True,
        "world": "MAIN"
    }]
}

SCRIPT_CONTENT = """
// 保持原有的反检测逻辑
const randomRange = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
Object.defineProperties(MouseEvent.prototype, {
    'screenX': { get: () => randomRange(800, 2000) },
    'screenY': { get: () => randomRange(400, 1200) }
});
"""

# ======================
# 修复后的浏览器初始化
# ======================
def create_extension():
    """创建临时扩展目录"""
    temp_dir = tempfile.mkdtemp(prefix='cf_ext_')
    with open(os.path.join(temp_dir, 'manifest.json'), 'w') as f:
        json.dump(MANIFEST_CONTENT, f, indent=2)
    with open(os.path.join(temp_dir, 'content.js'), 'w') as f:
        f.write(SCRIPT_CONTENT.strip())
    return temp_dir

def get_browser(headless=True):
    """配置浏览器实例（移除无效的cookie操作）"""
    co = ChromiumOptions()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--remote-allow-origins=*')
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    co.set_argument('--window-size=1920,1080')
    
    if headless:
        co.headless()
    
    ext_dir = create_extension()
    co.add_extension(ext_dir)
    
    try:
        browser = ChromiumPage(addr_or_opts=co, timeout=60)
        browser._temp_dirs = [ext_dir]
        
        # 修复：使用正确的CDP命令执行方式
        browser.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            '''
        })
        return browser
    except Exception as e:
        shutil.rmtree(ext_dir, ignore_errors=True)
        raise

# ======================
# 验证码处理逻辑（保持相同）
# ======================
def bypass_turnstile(page, max_retry=3):
    """验证码处理流程"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n🔄 第 {retry} 次尝试")
            page.wait.load_start()
            
            container = page.wait.ele(
                'css:.cf-turnstile, css:[data-sitekey], css:iframe[src*="challenges.cloudflare.com"]', 
                timeout=30
            )
            
            iframe = container.run_js('''
                return arguments[0].shadowRoot?.querySelector('iframe') 
                    || arguments[0].querySelector('iframe');
            ''', container)
            
            if not iframe:
                page.get_screenshot(f'iframe_error_{retry}.png')
                raise ElementNotFoundError("验证框架未找到")
            
            page.switch_to.frame(iframe)
            checkbox = page.wait.ele('css:input[type="checkbox"], css:.checkbox-label', timeout=25)
            page.actions.move_to(checkbox).click().perform()
            
            if any([
                page.wait.ele('.verifybox-success', timeout=20),
                page.wait.ele_text_contains('验证成功', timeout=15)
            ]):
                print("✅ 验证成功")
                return True
            
            page.refresh()
            time.sleep(3)
            
        except ElementNotFoundError as e:
            print(f"⚠️ 元素未找到: {str(e)[:50]}")
            page.get_screenshot(f'element_error_{retry}.png')
            page.refresh()
            time.sleep(5)
        except Exception as e:
            print(f"❌ 异常错误: {str(e)}")
            if retry == max_retry:
                page.get_screenshot('final_error.png')
                raise

    return False

# ======================
# 主流程（保持相同）
# ======================
if __name__ == "__main__":
    browser = None
    try:
        for _ in range(3):
            try:
                browser = get_browser(headless=True)
                break
            except BrowserConnectError as e:
                if _ == 2: raise
                print(f"🔁 浏览器连接失败，第 {_+1} 次重试...")
                time.sleep(10)
        
        target_url = "https://www.serv00.com/offer/create_new_account"
        print(f"🌐 正在访问 {target_url}")
        browser.get(target_url, retry=3, interval=3, timeout=60)
        browser.wait.load_start()
        
        if bypass_turnstile(browser):
            print("\n🎉 成功获取Cookies:")
            cookies = browser.cookies(as_dict=True)
            print(json.dumps(cookies, indent=2, ensure_ascii=False))
            
            with open("cookies.json", 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
        else:
            print("\n❌ 验证失败")
            
    except Exception as e:
        print(f"💥 致命错误: {str(e)}")
    finally:
        if browser:
            for d in getattr(browser, '_temp_dirs', []):
                shutil.rmtree(d, ignore_errors=True)
            browser.quit()
            print("\n🛑 浏览器已安全关闭")
