import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Keys
from DrissionPage.errors import ElementNotFound, PageDisconnectedError

# ======================
# 浏览器扩展配置（保持相同）
# ======================

def create_extension() -> str:
    """创建包含反检测脚本的临时扩展"""
    temp_dir = tempfile.mkdtemp(prefix='cf_ext_')
    manifest_path = os.path.join(temp_dir, 'manifest.json')
    script_path = os.path.join(temp_dir, 'script.js')
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(MANIFEST_CONTENT, f, indent=2)
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(SCRIPT_CONTENT.strip())
    
    return temp_dir

# ======================
# 浏览器配置（更新ChromiumPage使用）
# ======================
def get_configured_browser(headless=True) -> ChromiumPage:
    """配置带反检测扩展的浏览器实例"""
    co = ChromiumOptions()
    co.auto_port()
    co.no_imgs(True)  # 禁止加载图片加速
    co.set_paths(browser_path='/usr/bin/chromium-browser')  # 显式指定路径
    
    # Linux服务器必须参数
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-dev-shm-usage")
    co.set_argument("--remote-allow-origins=*")
    
    if headless:
        co.headless()  # 新版headless模式
    
    # 加载扩展
    ext_path = create_extension()
    co.add_extension(ext_path)
    
    browser = ChromiumPage(co)
    # 标记扩展目录以便后续清理
    browser._ext_tmp_dirs = [ext_path]
    return browser

# ======================
# 验证码处理核心逻辑（使用最新API）
# ======================
def handle_turnstile(page: ChromiumPage, max_attempts=3) -> bool:
    """处理Turnstile验证码的完整流程"""
    for attempt in range(1, max_attempts+1):
        try:
            print(f"\n=== Attempt {attempt}/{max_attempts} ===")
            
            # 新版等待元素API
            cf_wrapper = page.wait.ele('css:.cf-turnstile', timeout=15)
            if not cf_wrapper:
                raise ElementNotFound("Turnstile wrapper not found")
            
            # 处理Shadow DOM的新方式
            iframe = cf_wrapper.run_js('return this.shadowRoot.querySelector("iframe")')
            if not iframe:
                raise ElementNotFound("Turnstile iframe not found")
            
            # 切换到iframe
            page.wait.load_frame(iframe)
            
            # 定位复选框并点击
            checkbox = page.wait.ele('css:input[type="checkbox"]', timeout=10)
            checkbox.click(by_js=True)  # 使用JS点击更可靠
            
            # 验证成功检测
            return page.wait.ele(
                'css:.verifybox-success', 
                timeout=15, 
                display=True
            ) is not None
            
        except (ElementNotFound, PageDisconnectedError) as e:
            print(f"! Error: {str(e)[:80]}")
            if attempt < max_attempts:
                print("Reloading page...")
                page.refresh()
                page.wait.doc_loaded()
                time.sleep(2)
            else:
                raise
        except Exception as e:
            print(f"! Critical error: {str(e)}")
            raise

    return False

# ======================
# 主执行流程（更新异常处理）
# ======================
if __name__ == "__main__":
    browser = None
    try:
        # 初始化浏览器
        browser = get_configured_browser(headless=True)
        print("Browser initialized")
        
        # 访问目标页面
        target_url = "https://www.serv00.com/offer/create_new_account"
        print(f"Navigating to: {target_url}")
        browser.get(target_url)
        browser.wait.doc_loaded()
        
        # 执行验证流程
        if handle_turnstile(browser):
            print("\n=== SUCCESS ===")
            print("Turnstile bypass successful")
            
            # 获取cookies
            cookies = browser.cookies(as_dict=True)
            print("\nCookies obtained:")
            for k, v in cookies.items():
                print(f"{k}: {v[:50]}{'...' if len(v)>50 else ''}")
            
            # 保存cookies
            with open("cookies.json", 'w') as f:
                json.dump(cookies, f, indent=2)
        else:
            print("\n=== FAILURE ===")
            print("Turnstile bypass failed")

    except Exception as e:
        print(f"\n!!! MAIN ERROR: {str(e)}")
        if browser:
            browser.get_screenshot(path='error.png')
            print("Screenshot saved to error.png")
        
    finally:
        if browser:
            # 清理临时扩展目录
            for ext_dir in getattr(browser, '_ext_tmp_dirs', []):
                if os.path.exists(ext_dir):
                    shutil.rmtree(ext_dir, ignore_errors=True)
            # 关闭浏览器
            browser.quit()
            print("\nBrowser safely closed")
