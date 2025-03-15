import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, BrowserConnectError

# ======================
# 扩展配置（增强反检测）
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "CF Bypass Helper",
    "version": "2.0",
    "content_scripts": [{
        "js": ["content.js"],
        "matches": ["<all_urls>"],
        "run_at": "document_start",
        "all_frames": True,
        "world": "MAIN"
    }]
}

SCRIPT_CONTENT = """
// 增强浏览器指纹保护
const randomRange = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const screenX = randomRange(800, 2000);
const screenY = randomRange(400, 1200);

// 覆盖鼠标参数
Object.defineProperties(MouseEvent.prototype, {
    'screenX': { get: () => screenX },
    'screenY': { get: () => screenY }
});

// 修改WebGL参数
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    const overrides = {
        37445: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0)',
        37446: 'NVIDIA Corporation'
    };
    return overrides[parameter] || getParameter.call(this, parameter);
};

// 修改Canvas指纹
const toBlob = HTMLCanvasElement.prototype.toBlob;
HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
    const canvas = document.createElement('canvas');
    canvas.width = this.width;
    canvas.height = this.height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(this, 0, 0);
    return toBlob.call(canvas, callback, type, quality);
};
"""

# ======================
# 浏览器初始化配置
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
    
    # 重要：设置用户代理和窗口尺寸
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    co.set_argument('--window-size=1920,1080')
    
    if headless:
        co.headless()
    
    # 加载扩展
    ext_dir = create_extension()
    co.add_extension(ext_dir)
    
    try:
        browser = ChromiumPage(addr_or_opts=co, timeout=60)
        browser._temp_dirs = [ext_dir]
        
        # 隐藏自动化特征
        browser.set.cookie('', '')  # 触发driver初始化
        driver = browser.driver
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            '''
        })
        return browser
    except Exception as e:
        shutil.rmtree(ext_dir, ignore_errors=True)
        raise

# ======================
# 验证码处理核心逻辑
# ======================
def bypass_turnstile(page, max_retry=3):
    """验证码处理流程"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n🔄 第 {retry} 次尝试")
            page.wait.load_start()
            
            # 等待核心元素加载（多种定位方式）
            container = page.wait.ele(
                'css:.cf-turnstile, css:[data-sitekey], css:iframe[src*="challenges.cloudflare.com"]', 
                timeout=30
            )
            
            # 处理Shadow DOM和iframe
            iframe = container.run_js('''
                function findCFIframe(element) {
                    return element.shadowRoot?.querySelector('iframe') 
                        || element.querySelector('iframe')
                        || (element.tagName === 'IFRAME' ? element : null);
                }
                return findCFIframe(arguments[0]);
            ''', container)
            
            if not iframe:
                page.get_screenshot(f'iframe_error_{retry}.png')
                raise ElementNotFoundError("验证框架未找到")
            
            # 切换到iframe并点击
            page.switch_to.frame(iframe)
            checkbox = page.wait.ele('''
                css:input[type="checkbox"], 
                css:.checkbox-label, 
                xpath://span[contains(@class, 'mark')]
            ''', timeout=25)
            
            # 使用动作链模拟人类点击
            page.actions.move_to(checkbox).click().perform()
            
            # 多维度验证成功状态
            success = any([
                page.wait.ele('.verifybox-success', timeout=20),
                page.wait.ele_text_contains('验证成功', timeout=15),
                page.wait.ele_text_contains('success', timeout=15),
                page.wait.ele('css:[data-success]', timeout=15)
            ])
            
            if success:
                print("✅ 验证成功")
                return True
            
            # 触发重新验证
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
# 主执行流程
# ======================
if __name__ == "__main__":
    browser = None
    try:
        # 初始化浏览器（带重试机制）
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
        
        # 页面加载配置
        browser.get(target_url, retry=3, interval=3, timeout=60)
        browser.wait.load_start()
        
        if bypass_turnstile(browser):
            print("\n🎉 成功获取Cookies:")
            cookies = browser.cookies(as_dict=True)
            print(json.dumps(cookies, indent=2, ensure_ascii=False))
            
            # 保存Cookies
            with open("cookies.json", 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            
            # 验证后续访问
            if browser.ele('css:#username', timeout=10):
                print("✅ 已成功进入注册页面")
            else:
                print("⚠️ 验证成功但页面跳转异常")
        else:
            print("\n❌ 验证失败")
            
    except Exception as e:
        print(f"💥 致命错误: {str(e)}")
    finally:
        if browser:
            # 清理临时文件
            for d in getattr(browser, '_temp_dirs', []):
                shutil.rmtree(d, ignore_errors=True)
            browser.quit()
            print("\n🛑 浏览器已安全关闭")
