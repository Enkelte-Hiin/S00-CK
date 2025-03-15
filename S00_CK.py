import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, BrowserConnectError

# ======================
# 扩展配置（保持最新）
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "Turnstile Expert",
    "version": "1.2",
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
const overrideParams = () => {
    const randomize = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
    
    // 鼠标轨迹参数
    Object.defineProperties(MouseEvent.prototype, {
        'screenX': { get: () => randomize(800, 2000) },
        'screenY': { get: () => randomize(400, 1200) }
    });

    // WebGL渲染器伪装
    const origGetParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        const overrides = {
            37445: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4090)',
            37446: 'NVIDIA Corporation',
            7937: 'WebKit'
        };
        return overrides[param] || origGetParameter.call(this, param);
    };
};

// 更早执行覆盖
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', overrideParams);
} else {
    overrideParams();
}
"""

# ======================
# 修复浏览器初始化
# ======================
def get_browser(headless=True):
    """配置浏览器实例（使用最新API）"""
    co = ChromiumOptions()
    
    # 必须参数
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--remote-allow-origins=*')
    co.set_argument('--disable-blink-features=AutomationControlled')
    
    # GitHub Actions专用配置
    co.set_browser_path('/usr/bin/chromium')
    co.set_local_port(9222)
    
    if headless:
        co.headless()
    
    # 创建并加载扩展
    ext_dir = create_extension()
    co.add_extension(ext_dir)
    
    try:
        # 修正初始化参数名
        browser = ChromiumPage(addr_or_opts=co, timeout=40)
        browser._temp_dirs = [ext_dir]
        return browser
    except Exception as e:
        shutil.rmtree(ext_dir, ignore_errors=True)
        raise

# ======================
# 更新元素定位逻辑
# ======================
def bypass_turnstile(page, max_retry=3):
    """验证码处理流程（兼容新版API）"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n🔄 第 {retry} 次尝试 (v2.1)")
            
            # 使用智能等待
            container = page.wait.ele('.cf-turnstile, [data-sitekey]', timeout=30)
            
            # 执行JavaScript穿透Shadow DOM
            iframe = container.run_js('''
                return this.shadowRoot?.querySelector('iframe') 
                    || this.querySelector('iframe');
            ''')
            
            if not iframe:
                page.get_screenshot(f'iframe_error_{retry}.png')
                raise ElementNotFoundError("验证框架未找到")
            
            # 切换到iframe
            page.frame_to(iframe)
            
            # 使用复合选择器定位复选框
            checkbox = page.wait.ele('''
                xpath://input[@type="checkbox"] | 
                css:input[type="checkbox"],
                css:.checkbox-label
            ''', timeout=25)
            
            # 使用动作链点击
            page.actions.click(checkbox)
            
            # 多条件验证
            success = any([
                page.wait.ele('.verifybox-success', timeout=20),
                page.wait.ele_text_contains('成功', timeout=15),
                page.wait.ele_text_contains('verified', timeout=15)
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
            time.sleep(3)
        except Exception as e:
            print(f"❌ 意外错误: {str(e)}")
            if retry == max_retry:
                page.get_screenshot('final_error.png')
                raise

    return False

# ======================
# 主流程（优化重试机制）
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
                time.sleep(5)
        
        target_url = "https://www.serv00.com/offer/create_new_account"
        print(f"🌍 访问目标: {target_url}")
        
        # 强化页面加载
        browser.get(target_url, retry=3, interval=2, timeout=60)
        browser.wait.eles_loaded('body, .cf-turnstile, [data-sitekey]', timeout=40)
        
        if bypass_turnstile(browser):
            print("\n🎯 成功获取凭证:")
            cookies = browser.cookies(as_dict=True)
            print(json.dumps(cookies, indent=2, ensure_ascii=False))
            
            with open("cookies.json", 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
        else:
            print("\n⛔ 验证失败")
            
    except BrowserConnectError as e:
        print(f"🔥 连接异常: {str(e)}")
    except Exception as e:
        print(f"💥 崩溃错误: {str(e)}")
    finally:
        if browser:
            # 资源清理
            for d in getattr(browser, '_temp_dirs', []):
                shutil.rmtree(d, ignore_errors=True)
            browser.quit()
            print("\n🛑 浏览器终止")
