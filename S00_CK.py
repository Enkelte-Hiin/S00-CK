import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError

# ======================
# 扩展配置（增强反检测）
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "Turnstile Expert",
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
// 强化浏览器指纹保护
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
const getRandom = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;

// 覆盖鼠标参数
Object.defineProperties(MouseEvent.prototype, {
    'screenX': { value: getRandom(800, 2000) },
    'screenY': { value: getRandom(400, 1200) }
});

// 修改WebGL渲染器
const origGetParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    const overrides = {
        37445: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0)',
        37446: 'NVIDIA Corporation'
    };
    return overrides[param] || origGetParameter.call(this, param);
};
"""

# ======================
# 浏览器初始化
# ======================
def create_extension():
    """创建临时扩展目录"""
    temp_dir = tempfile.mkdtemp(prefix='cf_ext_')
    with open(os.path.join(temp_dir, 'manifest.json'), 'w') as f:
        json.dump(MANIFEST_CONTENT, f, indent=2)
    with open(os.path.join(temp_dir, 'content.js'), 'w') as f:
        f.write(SCRIPT_CONTENT.strip())
    return temp_dir

def get_patched_browser(headless=True):
    """配置浏览器实例"""
    co = ChromiumOptions()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-blink-features=AutomationControlled')
    
    # 设置真实用户代理
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    co.set_argument(f'--user-agent={user_agent}')
    
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
# 验证码处理核心逻辑
# ======================
def click_turnstile_checkbox(page, max_retry=3):
    """执行验证流程"""
    for retry in range(1, max_retry + 1):
        try:
            print(f"\n🔄 第 {retry} 次尝试")
            
            # 等待核心元素加载（使用 wait_for_selector）
            container = page.wait_for_selector(
                'css:div[data-sitekey], css:.cf-turnstile, css:iframe[src*="challenges.cloudflare.com"]',
                timeout=40
            )
            if not container:
                raise ElementNotFoundError("未找到验证码容器")
            
            # 穿透Shadow DOM查找iframe
            iframe = container.run_js('''
                function findIframe(element) {
                    return element.shadowRoot?.querySelector('iframe') 
                        || element.querySelector('iframe')
                        || document.querySelector('iframe[src*="turnstile"]');
                }
                return findIframe(arguments[0]);
            ''', container)
            
            if not iframe:
                page.get_screenshot(f'iframe_error_{retry}.png')
                raise ElementNotFoundError("验证框架未找到")

            # 切换到iframe上下文
            page.switch_to.frame(iframe)
            
            # 定位并点击验证框
            checkbox = page.wait_for_selector(
                'css:input[type="checkbox"], css:.checkbox-label, css:.mark',
                timeout=30
            )
            if checkbox:
                checkbox.click(by_js=True)  # 使用JS点击更可靠
            else:
                raise ElementNotFoundError("未找到复选框")
            
            # 多维度验证结果
            success = any([
                page.ele('.verifybox-success', timeout=20, raise_err=False),
                page.ele('text=验证成功', timeout=15, raise_err=False),
                page.ele('text=success', timeout=15, raise_err=False)
            ])
            
            if success:
                print("✅ 验证成功")
                return True
            else:
                print("⚠️ 未检测到成功标志，刷新重试")
                page.refresh()
                time.sleep(5)
            
        except ElementNotFoundError as e:
            print(f"⚠️ 元素未找到: {str(e)}")
            page.get_screenshot(f'error_{retry}.png')
            page.refresh()
            time.sleep(8)
        except Exception as e:
            print(f"❌ 发生异常: {str(e)}")
            if retry == max_retry:
                page.get_screenshot('final_error.png')
                raise

    print("❌ 所有尝试均失败")
    return False

# ======================
# 主流程
# ======================
if __name__ == "__main__":
    browser = None
    try:
        browser = get_patched_browser(headless=True)
        target_url = "https://www.serv00.com/offer/create_new_account"
        print(f"🌐 正在访问 {target_url}")
        
        # 带重试的页面加载
        browser.get(target_url, retry=3, interval=5, timeout=60)
        browser.wait.load_start()
        
        if click_turnstile_checkbox(browser):
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
            # 清理临时文件
            for d in getattr(browser, '_temp_dirs', []):
                shutil.rmtree(d, ignore_errors=True)
            browser.quit()
            print("\n🛑 浏览器已安全关闭")
