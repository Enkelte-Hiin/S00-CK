import os
import random
import time
from DrissionPage import ChromiumOptions, ChromiumPage
from urllib.parse import urlparse

class CFBypasser:
    def __init__(self, headless=True):
        self.page = None
        self.headless = headless
        self.screenshot_dir = "debug_screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
    def init_browser(self):
        """初始化浏览器"""
        # 创建 ChromiumOptions 对象来设置浏览器参数
        options = ChromiumOptions()
        
        # 设置必要的参数，适合 GitHub Actions 或无头模式
        options.set_argument('--no-sandbox')  # CI 环境必须
        options.set_argument('--disable-gpu')  # 禁用 GPU
        options.set_argument('--disable-dev-shm-usage')  # 避免内存问题
        options.set_argument('--disable-blink-features=AutomationControlled')  # 隐藏自动化标志
        options.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')  # 设置用户代理
        
        # 如果是无头模式，添加 --headless 参数
        if self.headless:
            options.set_argument('--headless')
        
        # 使用配置好的 options 初始化 ChromiumPage
        self.page = ChromiumPage(options)
        
        # 清除旧 cookie（修复点：使用 clear_cache(cookies=True) 替代 delete_all_cookies()）
        self.page.clear_cache(cookies=True)
        
        # 配置页面设置
        self.page.set_setting('webdriver', 'undefined')
        self.page.set_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-CH-UA-Platform': '"Windows"'
        })
        
        if self.headless:
            self.page.set_window_max()

    def capture_screen(self, filename):
        """截图并保存"""
        if self.page is not None:
            timestamp = int(time.time())
            path = f"{self.screenshot_dir}/{timestamp}_{filename}.png"
            self.page.get_screenshot(path, full_page=True)
            return path
        else:
            print("浏览器已关闭，无法截图。")
            return None

    def human_interaction(self, retry=3):
        """模拟人类行为绕过验证"""
        for attempt in range(retry):
            try:
                viewport_size = self.page.get_window_size()
                actions = [
                    (random.uniform(0.2, 0.5),  # 移动速度
                     random.randint(3, 7),      # 移动步数
                     random.randint(30, 70))    # 移动幅度
                ]
                
                start_x = random.randint(0, viewport_size['width']//2)
                start_y = random.randint(0, viewport_size['height']//2)
                self.page.mouse.move_to(start_x, start_y)
                
                for _ in range(actions[1]):
                    offset_x = random.randint(-actions[2], actions[2])
                    offset_y = random.randint(-actions[2], actions[2])
                    self.page.mouse.move(offset_x, offset_y)
                    time.sleep(actions[0] + random.uniform(-0.1, 0.1))
                
                if random.random() < 0.7:
                    self.page.mouse.click()
                    time.sleep(random.uniform(1.5, 3.0))
                
                if self.check_cf_passed():
                    return True
                    
            except Exception as e:
                self.capture_screen(f"error_attempt{attempt}")
                if attempt == retry - 1:
                    raise Exception(f"模拟人类交互失败: {str(e)}")
        
        return False

    def check_cf_passed(self, timeout=30):
        """检查是否通过 Cloudflare 验证"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_title = self.page.title.lower()
            if 'cloudflare' not in current_title and 'challenge' not in current_title:
                return True
            if not self.page.ele('css:#challenge-form', timeout=2):
                return True
            if 'cf_clearance' in self.page.cookies():
                return True
            time.sleep(2)
        return False

    def get_cookies(self):
        """获取格式化的 Cookies"""
        cookies = self.page.cookies()
        return '; '.join([f"{c['name']}={c['value']}" for c in cookies])

    def bypass_protection(self, url):
        """主流程：绕过 Cloudflare 保护"""
        try:
            self.init_browser()
            self.page.get(url)
            self.capture_screen("initial_page")
            
            time.sleep(5 if self.headless else 3)
            
            if self.page.title == 'Just a moment...':
                time.sleep(5 + random.uniform(1, 3))
                self.capture_screen("pre_jschallenge")
                
            elif 'challenge' in self.page.title:
                if not self.human_interaction():
                    raise Exception("Cloudflare 交互验证失败")
                self.capture_screen("post_challenge")
            
            if not self.check_cf_passed():
                raise Exception("Cloudflare 验证未通过")
                
            if 'cf_clearance' not in self.page.cookies():
                raise Exception("未获取到关键 Cookie")
                
            return self.get_cookies()
            
        except Exception as e:
            if self.page is not None:
                self.capture_screen("final_error")
            raise
        finally:
            if self.page is not None:
                self.page.quit()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--headless', type=bool, default=True)
    parser.add_argument('--url', default='https://www.serv00.com/offer/create_new_account')
    args = parser.parse_args()
    
    try:
        cf = CFBypasser(headless=args.headless)
        cookies = cf.bypass_protection(args.url)
        print(f"成功获取 Cookies:\n{cookies}")
    except Exception as e:
        print(f"失败原因: {str(e)}")
        exit(1)
