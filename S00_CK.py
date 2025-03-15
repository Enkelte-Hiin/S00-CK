import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, BrowserConnectError

# ======================
# 新增扩展配置常量定义
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "Turnstile Helper Pro",
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
// 增强版反检测脚本
const getParams = () => {
    const randX = Math.floor(Math.random() * 1200 + 800);
    const randY = Math.floor(Math.random() * 600 + 400);
    const renderer = 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3090 Direct3D11 vs_5_0 ps_5_0)';
    
    // 覆盖鼠标坐标
    Object.defineProperties(MouseEvent.prototype, {
        'screenX': { get: () => randX },
        'screenY': { get: () => randY }
    });
    
    // 覆盖WebGL参数
    const origGetParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        switch(param) {
            case 37445: return renderer;
            case 37446: return 'NVIDIA Corporation';
            default: return origGetParameter.call(this, param);
        }
    };
};

document.addEventListener('DOMContentLoaded', getParams, { once: true });
"""

# ======================
# 浏览器扩展创建函数
# ======================
def create_extension():
    """创建临时扩展目录"""
    temp_dir = tempfile.mkdtemp(prefix='cf_ext_')
    manifest_path = os.path.join(temp_dir, 'manifest.json')
    script_path = os.path.join(temp_dir, 'content.js')  # 修正文件名
    
    with open(manifest_path, 'w') as f:
        json.dump(MANIFEST_CONTENT, f, indent=2)
    
    with open(script_path, 'w') as f:
        f.write(SCRIPT_CONTENT.strip())
    
    return temp_dir

# ======================
# 浏览器配置（修复路径问题）
# ======================
def get_browser(headless=True):
    """配置浏览器实例"""
    co = ChromiumOptions()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')  # 新增GPU兼容参数
    co.set_argument('--remote-allow-origins=*')
    
    # GitHub Actions专用路径配置
    co.set_browser_path('/usr/bin/chromium-browser')
    co.set_local_port(9222)  # 固定调试端口
    
    if headless:
        co.headless()
    
    # 加载扩展
    ext_dir = create_extension()
    co.add_extension(ext_dir)
    
    try:
        browser = ChromiumPage(addr_driver_opts=co, timeout=30)  # 延长超时时间
        browser._temp_dirs = [ext_dir]
        return browser
    except Exception as e:
        shutil.rmtree(ext_dir, ignore_errors=True)
        raise

# ======================
# 增强版验证码处理逻辑
# ======================
def bypass_turnstile(page, max_retry=3):
    """执行验证码绕过"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n🚀 尝试第 {retry} 次验证")
            
            # 等待核心元素加载
            page.wait.ele('.cf-turnstile', timeout=30)
            
            # 执行Shadow DOM查询
            iframe = page.run_js('''
                const wrapper = document.querySelector('.cf-turnstile');
                return wrapper?.shadowRoot?.querySelector('iframe');
            ''')
            
            if not iframe:
                raise ElementNotFoundError("验证iframe未找到")
            
            # 切换到iframe
            page.frame_to(iframe)
            
            # 使用混合选择器
            checkbox = page.wait.ele('xpath://input[@type="checkbox"] | css:input[type="checkbox"]', timeout=20)
            checkbox.click(by_js=True)
            
            # 双重验证机制
            success1 = page.wait.ele('.verifybox-success', timeout=20)
            success2 = page.wait.ele_text_contains('验证成功', timeout=15)
            
            if success1 or success2:
                print("✅ 验证成功")
                return True
            
            raise ElementNotFoundError("未检测到成功标识")

        except ElementNotFoundError as e:
            print(f"⚠️ 元素错误: {str(e)[:80]}")
            page.refresh()
            page.wait.load_start()
            time.sleep(3)
        except Exception as e:
            print(f"❌ 尝试失败: {str(e)}")
            if retry == max_retry:
                page.get_screenshot(f'error_{time.time()}.png')
                raise

    return False

# ======================
# 主流程（新增重试机制）
# ======================
if __name__ == "__main__":
    browser = None
    try:
        # 初始化浏览器（带重试）
        for i in range(3):
            try:
                browser = get_browser(headless=True)
                break
            except BrowserConnectError:
                if i == 2: raise
                print("🔄 浏览器连接失败，重试中...")
                time.sleep(5)
        
        url = "https://www.serv00.com/offer/create_new_account"
        print(f"🌐 正在访问 {url}")
        browser.get(url, retry=3, interval=3, timeout=40)
        
        if bypass_turnstile(browser):
            print("\n🎉 成功获取Cookies:")
            cookies = browser.cookies(as_dict=True)
            print(json.dumps(cookies, indent=2))
            
            with open("cookies.json", 'w') as f:
                json.dumps(cookies, f, ensure_ascii=False, indent=2)
        else:
            print("\n😞 验证失败")
            
    except BrowserConnectError as e:
        print(f"💥 连接错误: {str(e)}")
    except Exception as e:
        print(f"💣 致命错误: {str(e)}")
    finally:
        if browser:
            # 清理资源
            for d in getattr(browser, '_temp_dirs', []):
                shutil.rmtree(d, ignore_errors=True)
            browser.quit()
            print("\n🛑 浏览器已安全关闭")
