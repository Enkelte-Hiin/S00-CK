from DrissionPage import Chromium, ChromiumOptions
import time
import os
import tempfile
import shutil
import json

# 定义函数来关闭所有 Microsoft Edge 进程
def close_existing_browsers():
    try:
        os.system("taskkill /f /im msedge.exe")
        print("已关闭所有现有的 Edge 浏览器进程")
    except Exception as e:
        print(f"关闭浏览器进程时出错：{e}")
    time.sleep(1)

# 设置 Microsoft Edge 浏览器的路径
edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

# 在脚本运行前关闭现有浏览器
close_existing_browsers()

# 创建临时用户数据目录
temp_dir = tempfile.mkdtemp()
print(f"使用临时用户数据目录：{temp_dir}")

# 配置浏览器选项
options = ChromiumOptions()
options.set_paths(browser_path=edge_path)
options.set_argument("--window-size=1024,768")
options.set_argument("--window-position=0,0")
options.set_argument("--incognito")
options.set_argument(f"--user-data-dir={temp_dir}")
# 可选：尝试无头模式以适配 GitHub Actions
# options.set_argument("--headless")

# 启动浏览器
try:
    browser = Chromium(options)
    tab = browser.latest_tab
    print("成功连接到 Edge 浏览器（无痕模式 + 新用户数据目录）！")
except Exception as e:
    print(f"连接失败：{e}")
    shutil.rmtree(temp_dir, ignore_errors=True)
    exit()

# 导航到目标网站
tab.get("https://www.serv00.com/offer/create_new_account")

# 等待页面加载
tab.wait(10)

# 定时点击以绕过 Cloudflare 验证码
max_attempts = 20
attempt = 0

while attempt < max_attempts:
    tab.actions.move_to((64, 290)).click()
    print(f"第 {attempt + 1} 次点击，位置：(64, 290)")
    time.sleep(5)
    title = tab.title.lower()
    if "serv00.com" in title:
        print("网站标题包含 'serv00.com'，验证码已通过")
        break
    elif "just a" in title:
        print("网站标题包含 'just a'，仍在验证中")
    else:
        print("网站标题未匹配，继续尝试")
    attempt += 1

# 获取 Cookie 并保存到文件
if attempt < max_attempts:
    cookies = tab.cookies()
    cf_clearance = next((cookie for cookie in cookies if cookie['name'] == 'cf_clearance'), None)
    if cf_clearance:
        print("获取到的 cf_clearance Cookie：", cf_clearance)
        # 保存到文件
        with open("cf_clearance.json", "w") as f:
            json.dump({"cf_clearance": cf_clearance['value']}, f)
        print("已将 cf_clearance 保存到 cf_clearance.json")
    else:
        print("未找到 cf_clearance Cookie")
else:
    print("达到最大尝试次数，未能通过验证码")

# 关闭浏览器并清理临时目录
browser.quit()
shutil.rmtree(temp_dir, ignore_errors=True)
print("已清理临时用户数据目录")
