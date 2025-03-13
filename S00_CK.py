# S00_CK.py
import os
import random
import time
from DrissionPage import ChromiumPage
from urllib.parse import urlparse

class CFBypasser:
    def __init__(self, headless=True):
        self.page = None
        self.headless = headless
        self.screenshot_dir = "debug_screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
    def init_browser(self):
        """初始化浏览器配置"""
        self.page = ChromiumPage(flags=[
            '--no-sandbox',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ])
        
        # 指纹伪装
        self.page.set.cookie('', '')  # 清除旧cookie
        self.page.set.setting('webdriver', 'undefined')
        self.page.set.headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-CH-UA-Platform': '"Windows"'
        })
        
        if self.headless:
            self.page.set.headless(True)
            self.page.set.window.max()

    def capture_screen(self, filename):
        """带时间戳的截图"""
        timestamp = int(time.time())
        path = f"{self.screenshot_dir}/{timestamp}_{filename}.png"
        self.page.get_screenshot(path, full_page=True)
        return path

    def human_interaction(self, retry=3):
        """模拟人类交互绕过验证"""
        for attempt in range(retry):
            try:
                # 生成随机交互路径
                viewport_size = self.page.get_window_size()
                actions = [
                    (random.uniform(0.2, 0.5),  # 移动速度
                    random.randint(3, 7),       # 移动步数
                    random.randint(30, 70))       # 移动幅度
                ]
                
                # 生成移动轨迹
                start_x = random.randint(0, viewport_size['width']//2)
                start_y = random.randint(0, viewport_size['height']//2)
                self.page.mouse.move_to((start_x, start_y))
                
                for _ in range(actions[1]):
                    offset_x = random.randint(-actions[2], actions[2])
                    offset_y = random.randint(-actions[2], actions[2])
                    self.page.mouse.move(offset_x, offset_y)
                    time.sleep(actions[0] + random.uniform(-0.1, 0.1))
                
                # 随机点击
                if random.random() < 0.7:
                    self.page.mouse.click()
                    time.sleep(random.uniform(1.5, 3.0))
                
                # 检测验证状态
                if self.check_cf_passed():
                    return True
                    
            except Exception as e:
                self.capture_screen(f"error_attempt{attempt}")
                if attempt == retry -1:
                    raise Exception(f"Human interaction failed: {str(e)}")
        
        return False

    def check_cf_passed(self, timeout=30):
        """检测Cloudflare验证状态"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 检测方式1：标题变化
            current_title = self.page.title.lower()
            if 'cloudflare' not in current_title and 'challenge' not in current_title:
                return True
                
            # 检测方式2：特定元素消失
            if not self.page.ele('css:#challenge-form', timeout=2):
                return True
                
            # 检测方式3：请求头验证
            if 'cf_clearance' in self.page.cookies():
                return True
                
            time.sleep(2)
            
        return False

    def get_cookies(self):
        """获取格式化后的Cookies"""
        cookies = self.page.cookies()
        return '; '.join([f"{c['name']}={c['value']}" for c in cookies])

    def bypass_protection(self, url):
        """主执行流程"""
        try:
            self.init_browser()
            self.page.get(url)
            self.capture_screen("initial_page")
            
            # 等待Cloudflare初始化
            time.sleep(5 if self.headless else 3)
            
            # 自动检测验证类型
            if self.page.title == 'Just a moment...':
                # 处理5秒盾
                time.sleep(5 + random.uniform(1,3))
                self.capture_screen("pre_jschallenge")
                
            elif 'challenge' in self.page.title:
                # 需要交互验证
                if not self.human_interaction():
                    raise Exception("Cloudflare交互验证失败")
                self.capture_screen("post_challenge")
                
            # 最终状态检测
            if not self.check_cf_passed():
                raise Exception("Cloudflare验证未通过")
                
            # 验证成功后获取Cookie
            if 'cf_clearance' not in self.page.cookies():
                raise Exception("未获取到关键Cookie")
                
            return self.get_cookies()
            
        except Exception as e:
            self.capture_screen("final_error")
            raise
        finally:
            if self.page:
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
        print(f"成功获取Cookies:\n{cookies}")
    except Exception as e:
        print(f"失败原因: {str(e)}")
        exit(1)
