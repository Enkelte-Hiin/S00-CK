import os
import tempfile
import json
import shutil
import time
from DrissionPage import Chromium, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, PageDisconnectedError

# ======================
# 浏览器扩展配置
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "Turnstile Helper",
    "version": "0.2",
    "content_scripts": [{
        "js": ["./script.js"],
        "matches": ["<all_urls>"],
        "run_at": "document_start",
        "all_frames": True,
        "world": "MAIN"
    }]
}

SCRIPT_CONTENT = """
// 伪造随机屏幕坐标
const randomScreen = {
    x: Math.floor(Math.random() * 1200 + 800),
    y: Math.floor(Math.random() * 600 + 400)
};

Object.defineProperties(MouseEvent.prototype, {
    'screenX': { get: () => randomScreen.x },
    'screenY': { get: () => randomScreen.y }
});

// 覆盖WebGL渲染器参数
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) { // UNMASKED_RENDERER_WEBGL
        return 'NVIDIA GeForce RTX 3090 OpenGL Engine';
    }
    return getParameter.call(this, parameter);
};
"""

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
# 浏览器配置
# ======================
def get_configured_browser(headless=True) -> Chromium:
    """配置带反检测扩展的浏览器实例"""
    options = ChromiumOptions().auto_port()
    options.set_argument("--no-sandbox")
    options.set_argument("--disable-dev-shm-usage")
    options.set_argument("--window-size=1600,900")
    options.set_argument("--disable-blink-features=AutomationControlled")
    
    if headless:
        options.headless(True).set_argument("--headless=new")
    
    # 加载扩展
    ext_path = create_extension()
    options.add_extension(ext_path)
    
    browser = Chromium(options)
    # 标记扩展目录以便后续清理
    browser._attached_extensions = [ext_path]  
    return browser

# ======================
# 验证码处理核心逻辑
# ======================
def handle_turnstile(tab, max_attempts=3) -> bool:
    """处理Turnstile验证码的完整流程"""
    for attempt in range(1, max_attempts+1):
        try:
            print(f"\n=== 第 {attempt} 次尝试 ===")
            
            # 显式等待验证组件容器
            tab.wait.ele_loaded('css:[data-sitekey]', timeout=20)
            
            # 定位外层容器
            wrapper = tab.ele('css:.cf-turnstile', timeout=15)
            if not wrapper.exists:
                raise ElementNotFoundError("Turnstile容器未找到")
            
            # 穿透Shadow DOM定位iframe
            iframe = wrapper.shadow_root.ele('tag:iframe', timeout=15)
            if not iframe.exists:
                raise ElementNotFoundError("iframe未找到")
            
            # 切换到iframe内部
            iframe_doc = iframe.inner_frame
            iframe_doc.wait.doc_loaded()
            
            # 定位并点击验证复选框
            checkbox = iframe_doc.ele('css:input[type="checkbox"]', timeout=15)
            if checkbox.exists:
                print("触发验证复选框点击...")
                checkbox.click()
                
                # 等待验证成功标志
                success = iframe_doc.wait.ele(
                    'css:.verifybox-success', 
                    timeout=15, 
                    display=True
                )
                if success:
                    print("√ 验证成功")
                    return True
                
            raise RuntimeError("验证流程未完成")
            
        except (ElementNotFoundError, PageDisconnectedError) as e:
            print(f"! 遇到错误: {str(e)[:80]}")
            if attempt < max_attempts:
                print("刷新页面并重试...")
                tab.refresh()
                time.sleep(3)
            else:
                raise
        except Exception as e:
            print(f"! 未知错误: {str(e)[:80]}")
            raise

    return False

# ======================
# 主执行流程
# ======================
if __name__ == "__main__":
    browser = None
    try:
        # 初始化浏览器
        browser = get_configured_browser(headless=True)
        tab = browser.get_tab()
        
        # 访问目标页面
        target_url = "https://www.serv00.com/offer/create_new_account"
        print(f"访问目标页面: {target_url}")
        tab.get(target_url)
        tab.wait.doc_loaded()
        
        # 执行验证流程
        if handle_turnstile(tab):
            print("\n=== 验证结果 ===")
            print("成功绕过Turnstile验证")
            
            # 获取并输出cookies
            cookies = tab.get_cookies(as_dict=True)
            print("\n获取到的Cookies:")
            for k, v in cookies.items():
                print(f"{k}: {v[:50]}{'...' if len(v)>50 else ''}")
            
            # 示例：保存cookies到文件
            with open("cookies.json", 'w') as f:
                json.dump(cookies, f, indent=2)
        else:
            print("验证失败，请检查网络或验证码配置")

    except Exception as e:
        print(f"\n!!! 主流程错误: {str(e)}")
        
    finally:
        if browser:
            # 清理临时扩展目录
            for ext_dir in getattr(browser, '_attached_extensions', []):
                if os.path.exists(ext_dir):
                    shutil.rmtree(ext_dir, ignore_errors=True)
            # 关闭浏览器
            browser.quit()
            print("\n浏览器已安全关闭")
