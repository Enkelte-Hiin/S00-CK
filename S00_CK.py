import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, BrowserConnectError

# ======================
# 扩展配置
# ======================
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "Turnstile Expert",
    "version": "1.3",
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
    const random = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
    
    // 伪造屏幕参数
    Object.defineProperties(MouseEvent.prototype, {
        'screenX': { get: () => random(800, 2000) },
        'screenY': { get: () => random(400, 1200) }
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
# 新增关键函数定义
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

# ======================
# 浏览器初始化（修复路径问题）
# ======================
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
    ext_dir = create_extension()  # 调用修复后的函数
    co.add_extension(ext_dir)
    
    try:
        browser = ChromiumPage(addr_or_opts=co, timeout=60)
        browser._temp_dirs = [ext_dir]
        return browser
    except Exception as e:
        shutil.rmtree(ext_dir, ignore_errors=True)
        raise

# ======================
# 验证码处理逻辑（保持最新）
# ======================
def bypass_turnstile(page, max_retry=3):
    """验证码处理流程"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n🔄 尝试第 {retry} 次")
            
            # 等待核心元素
            container = page.wait.ele('.cf-turnstile, [data-sitekey]', timeout=40)
            
            # 穿透Shadow DOM
            iframe = container.run_js('''
                return this.shadowRoot?.querySelector('iframe') 
                    || this.querySelector('iframe');
            ''')
            
            if not iframe:
                raise ElementNotFoundError("验证框架未找到")
            
            # 切换iframe
            page.frame_to(iframe)
            
            # 点击复选框
            checkbox = page.wait.ele('''
                xpath://input[@type="checkbox"] | 
                css:input[type="checkbox"],
                css:.checkbox-label
            ''', timeout=30)
            checkbox.click(by_js=True)
            
            # 验证结果
            if page.wait.ele('.verifybox-success', timeout=25):
                print("✅ 验证成功")
                return True
            
            # 备用验证
            if '验证成功' in page.html:
                print("✅ 备用验证通过")
                return True
            
        except ElementNotFoundError as e:
            print(f"⚠️ 错误: {str(e)[:50]}")
            page.refresh()
            time.sleep(5)
        except Exception as e:
            print(f"❌ 异常: {str(e)}")
            if retry == max_retry:
                page.get_screenshot('final_error.png')
                raise

    return False

# ======================
# 主流程
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
                print("🔄 浏览器重连中...")
                time.sleep(10)
        
        print("🌐 访问目标页面...")
        browser.get('https://www.serv00.com/offer/create_new_account', retry=3, timeout=60)
        
        if bypass_turnstile(browser):
            print("\n🎉 成功获取Cookies:")
            cookies = browser.cookies(as_dict=True)
            print(json.dumps(cookies, indent=2, ensure_ascii=False))
            
            with open("cookies.json", 'w') as f:
                json.dump(cookies, f, indent=2)
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
