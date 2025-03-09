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

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def verify_image_match(screenshot_path, template_path):
    """图像匹配核心逻辑"""
    try:
        # 读取图像
        screenshot = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        
        # 多尺度模板匹配
        res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        # 动态阈值
        threshold = max(0.6, max_val - 0.1)
        logger.info(f"匹配度: {max_val:.2f} (阈值: {threshold:.2f})")
        
        if max_val < threshold:
            return None
            
        # 计算中心点
        h, w = template.shape
        x_center = max_loc[0] + w // 2
        y_center = max_loc[1] + h // 2
        return (x_center, y_center)
        
    except Exception as e:
        logger.error(f"图像处理失败: {str(e)}")
        return None

def bypass_cloudflare():
    """绕过Cloudflare验证主逻辑"""
    driver = None
    try:
        # 浏览器配置
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # 必须指定Chrome路径
        chrome_path = "/usr/bin/google-chrome"
        if not os.path.exists(chrome_path):
            raise FileNotFoundError(f"Chrome路径不存在: {chrome_path}")
            
        # 启动浏览器
        driver = uc.Chrome(
            options=options,
            browser_executable_path=chrome_path,
            version_main=120
        )
        
        # 访问目标页面
        target_url = 'https://www.serv00.com/offer/create_new_account'
        driver.get(target_url)
        logger.info(f"已访问: {target_url}")
        
        # 等待页面加载
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        
        # 保存截图
        screenshot_path = 'page_screenshot.png'
        driver.save_screenshot(screenshot_path)
        logger.info("页面截图已保存")
        
        # 定位验证框
        template_path = 'image.jpg'  # 必须使用此文件名
        click_pos = verify_image_match(screenshot_path, template_path)
        if not click_pos:
            raise ValueError("验证框定位失败，请检查image.jpg")
            
        logger.info(f"点击坐标: {click_pos}")
        
        # 模拟点击
        body = driver.find_element(By.TAG_NAME, 'body')
        action = ActionChains(driver)
        action.move_to_element_with_offset(body, click_pos[0], click_pos[1])
        action.click().pause(1).perform()
        logger.info("已执行点击操作")
        
        # 等待验证通过
        WebDriverWait(driver, 20).until(
            EC.title_contains("Create an account")
        )
        logger.info("验证已通过")
        
        # 获取Cookie
        cookies = driver.get_cookies()
        logger.info("成功获取Cookies:")
        for cookie in cookies:
            logger.info(f"{cookie['name']}: {cookie['value']}")
            
        return cookies
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        if driver:
            driver.save_screenshot('error.png')
        return None
        
    finally:
        if driver:
            driver.quit()
            logger.info("浏览器已关闭")

if __name__ == "__main__":
    bypass_cloudflare()
