import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, BrowserConnectError

# ======================
# 浏览器扩展配置
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "Turnstile Helper",
    "version": "0.3",
    "content_scripts": [{
        "js": ["./script.js"],
        "matches": ["<all_urls>"],
        "run_at": "document_start",
        "all_frames": True,
        "world": "MAIN"
    }]
}

SCRIPT_CONTENT = """
// 增强版反检测脚本
const randomScreen = {
    x: Math.floor(Math.random() * 1200 + 800),
    y: Math.floor(Math.random() * 600 + 400)
};

Object.defineProperties(MouseEvent.prototype, {
    'screenX': { get: () => randomScreen.x },
    'screenY': { get: () => randomScreen.y }
});

// 覆盖WebGL参数
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    const overrides = {
        37445: 'NVIDIA GeForce RTX 3090',
        37446: 'NVIDIA Corporation'
    };
    return overrides[parameter] || getParameter.call(this, parameter);
};
"""

def create_extension():
    """创建临时扩展目录"""
    temp_dir = tempfile.mkdtemp(prefix='cf_ext_')
    with open(os.path.join(temp_dir, 'manifest.json'), 'w') as f:
        json.dump(MANIFEST_CONTENT, f)
    with open(os.path.join(temp_dir, 'script.js'), 'w') as f:
        f.write(SCRIPT_CONTENT)
    return temp_dir

# ======================
# 浏览器配置
# ======================
def get_browser(headless=True):
    """配置浏览器实例"""
    co = ChromiumOptions()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--remote-allow-origins=*')
    
    if headless:
        co.headless()
    
    # 加载扩展
    ext_dir = create_extension()
    co.add_extension(ext_dir)
    
    browser = ChromiumPage(co)
    # 记录临时目录用于清理
    browser._temp_dirs = [ext_dir]
    return browser

# ======================
# 验证码处理逻辑
# ======================
def bypass_turnstile(page, max_retry=3):
    """执行验证码绕过"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n🚀 尝试第 {retry} 次验证")
            
            # 等待验证组件加载
            container = page.wait.ele('.cf-turnstile', timeout=20)
            
            # 处理Shadow DOM
            iframe = container.run_js('return this.shadowRoot.querySelector("iframe")')
            if not iframe:
                raise ElementNotFoundError("验证iframe未找到")
            
            # 切换到iframe
            page.wait.load_frame(iframe)
            
            # 点击复选框
            checkbox = page.wait.ele('input[type="checkbox"]', timeout=10)
            checkbox.click(by_js=True)
            
            # 验证结果
            if page.wait.ele('.verifybox-success', timeout=15):
                print("✅ 验证成功")
                return True
            
        except ElementNotFoundError as e:
            print(f"⚠️ 元素未找到: {str(e)[:80]}")
            page.refresh()
            page.wait.doc_loaded()
            time.sleep(2)
        except BrowserConnectError as e:
            print(f"🔌 浏览器连接错误: {str(e)[:80]}")
            raise
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
            if retry == max_retry:
                raise

    return False

# ======================
# 主流程
# ======================
if __name__ == "__main__":
    browser = None
    try:
        browser = get_browser(headless=True)
        url = "https://www.serv00.com/offer/create_new_account"
        print(f"🌐 正在访问 {url}")
        browser.get(url)
        
        if bypass_turnstile(browser):
            print("\n🎉 成功获取Cookies:")
            cookies = browser.cookies(as_dict=True)
            for k, v in cookies.items():
                print(f"🍪 {k}: {v[:50]}{'...' if len(v)>50 else ''}")
            
            with open("cookies.json", 'w') as f:
                json.dump(cookies, f, indent=2)
        else:
            print("\n😞 验证失败")
            
    except BrowserConnectError as e:
        print(f"💥 浏览器连接失败: {str(e)}")
    except Exception as e:
        print(f"💣 致命错误: {str(e)}")
    finally:
        if browser:
            # 清理临时目录
            for d in getattr(browser, '_temp_dirs', []):
                shutil.rmtree(d, ignore_errors=True)
            browser.quit()
            print("\n🛑 浏览器已关闭")
