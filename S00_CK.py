import os
import cv2
import logging
import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc

# ================== 配置常量 ==================
TEMPLATE_PATH = "image.jpg"
TARGET_URL = "https://www.serv00.com/offer/create_new_account"
CHROME_PATH = "/usr/bin/chromium-browser"
DRIVER_PATH = "/usr/local/bin/chromedriver"
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
    """环境验证（硬核版）"""
    if not os.path.exists(CHROME_PATH):
        raise FileNotFoundError(f"浏览器路径不存在: {CHROME_PATH}")
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"模板文件不存在: {TEMPLATE_PATH}")
    if not os.access(DRIVER_PATH, os.X_OK):
        raise PermissionError("chromedriver 无执行权限")

def match_template(screenshot_path):
    """图像匹配（无符号错误版）"""
    try:
        # 读取图像
        screenshot = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        template = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
        
        # 模板匹配
        res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        
        # 动态阈值
        threshold = max(0.6, max_val - 0.1)
        logger.info(f"匹配度: {max_val:.2f} (阈值: {threshold:.2f})")
        
        if max_val < threshold:
            return None
            
        # 计算坐标
        h, w = template.shape
        return (max_loc[0] + w//2, max_loc[1] + h//2)
    except Exception as e:
        logger.error(f"图像处理失败: {str(e)}")
        return None

def main():
    """主流程（绝对完整版）"""
    driver = None
    try:
        # 环境验证
        validate_environment()

        # 浏览器配置
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = CHROME_PATH

        # 启动浏览器
        driver = uc.Chrome(
            options=options,
            driver_executable_path=DRIVER_PATH,
            version_main=120,
            use_subprocess=True
        )
        
        # 访问页面
        logger.info(f"正在访问: {TARGET_URL}")
        driver.get(TARGET_URL)
        
        # 等待加载
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # 截图匹配
        screenshot_path = "page.png"
        driver.save_screenshot(screenshot_path)
        click_pos = match_template(screenshot_path)
        
        if not click_pos:
            raise RuntimeError("验证框定位失败，请检查image.jpg的精度")
            
        # 执行点击
        body = driver.find_element(By.TAG_NAME, "body")
        ActionChains(driver)\
            .move_to_element_with_offset(body, click_pos[0], click_pos[1])\
            .click()\
            .pause(1)\
            .perform()
        logger.info(f"已点击坐标: {click_pos}")
        
        # 验证结果
        WebDriverWait(driver, TIMEOUT).until(
            EC.title_contains("Create an account")
        )
        logger.info("验证成功")
        
        # 获取Cookies
        cookies = driver.get_cookies()
        logger.info("获取到Cookies:")
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
            logger.info("浏览器已关闭")

if __name__ == "__main__":
    main()
