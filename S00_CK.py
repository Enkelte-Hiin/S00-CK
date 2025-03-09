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
import os

def locate_verify_button(screenshot_path='screenshot.png', template_path='image.jpg'):
    # 读取图像并灰度化
    screenshot = cv2.imread(screenshot_path)
    template = cv2.imread(template_path)
    
    # 灰度转换提升匹配速度
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    # 模板匹配
    res = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    threshold = 0.7
    loc = np.where(res >= threshold)
    
    if len(loc[0]) == 0:
        return None
    
    # 取第一个匹配点
    x, y = loc[1][0], loc[0][0]
    w, h = template_gray.shape[::-1]
    center_x = x + w // 2
    center_y = y + h // 2
    return (center_x, center_y)

def main():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = uc.Chrome(options=options)
    try:
        driver.get('https://www.serv00.com/offer/create_new_account')
        
        # 修复括号闭合问题
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        
        # 截取页面截图
        driver.save_screenshot('screenshot.png')
        
        # 定位验证按钮
        button_pos = locate_verify_button()
        if not button_pos:
            raise Exception("验证框定位失败")
        
        # 精确点击
        body = driver.find_element(By.TAG_NAME, 'body')
        action = ActionChains(driver)
        action.move_to_element_with_offset(body, button_pos[0], button_pos[1]).click().perform()
        
        # 验证结果检测
        WebDriverWait(driver, 15).until(
            lambda d: 'Create an account' in d.page_source
        )
        
        # 获取Cookie
        cookies = driver.get_cookies()
        print(f"成功获取Cookies: {cookies}")
        return cookies
        
    except Exception as e:
        print(f"运行失败: {str(e)}")
        driver.save_screenshot('error.png')
        return None
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
