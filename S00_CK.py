import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, BrowserConnectError

# ======================
# 浏览器扩展配置（保持相同）
# ======================

def create_extension():
    """创建临时扩展目录"""
    temp_dir = tempfile.mkdtemp(prefix='cf_ext_')
    with open(os.path.join(temp_dir, 'manifest.json'), 'w') as f:
        json.dump(MANIFEST_CONTENT, f)
    with open(os.path.join(temp_dir, 'script.js'), 'w') as f:
        f.write(SCRIPT_CONTENT)
    return temp_dir

# ======================
# 修复后的浏览器配置
# ======================
def get_browser(headless=True):
    """配置浏览器实例"""
    co = ChromiumOptions()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--remote-allow-origins=*')
    
    # 显式设置浏览器路径（GitHub Actions 专用）
    co.set_browser_path('/usr/bin/chromium-browser')
    
    if headless:
        co.headless()
    
    # 加载扩展
    ext_dir = create_extension()
    co.add_extension(ext_dir)
    
    browser = ChromiumPage(addr_driver_opts=co)  # 使用新式初始化方法
    browser._temp_dirs = [ext_dir]
    return browser

# ======================
# 修复后的验证码处理逻辑
# ======================
def bypass_turnstile(page, max_retry=3):
    """执行验证码绕过"""
    for retry in range(1, max_retry+1):
        try:
            print(f"\n🚀 尝试第 {retry} 次验证")
            
            # 使用新版元素等待API
            container = page.wait.ele('.cf-turnstile', timeout=20)
            
            # 处理Shadow DOM
            iframe = container.run_js('return this.shadowRoot.querySelector("iframe")')
            if not iframe:
                raise ElementNotFoundError("验证iframe未找到")
            
            # 切换到iframe
            page.frame_to(iframe)
            
            # 使用更可靠的选择器
            checkbox = page.wait.ele('xpath://input[@type="checkbox"]', timeout=15)
            checkbox.click(by_js=True)
            
            # 等待验证结果
            if page.wait.ele('.verifybox-success', timeout=20):
                print("✅ 验证成功")
                return True
            
            # 添加备用验证方式
            if page.wait.ele_text_contains('验证成功', timeout=10):
                print("✅ 备用验证成功")
                return True
            
        except ElementNotFoundError as e:
            print(f"⚠️ 元素未找到: {str(e)[:80]}")
            page.refresh()
            page.wait.load_start()
            time.sleep(3)
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
            if retry == max_retry:
                page.get_screenshot(f'error_{int(time.time())}.png')
                raise

    return False

# ======================
# 主流程（增加页面加载检测）
# ======================
if __name__ == "__main__":
    browser = None
    try:
        browser = get_browser(headless=True)
        url = "https://www.serv00.com/offer/create_new_account"
        print(f"🌐 正在访问 {url}")
        
        # 使用新版页面加载检测
        browser.get(url, retry=3, interval=2, timeout=30)
        browser.wait.load_start()
        
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
