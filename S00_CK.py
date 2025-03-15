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
    "version": "1.4",
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
    
    # 写入manifest文件
    with open(os.path.join(temp_dir, 'manifest.json'), 'w') as f:
        json.dump(MANIFEST_CONTENT, f, indent=2)
    
    # 写入脚本文件
    with open(os.path.join(temp_dir, 'content.js'), 'w') as f:
        f.write(SCRIPT_CONTENT.strip())
    
    return temp_dir

def get_browser(headless=True):
    """配置浏览器实例"""
    co = ChromiumOptions()
    
    # 核心参数
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--remote-allow-origins=*')
    
    # GitHub Actions专用配置
    co.set_browser_path('/usr/bin/chromium-browser')
    co.set_local_port(9222)
    
    if headless:
        co.headless()
    
    # 加载扩展
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
# 验证码处理（使用最新元素定位API）
# ======================
def bypass_turnstile(page, max_retry=3):
    """验证码处理流程"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n🔄 第 {retry} 次尝试 (v4.3)")
            
            # 使用新版等待API
            container = page.wait.ele('css:.cf-turnstile, css:[data-sitekey]', timeout=40)
            
            # 执行JavaScript穿透Shadow DOM
            iframe = container.run_js('''
                return this.shadowRoot?.querySelector('iframe') 
                    || this.querySelector('iframe');
            ''')
            
            if not iframe:
                page.get_screenshot(f'iframe_error_{retry}.png')
                raise ElementNotFoundError("验证框架未找到")
            
            # 切换到iframe（新版API）
            page.switch_to.frame(iframe)
            
            # 使用显式等待定位元素
            checkbox = page.wait.available('css:input[type="checkbox"], css:.checkbox-label', timeout=30)
            
            # 使用动作链点击
            page.actions.click(checkbox)
            
            # 多条件验证
            success = any([
                page.wait.ele('.verifybox-success', timeout=25),
                page.wait.text_contains('成功', timeout=15),
                page.wait.text_contains('verified', timeout=15)
            ])
            
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
# 主流程（优化元素等待）
# ======================
if __name__ == "__main__":
    browser = None
    try:
        # 带重试的浏览器初始化
        for i in range(3):
            try:
                browser = get_browser(headless=True)
                break
            except BrowserConnectError:
                if i == 2: raise
                print("🔁 浏览器连接重试...")
                time.sleep(10)
        
        target_url = "https://www.serv00.com/offer/create_new_account"
        print(f"🌍 访问目标: {target_url}")
        
        # 强化页面加载
        browser.get(target_url, retry=3, interval=2, timeout=60)
        browser.wait.load_start()
        
        if bypass_turnstile(browser):
            print("\n🎯 成功获取凭证:")
            cookies = browser.cookies(as_dict=True)
            print(json.dumps(cookies, indent=2, ensure_ascii=False))
            
            with open("cookies.json", 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
        else:
            print("\n⛔ 验证失败")
            
    except Exception as e:
        print(f"💥 崩溃错误: {str(e)}")
    finally:
        if browser:
            # 资源清理
            for d in getattr(browser, '_temp_dirs', []):
                shutil.rmtree(d, ignore_errors=True)
            browser.quit()
            print("\n🛑 浏览器终止")
