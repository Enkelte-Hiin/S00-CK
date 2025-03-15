import os
import tempfile
import json
import shutil
import time
from DrissionPage import Chromium, ChromiumOptions
from DrissionPage.errors import PageDisconnectedError

# 扩展的 manifest 文件内容
MANIFEST_CONTENT = {
    "manifest_version": 3,
    "name": "Turnstile Patcher",
    "version": "0.1",
    "content_scripts": [{
        "js": ["./script.js"],
        "matches": ["<all_urls>"],
        "run_at": "document_start",
        "all_frames": True,
        "world": "MAIN"
    }]
}

# 扩展的 JavaScript 内容，用于伪造鼠标坐标
SCRIPT_CONTENT = """
function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}
let screenX = getRandomInt(800, 1200);
let screenY = getRandomInt(400, 600);
Object.defineProperty(MouseEvent.prototype, 'screenX', { value: screenX });
Object.defineProperty(MouseEvent.prototype, 'screenY', { value: screenY });
"""

def create_extension() -> str:
    """创建临时浏览器扩展"""
    temp_dir = tempfile.mkdtemp(prefix='turnstile_extension_')
    with open(os.path.join(temp_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(MANIFEST_CONTENT, f, indent=4)
    with open(os.path.join(temp_dir, 'script.js'), 'w', encoding='utf-8') as f:
        f.write(SCRIPT_CONTENT.strip())
    return temp_dir

def get_patched_browser(headless=True) -> Chromium:
    """配置并返回带扩展的 Chromium 浏览器"""
    options = ChromiumOptions().auto_port()
    if headless:
        options.headless(True)
    options.set_argument("--no-sandbox")
    extension_path = create_extension()
    options.add_extension(extension_path)
    browser = Chromium(options)
    shutil.rmtree(extension_path)
    return browser


def click_turnstile_checkbox(tab, retries=3) -> bool:
    """点击 Turnstile 验证码框并验证结果，支持重试"""
    for attempt in range(retries):
        try:
            print(f"尝试 {attempt + 1}")
            # 等待页面加载完成
            tab.wait.doc_loaded(timeout=10)
            
            # 重新定位 Turnstile 元素
            solution = tab.ele("@name=cf-turnstile-response", timeout=10)
            if not solution:
                raise RuntimeError("未检测到 Turnstile 组件")
            
            wrapper = solution.parent()
            iframe = wrapper.shadow_root.ele("tag:iframe", timeout=10)
            if not iframe:
                raise RuntimeError("未找到 iframe")
            
            iframe_body = iframe.ele("tag:body").shadow_root
            checkbox = iframe_body.ele("tag:input", timeout=10)
            if not checkbox:
                raise RuntimeError("未找到复选框")
            
            success = iframe_body.ele("@id=success", timeout=10)
            if not success:
                raise RuntimeError("未找到成功元素")
            
            # 点击复选框
            checkbox.click()
            
            # 等待成功元素显示
            return tab.wait.ele_displayed(success, timeout=5)
        except Exception as e:
            print(f"尝试 {attempt + 1} 失败: {e}")
            if attempt < retries - 1:
                time.sleep(2)  # 等待 2 秒后重试
            else:
                raise RuntimeError("所有尝试均失败")

if __name__ == "__main__":
    try:
        browser = get_patched_browser(headless=True)  # GitHub Actions 使用无头模式
        tab = browser.get_tab()
        tab.get("https://www.serv00.com/offer/create_new_account")
        if click_turnstile_checkbox(tab):
            print("Turnstile 绕过成功")
            cookies = tab.get_cookies()
            print("Cookies:", cookies)
        else:
            print("Turnstile 绕过失败")
    except Exception as e:
        print(f"脚本执行失败: {e}")
    finally:
        browser.quit()
