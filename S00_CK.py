import os
import cv2
import logging
import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc

# ================== 配置区块 ==================
TEMPLATE_PATH = "image.jpg"  # 您的模板文件
TARGET_URL = "https://www.serv00.com/offer/create_new_account"
CHROME_PATH = "/usr/bin/chromium-browser"  # 系统安装路径
TIMEOUT = 15
# =============================================

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def validate_environment():
    """环境验证"""
    checks = [
        (os.path.exists(CHROME_PATH)), 
        (os.path.exists(TEMPLATE_PATH))
    ]
    if not all(checks):
        missing = [
            "浏览器" if not checks[0] else "",
            "模板图片" if not checks[1] else ""
        ]
        raise FileNotFoundError(f"缺失: {', '.join(filter(None, missing))}")

def match_template(screenshot_path):
    """图像匹配核心逻辑"""
    try:
        # 图像预处理
        screenshot = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        template = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
        
        # 多尺度匹配
        res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        
        # 动态阈值
        threshold = max(0.6, max_val - 0.1)
        logger.info(f"匹配度: {max_val:.2f} (阈值: {threshold:.2f})")
        
        if max_val < threshold:
            return None
            
        # 计算中心坐标
        h, w = template.shape
        return (max_loc[0] + w//2, max_loc[1] + h//2)
    except Exception as e:
        logger.error(f"图像处理异常: {str(e)}")
        return None

def main():
    """主流程"""
    driver = None
    try:
        validate_environment()  # 环境预检
        
        # ================== 浏览器配置 ==================
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = CHROME_PATH  # 硬编码路径
        
        # 驱动配置
        driver = uc.Chrome(
            options=options,
            driver_executable_path="/usr/local/bin/chromedriver",  # 系统驱动路径
            version_main=120  # 精确版本控制
        )
        
        # ================== 页面操作 ==================
        logger.info(f"访问目标: {TARGET_URL}")
        driver.get(TARGET_URL)
        
        # 等待加载
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # 截图处理
        screenshot_path = "page.png"
        driver.save_screenshot(screenshot_path)
        click_pos = match_template(screenshot_path)
        
        if not click_pos:
            raise RuntimeError("验证框定位失败，请检查image.jpg精度")
            
        # 执行点击
        body = driver.find_element(By.TAG_NAME, "body")
        ActionChains(driver)\
            .move_to_element_with_offset(body, *click_pos)\
            .click()\
            .pause(1)\
            .perform()
        logger.info(f"已点击坐标: {click_pos}")
        
        # 验证结果
        WebDriverWait(driver, TIMEOUT).until(
            EC.title_contains("Create an account"))
        logger.info("验证通过")
        
        # 获取Cookies
        cookies = driver.get_cookies()
        logger.info("成功获取Cookies:")
        for cookie in cookies:
            logger.info(f"{cookie['name']}: {cookie['value'][:15]}...")
            
        return True
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        if driver:
            driver.save_screenshot("error.png")
        return False
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
