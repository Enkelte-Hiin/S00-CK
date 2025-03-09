import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import cv2
import numpy as np
import time
import pytesseract
from PIL import Image
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def preprocess_image(image_path):
    """图像预处理增强识别精度"""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    return thresh

def find_verify_position(screenshot_path, template_path):
    """使用模板匹配定位验证框"""
    try:
        # 预处理图像
        screenshot = preprocess_image(screenshot_path)
        template = preprocess_image(template_path)
        
        # 多尺度模板匹配
        res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        # 动态阈值处理
        threshold = max(0.7, max_val - 0.1)  # 自适应阈值
        logger.info(f"匹配置信度: {max_val:.2f}, 使用阈值: {threshold:.2f}")
        
        if max_val < threshold:
            return None
            
        # 计算中心坐标
        h, w = template.shape
        x = max_loc[0] + w // 2
        y = max_loc[1] + h // 2
        return (x, y)
        
    except Exception as e:
        logger.error(f"图像处理失败: {str(e)}")
        return None

def cloudflare_bypass():
    """执行Cloudflare绕过流程"""
    driver = None
    try:
        # 浏览器配置
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')  # 新版无头模式
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # 启动浏览器 (指定主版本)
        driver = uc.Chrome(
            options=options,
            version_main=120,  # 与Docker镜像版本一致
            use_subprocess=True
        )
        
        # 访问目标页面
        target_url = 'https://www.serv00.com/offer/create_new_account'
        driver.get(target_url)
        logger.info(f"已访问目标页面: {target_url}")
        
        # 等待页面加载
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        
        # 截取页面截图
        screenshot_path = 'page_screenshot.png'
        driver.save_screenshot(screenshot_path)
        logger.info("页面截图已保存")
        
        # 定位验证框
        template_path = 'verify_template.png'  # 需提前准备的模板图片
        click_position = find_verify_position(screenshot_path, template_path)
        
        if not click_position:
            raise Exception("验证框定位失败，请检查模板图片")
            
        logger.info(f"验证框坐标定位成功: {click_position}")
        
        # 模拟点击
        body = driver.find_element(By.TAG_NAME, 'body')
        action = ActionChains(driver)
        action.move_to_element_with_offset(body, click_position[0], click_position[1])
        action.click().pause(0.5).perform()
        logger.info("已执行验证点击")
        
        # 等待验证通过
        WebDriverWait(driver, 20).until(
            EC.title_contains("Create an account")  # 根据实际页面标题调整
        )
        logger.info("验证已成功通过")
        
        # 获取Cookie
        cookies = driver.get_cookies()
        logger.info("获取到Cookies:")
        for cookie in cookies:
            logger.info(f"{cookie['name']}: {cookie['value']}")
            
        return cookies
        
    except Exception as e:
        driver.save_screenshot('error.png')
        logger.error(f"流程执行失败: {str(e)}")
        return None
        
    finally:
        if driver:
            driver.quit()
            logger.info("浏览器已关闭")

if __name__ == "__main__":
    cloudflare_bypass()
