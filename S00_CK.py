import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, BrowserConnectError

# ======================
# 扩展配置（最新语法）
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "Turnstile Expert",
    "version": "1.5",
    "content_scripts": [{
        "js": ["content.js"],
        "matches": ["<all_urls>"],
        "run_at": "document_start",
        "all_frames": True,
        "world": "MAIN"
    }]
}

SCRIPT_CONTENT = """
// 强化反检测逻辑
(() => {
    const rand = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
    
    // 覆盖鼠标参数
    Object.defineProperties(MouseEvent.prototype, {
        'screenX': { get: () => rand(800, 2000) },
        'screenY': { get: () => rand(400, 1200) }
    });

    // 覆盖WebGL参数
    const origGetParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        const overrides = {
            37445: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4090)',
            37446: 'NVIDIA Corporation',
            7937: 'WebKit'
        };
        return overrides[param] || origGetParameter.call(this, param);
    };
})();
"""

# ======================
# 浏览器初始化（兼容新版API）
# ======================
def create_extension():
    """创建浏览器扩展临时目录"""
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
    co.set_argument('--disable-gpu')
    co.set_argument('--remote-allow-origins=*')
    co.set_browser_path('/usr/bin/chromium-browser')
    
    if headless:
        co.headless()
    
    ext_dir = create_extension()
    co.add_extension(ext_dir)
    
    try:
        browser = ChromiumPage(addr_or_opts=co, timeout=60)
        browser._temp_dirs = [ext_dir]
        return browser
    except Exception as e:
        shutil.rmtree(ext_dir, ignore_errors=True)
        raise

# ======================
# 验证码处理（适配最新API）
# ======================
def bypass_turnstile(page, max_retry=3):
    """验证码处理流程"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n🔄 第 {retry} 次尝试 (v4.3.1)")
            
            # 新版元素定位API
            container = page.ele('.cf-turnstile, [data-sitekey]', timeout=40)
            
            # 处理Shadow DOM
            iframe = container.run_js('''
                return this.shadowRoot?.querySelector('iframe') 
                    || this.querySelector('iframe');
            ''')
            
            if not iframe:
                page.get_screenshot(f'iframe_error_{retry}.png')
                raise ElementNotFoundError("验证框架未找到")
            
            # 切换到iframe
            page.switch_to.frame(iframe)
            
            # 显式等待元素可点击
            checkbox = page.ele('input[type="checkbox"], .checkbox-label', timeout=30)
            checkbox.click()
            
            # 验证结果（使用新版文本检测API）
            success = page.wait.ele('.verifybox-success', timeout=25) \
                     or page.wait.ele_contains_text('成功|verified', timeout=15)
            
            if success:
                print("✅ 验证状态确认")
                return True
            
            # 触发重新验证
            page.run_js('window.__cfChallengeRan = false;')
            
        except ElementNotFoundError as e:
            print(f"⚠️ 定位失败: {str(e)[:60]}")
            page.refresh()
            page.wait.load_start()
            time.sleep(5)
        except Exception as e:
            print(f"❌ 意外错误: {str(e)}")
            if retry == max_retry:
                page.get_screenshot('final_error.png')
                raise

    return False

# ======================
# 主流程（优化元素定位）
# ======================
if __name__ == "__main__":
    browser = None
    try:
        # 浏览器初始化（带重试）
        for _ in range(3):
            try:
                browser = get_browser(headless=True)
                break
            except BrowserConnectError:
                if _ == 2: raise
                print("🔁 浏览器重连中...")
                time.sleep(10)
        
        print("🌐 访问目标页面...")
        browser.get('https://www.serv00.com/offer/create_new_account', retry=3, timeout=60)
        
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
            # 清理资源
            for d in getattr(browser, '_temp_dirs', []):
                shutil.rmtree(d, ignore_errors=True)
            browser.quit()
            print("\n🛑 浏览器已关闭")
