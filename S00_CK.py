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
    # 图像预处理
    screenshot = cv2.imread(screenshot_path)
    template = cv2.imread(template_path)
    
    # 灰度化提升匹配速度
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    # 模板匹配
    res = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    threshold = 0.7  # 根据实际调整
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
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        
        # 截取初始页面
        driver.save_screenshot('screenshot.png')
        
        # 定位验证按钮
        button_pos = locate_verify_button()
        if not button_pos:
            raise Exception("Turnstile验证框未找到")
        
        # 精确点击验证框
        body = driver.find_element(By.TAG_NAME, 'body')
        action = ActionChains(driver)
        action.move_to_element_with_offset(body, button_pos[0], button_pos[1]).click().perform()
        
        # 等待验证通过并检查结果
        WebDriverWait(driver, 15).until(
            lambda d: 'Create an account' in d.page_source
        )
        
        # 验证成功后获取Cookie
        cookies = driver.get_cookies()
        print(f"成功获取Cookie: {cookies}")
        return cookies
        
    except Exception as e:
        print(f"运行失败: {str(e)}")
        driver.save_screenshot('error.png')  # 保存错误截图
        return None
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
