import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, BrowserConnectError

# ======================
# 扩展配置（优化版）
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "CF Bypass Expert",
    "version": "3.0",
    "content_scripts": [{
        "js": ["content.js"],
        "matches": ["<all_urls>"],
        "run_at": "document_start",
        "all_frames": True,
        "world": "MAIN"
    }]
}

SCRIPT_CONTENT = """
// 强化浏览器指纹保护
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });

const randomVal = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
Object.defineProperties(MouseEvent.prototype, {
    'screenX': { get: () => randomVal(800, 2000) },
    'screenY': { get: () => randomVal(400, 1200) }
});
"""

# ======================
# 浏览器初始化（兼容旧版API）
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
    """配置浏览器实例"""
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
        # 使用更兼容的初始化方式
        browser = ChromiumPage(addr_or_opts=co, timeout=60)
        browser._temp_dirs = [ext_dir]
        return browser
    except Exception as e:
        shutil.rmtree(ext_dir, ignore_errors=True)
        raise

# ======================
# 验证码处理逻辑（优化定位策略）
# ======================
def bypass_turnstile(page, max_retry=3):
    """验证码处理流程"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n🔄 第 {retry} 次尝试")
            
            # 智能等待页面核心元素
            page.wait.ele('css:body', timeout=60)
            
            # 使用混合定位策略
            container = page.wait.ele(
                'css:div[data-sitekey], css:.cf-turnstile, css:iframe[src*="challenges.cloudflare.com"]', 
                timeout=40
            )
            
            # 处理iframe嵌套
            iframe = container.run_js('''
                let iframe = arguments[0].shadowRoot?.querySelector('iframe');
                if (!iframe) iframe = arguments[0].querySelector('iframe');
                return iframe || document.querySelector('iframe[src*="turnstile"]');
            ''', container)
            
            if not iframe:
                page.get_screenshot(f'iframe_error_{retry}.png')
                raise ElementNotFoundError("验证框架未找到")
            
            # 切换到iframe
            page.switch_to.frame(iframe)
            
            # 定位并点击验证框
            checkbox = page.wait.ele(
                'css:input[type="checkbox"], css:.mark, css:.checkbox-label', 
                timeout=30
            )
            checkbox.click(by_js=True)  # 使用JS点击更可靠
            
            # 验证成功条件
            success = page.wait.ele(
                'css:.verifybox-success, css:[data-success], css:.success-mark', 
                timeout=25
            )
            
            if success:
                print("✅ 验证成功")
                return True
            
            # 触发页面更新
            page.refresh()
            time.sleep(5)
            
        except ElementNotFoundError as e:
            print(f"⚠️ 元素未找到: {str(e)[:50]}")
            page.get_screenshot(f'error_{retry}.png')
            page.refresh()
            time.sleep(8)
        except Exception as e:
            print(f"❌ 异常错误: {str(e)}")
            if retry == max_retry:
                page.get_screenshot('final_error.png')
                raise

    return False

# ======================
# 主流程（增强稳定性）
# ======================
if __name__ == "__main__":
    browser = None
    try:
        # 带指数退避的重试机制
        retry_delays = [5, 10, 15]
        for attempt in range(3):
            try:
                browser = get_browser(headless=True)
                break
            except BrowserConnectError as e:
                if attempt == 2: 
                    raise
                delay = retry_delays[attempt]
                print(f"🔁 浏览器连接失败，{delay}秒后重试...")
                time.sleep(delay)
        
        target_url = "https://www.serv00.com/offer/create_new_account"
        print(f"🌐 正在访问 {target_url}")
        
        # 带重试的页面加载
        browser.get(target_url, retry=3, interval=5, timeout=60)
        
        if bypass_turnstile(browser):
            print("\n🎉 成功获取Cookies:")
            cookies = browser.cookies(as_dict=True)
            print(json.dumps(cookies, indent=2, ensure_ascii=False))
            
            # 保存Cookies并验证有效性
            with open("cookies.json", 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            
            if browser.title != 'Just a moment...':
                print("✅ 验证流程完整通过")
            else:
                print("⚠️ 验证状态可能异常")
        else:
            print("\n❌ 验证流程失败")
            
    except Exception as e:
        print(f"💥 致命错误: {str(e)}")
    finally:
        if browser:
            # 清理临时文件
            for d in getattr(browser, '_temp_dirs', []):
                shutil.rmtree(d, ignore_errors=True)
            browser.quit()
            print("\n🛑 浏览器已安全关闭")
