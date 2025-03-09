import os
import cv2
import time
import logging
import numpy as np
from PIL import Image
import pytesseract
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc

# ================== 配置区块 ==================
TEMPLATE_IMAGE = "image.jpg"  # 您的模板文件名
TARGET_URL = "https://www.serv00.com/offer/create_new_account"
TIMEOUT = 15  # 全局超时时间(秒)
# =============================================

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def match_template(screenshot_path):
    """核心图像匹配函数"""
    try:
        # 读取图像并灰度化
        screenshot = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        template = cv2.imread(TEMPLATE_IMAGE, cv2.IMREAD_GRAYSCALE)
        
        # 多尺度模板匹配
        res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        
        # 动态阈值计算
        threshold = max(0.6, max_val - 0.1)
        logger.info(f"匹配度: {max_val:.2f} (阈值: {threshold:.2f})")
        
        if max_val < threshold:
            return None
            
        # 计算点击坐标
        h, w = template.shape
        return (
            max_loc[0] + w // 2,
            max_loc[1] + h // 2
        )
    except Exception as e:
        logger.error(f"图像处理失败: {str(e)}")
        return None

def main_flow():
    """主业务流程"""
    driver = None
    try:
        # ================== 浏览器配置 ==================
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # 自动检测浏览器路径
        browser_paths = [
            "/usr/bin/chromium-browser",  # Ubuntu官方源路径
            "/usr/bin/google-chrome"     # 兼容其他安装方式
        ]
        for path in browser_paths:
            if os.path.exists(path):
                options.binary_location = path
                break
        else:
            raise FileNotFoundError("未找到浏览器可执行文件")

        # 启动浏览器
        driver = uc.Chrome(
            options=options,
            version_main=120  # 匹配Chromium 120版本
        )
        
        # ================== 页面操作 ==================
        logger.info(f"访问目标页面: {TARGET_URL}")
        driver.get(TARGET_URL)
        
        # 等待页面加载
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # 截图并匹配
        screenshot_path = "page_screenshot.png"
        driver.save_screenshot(screenshot_path)
        click_pos = match_template(screenshot_path)
        
        if not click_pos:
            raise ValueError("验证框定位失败，请检查image.jpg")
            
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
        logger.info("验证已通过")
        
        # 获取Cookies
        cookies = driver.get_cookies()
        logger.info("获取到Cookies:")
        for cookie in cookies:
            logger.info(f"  {cookie['name']}: {cookie['value']}")
            
        return True
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        if driver:
            driver.save_screenshot("error.png")
        return False
        
    finally:
        if driver:
            driver.quit()
            logger.info("浏览器实例已关闭")

if __name__ == "__main__":
    main_flow()
