import os
import tempfile
import json
import shutil
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, SessionClosedError

# ======================
# 浏览器扩展配置（保持不变）
# ======================

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
# 更新后的浏览器配置
# ======================
def get_configured_browser(headless=True) -> ChromiumPage:
    """配置带反检测扩展的浏览器实例"""
    co = ChromiumOptions()
    co.set_browser_path('/usr/bin/chromium-browser')  # 显式指定路径
    co.auto_port(True)
    co.no_imgs(True)
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-dev-shm-usage")
    co.set_argument("--remote-allow-origins=*")
    
    if headless:
        co.headless()
    
    # 加载扩展
    ext_path = create_extension()
    co.add_extension(ext_path)
    
    browser = ChromiumPage(co)
    browser._ext_tmp_dirs = [ext_path]
    return browser

# ======================
# 验证码处理逻辑（使用最新API）
# ======================
def handle_turnstile(page: ChromiumPage, max_attempts=3) -> bool:
    """处理Turnstile验证码的完整流程"""
    for attempt in range(1, max_attempts+1):
        try:
            print(f"\n=== 第 {attempt} 次尝试 ===")
            
            # 使用新版等待API
            cf_wrapper = page.wait.ele('.cf-turnstile', timeout=15)
            if not cf_wrapper:
                raise ElementNotFoundError("未找到验证组件容器")
            
            # 处理Shadow DOM
            iframe = cf_wrapper.run_js('return this.shadowRoot.querySelector("iframe")')
            if not iframe:
                raise ElementNotFoundError("未找到验证iframe")
            
            # 切换到iframe
            page.wait.load_frame(iframe)
            
            # 定位并点击复选框
            checkbox = page.wait.ele('input[type="checkbox"]', timeout=10)
            checkbox.click(by_js=True)
            
            # 验证成功检测
            return page.wait.ele('.verifybox-success', timeout=15) is not None
            
        except (ElementNotFoundError, SessionClosedError) as e:
            print(f"! 错误: {str(e)[:80]}")
            if attempt < max_attempts:
                print("正在刷新页面...")
                page.refresh()
                page.wait.doc_loaded()
                time.sleep(2)
            else:
                raise
        except Exception as e:
            print(f"! 严重错误: {str(e)}")
            raise

    return False

# ======================
# 主执行流程
# ======================
if __name__ == "__main__":
    browser = None
    try:
        browser = get_configured_browser(headless=True)
        print("浏览器初始化完成")
        
        target_url = "https://www.serv00.com/offer/create_new_account"
        print(f"正在访问: {target_url}")
        browser.get(target_url)
        browser.wait.doc_loaded()
        
        if handle_turnstile(browser):
            print("\n=== 成功 ===")
            print("验证码绕过成功")
            
            # 获取cookies
            cookies = browser.cookies(as_dict=True)
            print("\n获取到的Cookies:")
            for k, v in cookies.items():
                print(f"{k}: {v[:50]}{'...' if len(v)>50 else ''}")
            
            with open("cookies.json", 'w') as f:
                json.dump(cookies, f, indent=2)
        else:
            print("\n=== 失败 ===")
            print("验证码绕过失败")

    except Exception as e:
        print(f"\n!!! 主流程错误: {str(e)}")
        if browser:
            browser.get_screenshot(path='error.png')
            print("错误截图已保存到 error.png")
        
    finally:
        if browser:
            # 清理扩展临时目录
            for ext_dir in getattr(browser, '_ext_tmp_dirs', []):
                shutil.rmtree(ext_dir, ignore_errors=True)
            browser.quit()
            print("\n浏览器已安全关闭")
