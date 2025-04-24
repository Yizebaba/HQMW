import time
import random
import os
import json
import requests
import urllib.request
from datetime import datetime, timedelta
import schedule
import threading
import socket
import socks
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# 创建存储凭证和媒体文件的目录
if not os.path.exists("credentials"):
    os.makedirs("credentials")
if not os.path.exists("media"):
    os.makedirs("media")
if not os.path.exists("logs"):
    os.makedirs("logs")
if not os.path.exists("stats"):
    os.makedirs("stats")

# 配置浏览器（自动下载ChromeDriver）
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--lang=en-US")  # 避免语言检测

# 禁用自动化标志（降低被检测风险）
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# 日志记录函数
def log_activity(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)
    with open(os.path.join("logs", "activity.log"), "a", encoding="utf-8") as f:
        f.write(log_message + "\n")

# 随机化延迟（模拟真人）
def human_delay(min_sec=1.0, max_sec=3.0):
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay

# ==== 代理IP配置 ====

def setup_proxy(proxy_address=None):
    """
    设置代理IP
    proxy_address: 代理地址，如'socks5://127.0.0.1:9050'或'http://user:pass@10.10.1.10:3128'
    """
    if not proxy_address:
        config = load_config()
        proxy_address = config.get("proxy", "")
    
    if not proxy_address:
        log_activity("未配置代理IP，使用本地连接", "INFO")
        return False
    
    try:
        # 解析代理地址
        if proxy_address.startswith("socks5://"):
            # SOCKS5代理
            proxy_parts = proxy_address[9:].split(":")
            proxy_host = proxy_parts[0]
            proxy_port = int(proxy_parts[1]) if len(proxy_parts) > 1 else 1080
            
            # 设置socket代理
            socks.set_default_proxy(socks.SOCKS5, proxy_host, proxy_port)
            socket.socket = socks.socksocket
            
            log_activity(f"已配置SOCKS5代理: {proxy_host}:{proxy_port}", "INFO")
        else:
            # HTTP代理
            chrome_options.add_argument(f'--proxy-server={proxy_address}')
            log_activity(f"已配置HTTP代理: {proxy_address}", "INFO")
        
        return True
    except Exception as e:
        log_activity(f"代理设置失败: {str(e)}", "ERROR")
        return False

# ==== 定时任务功能 ====

def schedule_post(config, platforms=None, delay_hours=None):
    """
    设置定时发布任务
    config: 配置字典
    platforms: 要发布的平台列表，如None则使用所有配置的平台
    delay_hours: 延迟发布时间（小时），如None则使用随机时间
    """
    if not platforms:
        # 使用所有配置了账号的平台
        platforms = [p for p, accounts in config["accounts"].items() if accounts]
    
    if not platforms:
        log_activity("没有可用平台，无法设置定时任务", "WARNING")
        return False
    
    # 为每个平台设置发布任务
    for platform in platforms:
        if not delay_hours:
            # 使用平台配置的发布频率
            frequency = config["post_frequency"].get(platform, 24)
            # 添加随机偏移量，避免所有平台同时发布
            offset = random.uniform(0, frequency * 0.2)
            delay = frequency + offset
        else:
            delay = delay_hours
        
        # 计算发布时间
        post_time = datetime.now() + timedelta(hours=delay)
        formatted_time = post_time.strftime("%Y-%m-%d %H:%M:%S")
        
        log_activity(f"已为{platform}设置定时发布任务，将在{formatted_time}执行", "INFO")
        
        # 将发布任务添加到调度器
        schedule.every(delay).hours.do(
            lambda p=platform: scheduled_post_task(p, config)
        )
    
    # 启动调度器线程
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    return True

def run_scheduler():
    """运行调度器线程"""
    log_activity("调度器线程已启动", "INFO")
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次待执行的任务

def scheduled_post_task(platform, config):
    """实际执行定时发布任务"""
    log_activity(f"开始执行{platform}的定时发布任务", "INFO")
    
    # 选择账号
    account = select_account(platform, config)
    if not account:
        log_activity(f"未找到{platform}可用账号", "WARNING")
        return False
    
    username, password = account
    
    # 选择随机主题
    topic = select_random_topic(config)
    
    # 下载图片
    image_path = download_image(topic)
    if not image_path:
        log_activity(f"无法下载图片，定时任务取消", "ERROR")
        return False
    
    # 生成文案
    length = "long" if platform in ["facebook", "vk"] else "short"
    caption = generate_caption(platform, topic, length)
    
    # 初始化浏览器
    try:
        # 配置代理
        setup_proxy()
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 登录
        login_func = globals().get(f"login_{platform}")
        if not login_func:
            log_activity(f"未找到{platform}登录函数", "ERROR")
            driver.quit()
            return False
        
        login_result = login_func(username, password)
        if not login_result:
            log_activity(f"{platform}账号{username}登录失败", "ERROR")
            driver.quit()
            return False
        
        # 发布内容
        publish_func = globals().get(f"post_to_{platform}")
        if not publish_func:
            log_activity(f"未找到{platform}发布函数", "ERROR")
            driver.quit()
            return False
        
        publish_result = publish_func(image_path, caption)
        
        # 更新发布时间
        if publish_result:
            update_account_post_time(platform, username)
            log_activity(f"{platform}定时发布任务成功完成", "INFO")
            
            # 记录发布统计
            record_post_stats(platform, username, topic, "success")
        else:
            log_activity(f"{platform}定时发布任务失败", "ERROR")
            record_post_stats(platform, username, topic, "failed")
        
        driver.quit()
        return publish_result
        
    except Exception as e:
        log_activity(f"定时发布任务执行出错: {str(e)}", "ERROR")
        record_post_stats(platform, username, topic, "error")
        try:
            driver.quit()
        except:
            pass
        return False

# ==== 数据统计功能 ====

def record_post_stats(platform, username, topic, status):
    """
    记录发布统计数据
    platform: 平台名称
    username: 用户名
    topic: 发布主题
    status: 状态(success/failed/error)
    """
    stats_file = os.path.join("stats", "post_stats.json")
    
    # 读取现有统计数据
    stats = {}
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except:
            pass
    
    # 确保各级字典都存在
    if platform not in stats:
        stats[platform] = {}
    if username not in stats[platform]:
        stats[platform][username] = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "topics": {}
        }
    
    # 更新统计数据
    stats[platform][username]["total"] += 1
    if status == "success":
        stats[platform][username]["success"] += 1
    elif status == "failed" or status == "error":
        stats[platform][username]["failed"] += 1
    
    # 主题统计
    if topic not in stats[platform][username]["topics"]:
        stats[platform][username]["topics"][topic] = 0
    stats[platform][username]["topics"][topic] += 1
    
    # 全局统计
    if "global" not in stats:
        stats["global"] = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "platforms": {},
            "topics": {}
        }
    
    stats["global"]["total"] += 1
    if status == "success":
        stats["global"]["success"] += 1
    elif status == "failed" or status == "error":
        stats["global"]["failed"] += 1
    
    # 平台统计
    if platform not in stats["global"]["platforms"]:
        stats["global"]["platforms"][platform] = 0
    stats["global"]["platforms"][platform] += 1
    
    # 主题统计
    if topic not in stats["global"]["topics"]:
        stats["global"]["topics"][topic] = 0
    stats["global"]["topics"][topic] += 1
    
    # 添加最新记录时间
    stats["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 保存统计数据
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def get_stats_summary():
    """获取统计数据摘要"""
    stats_file = os.path.join("stats", "post_stats.json")
    if not os.path.exists(stats_file):
        return "暂无统计数据"
    
    try:
        with open(stats_file, "r", encoding="utf-8") as f:
            stats = json.load(f)
        
        if "global" not in stats:
            return "暂无全局统计数据"
        
        global_stats = stats["global"]
        
        # 计算成功率
        success_rate = 0
        if global_stats["total"] > 0:
            success_rate = (global_stats["success"] / global_stats["total"]) * 100
        
        # 找出最常用的平台
        top_platform = max(global_stats["platforms"].items(), key=lambda x: x[1]) if global_stats["platforms"] else ("无", 0)
        
        # 找出最常用的主题
        top_topic = max(global_stats["topics"].items(), key=lambda x: x[1]) if global_stats["topics"] else ("无", 0)
        
        summary = f"""
统计数据摘要:
- 总发布次数: {global_stats['total']}
- 成功次数: {global_stats['success']}
- 失败次数: {global_stats['failed']}
- 成功率: {success_rate:.2f}%
- 最常用平台: {top_platform[0]} ({top_platform[1]}次)
- 最热门主题: {top_topic[0]} ({top_topic[1]}次)
- 最后更新: {stats.get('last_updated', '未知')}
        """
        
        return summary.strip()
        
    except Exception as e:
        return f"统计数据读取失败: {str(e)}"

# ===== 内容生成功能 =====

# 自动生成文案
def generate_caption(platform, topic, length="short"):
    """
    生成适合各平台的文案
    platform: 平台名称，如"instagram", "facebook"等
    topic: 主题，如"旅行", "美食"等
    length: 长度，"short"或"long"
    """
    log_activity(f"为{platform}生成关于{topic}的{length}文案")
    
    # 短文案模板（适合Instagram, Twitter）
    short_templates = [
        "探索{topic}的美好时刻 #生活方式 #{topic}爱好者",
        "每天都是与{topic}相伴的新一天 ✨ #日常生活",
        "{topic}，让生活更精彩！👏 #{topic}生活",
        "沉浸在{topic}的世界里，找到内心的平静 🧘‍♀️ #{topic}时光",
        "分享我的{topic}日常，希望能带给你灵感！💡"
    ]
    
    # 长文案模板（适合Facebook, VK）
    long_templates = [
        "今天想和大家分享关于{topic}的一些心得。\n\n过去几周我一直在探索这个领域，发现了很多有趣的事情。{topic}不仅仅是一种爱好，更是一种生活方式。\n\n你们对{topic}有什么看法？欢迎在评论区分享！ #{topic}分享 #生活方式",
        "{topic}的魅力在于它能让我们从繁忙的生活中抽身而出，找回内心的平静。\n\n每次当我沉浸在{topic}中时，仿佛整个世界都变得不同。\n\n希望我的分享能给你带来一些启发和快乐！ #{topic}时光",
        "关于{topic}，有一个小故事想和大家分享。\n\n最近在实践中，我发现了一些有趣的技巧和方法。\n\n{topic}真的能改变我们看待世界的方式，你们有同感吗？ #分享 #{topic}心得",
        "深入了解{topic}的世界后，我对它有了全新的认识。\n\n从初学者到现在，这段旅程充满了挑战和惊喜。\n\n希望我的经历能鼓励更多人探索{topic}的奇妙！ #{topic}之旅 #成长"
    ]
    
    # 根据平台和长度选择合适的模板
    if platform in ["instagram", "twitter", "tiktok"] or length == "short":
        template = random.choice(short_templates)
    else:
        template = random.choice(long_templates)
    
    # 添加表情符号
    emojis = ["✨", "🔥", "💫", "🌟", "💯", "🙌", "👏", "❤️", "😊", "🎉"]
    if random.random() > 0.5 and "}" in template:  # 50%概率在文案中随机位置添加表情
        parts = template.split("}")
        for i in range(1, len(parts)):
            if random.random() > 0.3:  # 70%概率在每个部分后添加表情
                parts[i] = f" {random.choice(emojis)}" + parts[i]
        template = "}".join(parts)
    
    # 填充主题
    caption = template.format(topic=topic)
    
    # 添加随机标签
    hashtags = [
        f"#{topic}", f"#{platform}分享", "#社交媒体", "#分享生活", 
        f"#{topic}爱好者", "#每日灵感", "#生活方式", f"#{topic}日常"
    ]
    random.shuffle(hashtags)
    selected_hashtags = hashtags[:3+random.randint(0, 3)]  # 选择3-6个标签
    
    if length == "long" and platform != "twitter":
        caption += "\n\n" + " ".join(selected_hashtags)
    else:
        caption += " " + " ".join(selected_hashtags)
    
    log_activity(f"文案生成完成，长度：{len(caption)}字符")
    return caption

# 下载图片
def download_image(keyword, save_path=None):
    """
    根据关键词从网络下载图片
    keyword: 搜索关键词
    save_path: 保存路径，默认为media文件夹下
    返回: 图片本地路径
    """
    log_activity(f"开始下载关键词为'{keyword}'的图片")
    
    if save_path is None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{keyword.replace(' ', '_')}_{timestamp}.jpg"
        save_path = os.path.join("media", filename)
    
    try:
        # 使用Unsplash API获取图片（免费，无需API密钥）
        search_keyword = keyword.replace(" ", "+")
        url = f"https://source.unsplash.com/featured/?{search_keyword}"
        
        # 下载图片
        response = requests.get(url, stream=True)
        response.raise_for_status()  # 如果请求失败则抛出异常
        
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log_activity(f"图片下载成功，保存至: {save_path}")
        return save_path
    
    except Exception as e:
        log_activity(f"图片下载失败: {str(e)}", "ERROR")
        # 如果失败，返回默认图片（如果存在）
        default_image = os.path.join("media", "default.jpg")
        if os.path.exists(default_image):
            return default_image
        return None

# ===== 各平台登录函数 =====

# 1. Instagram 自动化
def login_instagram(username, password):
    log_activity(f"正在登录Instagram账号: {username}...")
    driver.get("https://www.instagram.com/accounts/login/")
    human_delay()
    
    # 输入用户名密码
    try:
        driver.find_element(By.NAME, "username").send_keys(username)
        human_delay(0.5, 1.0)
        driver.find_element(By.NAME, "password").send_keys(password)
        human_delay(0.5, 1.0)
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        human_delay(3.0, 5.0)  # 登录后等待较长时间
        
        # 处理各种弹窗
        try:
            # 保存登录信息弹窗
            save_info_button = driver.find_element(By.XPATH, "//button[text()='稍后再说' or text()='Not Now']")
            save_info_button.click()
            human_delay()
        except Exception as e:
            log_activity(f"未出现保存信息弹窗或处理失败: {e}")
            
        try:
            # 开启通知弹窗
            notification_button = driver.find_element(By.XPATH, "//button[text()='稍后再说' or text()='Not Now']")
            notification_button.click()
        except Exception as e:
            log_activity(f"未出现通知弹窗或处理失败: {e}")
            
        # 验证是否登录成功
        if "instagram.com/accounts/onetap" in driver.current_url or "instagram.com/?" in driver.current_url:
            log_activity("✅ Instagram登录成功！")
            return True
        else:
            log_activity("⚠️ Instagram可能登录失败，请检查...", "WARNING")
            return False
            
    except Exception as e:
        log_activity(f"❌ Instagram登录过程出错: {e}", "ERROR")
        return False

# 2. Facebook 自动化
def login_facebook(username, password):
    log_activity(f"正在登录Facebook账号: {username}...")
    driver.get("https://www.facebook.com/login")
    human_delay()
    
    try:
        # 接受Cookie提示(如果存在)
        try:
            cookie_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), '接受')]")
            cookie_button.click()
            human_delay()
        except:
            pass
            
        # 输入登录信息
        driver.find_element(By.ID, "email").send_keys(username)
        human_delay(0.5, 1.0)
        driver.find_element(By.ID, "pass").send_keys(password)
        human_delay(0.5, 1.0)
        driver.find_element(By.ID, "pass").send_keys(Keys.RETURN)
        human_delay(5.0, 8.0)  # 登录后等待较长时间
        
        # 验证是否登录成功
        if "facebook.com/home" in driver.current_url or "facebook.com/?sk=h_chr" in driver.current_url:
            log_activity("✅ Facebook登录成功！")
            return True
        else:
            log_activity("⚠️ Facebook可能登录失败，请检查...", "WARNING")
            return False
            
    except Exception as e:
        log_activity(f"❌ Facebook登录过程出错: {e}", "ERROR")
        return False

# 3. Twitter/X 自动化
def login_twitter(username, password):
    log_activity(f"正在登录Twitter/X账号: {username}...")
    driver.get("https://twitter.com/i/flow/login")
    human_delay(3.0, 5.0)  # Twitter需要更长的加载时间
    
    try:
        # 输入用户名
        username_field = driver.find_element(By.XPATH, "//input[@autocomplete='username']")
        username_field.send_keys(username)
        human_delay()
        username_field.send_keys(Keys.RETURN)
        human_delay(2.0, 3.0)
        
        # 输入密码
        password_field = driver.find_element(By.XPATH, "//input[@name='password']")
        password_field.send_keys(password)
        human_delay()
        password_field.send_keys(Keys.RETURN)
        human_delay(5.0, 8.0)
        
        # 验证是否登录成功
        if "twitter.com/home" in driver.current_url:
            log_activity("✅ Twitter/X登录成功！")
            return True
        else:
            log_activity("⚠️ Twitter/X可能登录失败，请检查...", "WARNING")
            return False
            
    except Exception as e:
        log_activity(f"❌ Twitter/X登录过程出错: {e}", "ERROR")
        return False

# 4. VK 自动化
def login_vk(username, password):
    log_activity(f"正在登录VK账号: {username}...")
    driver.get("https://vk.com/")
    human_delay()
    
    try:
        # 点击登录按钮
        driver.find_element(By.XPATH, "//button[contains(@class, 'VkIdForm__button')]").click()
        human_delay()
        
        # 输入登录信息
        driver.find_element(By.NAME, "login").send_keys(username)
        human_delay()
        driver.find_element(By.XPATH, "//span[contains(text(), 'Continue')]/parent::button").click()
        human_delay(2.0)
        
        # 输入密码
        driver.find_element(By.NAME, "password").send_keys(password)
        human_delay()
        driver.find_element(By.XPATH, "//span[contains(text(), 'Log in')]/parent::button").click()
        human_delay(5.0)
        
        # 验证是否登录成功
        if "vk.com/feed" in driver.current_url:
            log_activity("✅ VK登录成功！")
            return True
        else:
            log_activity("⚠️ VK可能登录失败，请检查...", "WARNING")
            return False
            
    except Exception as e:
        log_activity(f"❌ VK登录过程出错: {e}", "ERROR")
        return False

# 5. TikTok 自动化（TikTok检测机制严格，可能需更复杂绕过方法）
def login_tiktok(username, password):
    log_activity(f"正在登录TikTok账号: {username}...")
    driver.get("https://www.tiktok.com/login")
    human_delay(3.0, 5.0)
    
    try:
        # 选择邮箱登录
        driver.find_element(By.XPATH, "//a[contains(@href, 'email/login')]").click()
        human_delay(2.0)
        
        # 输入登录信息
        driver.find_element(By.XPATH, "//input[@name='email']").send_keys(username)
        human_delay()
        driver.find_element(By.XPATH, "//input[@name='password']").send_keys(password)
        human_delay()
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        human_delay(5.0, 8.0)
        
        # 验证是否登录成功(可能需要处理人机验证)
        if "tiktok.com/foryou" in driver.current_url:
            log_activity("✅ TikTok登录成功！")
            return True
        else:
            log_activity("⚠️ TikTok可能登录失败或需要验证，请检查...", "WARNING")
            return False
            
    except Exception as e:
        log_activity(f"❌ TikTok登录过程出错: {e}", "ERROR")
        return False

# 6. Reddit 自动化
def login_reddit(username, password):
    log_activity(f"正在登录Reddit账号: {username}...")
    driver.get("https://www.reddit.com/login/")
    human_delay(2.0, 3.0)
    
    try:
        # 输入用户名密码
        driver.find_element(By.ID, "loginUsername").send_keys(username)
        human_delay(0.5, 1.0)
        driver.find_element(By.ID, "loginPassword").send_keys(password)
        human_delay(0.5, 1.0)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        human_delay(5.0, 8.0)  # 登录后等待较长时间
        
        # 处理可能出现的弹窗
        try:
            # 处理 "允许通知" 弹窗
            notification_button = driver.find_element(By.XPATH, "//button[text()='不允许' or text()='Cancel' or text()='Not Now']")
            notification_button.click()
            human_delay()
        except Exception as e:
            log_activity(f"未出现通知弹窗或处理失败: {e}")
        
        # 验证是否登录成功
        if "reddit.com" in driver.current_url and not "login" in driver.current_url:
            log_activity("✅ Reddit登录成功！")
            return True
        else:
            log_activity("⚠️ Reddit可能登录失败，请检查...", "WARNING")
            return False
            
    except Exception as e:
        log_activity(f"❌ Reddit登录过程出错: {e}", "ERROR")
        return False

# 7. OK.ru (Odnoklassniki) 自动化
def login_okru(username, password):
    log_activity(f"正在登录OK.ru账号: {username}...")
    driver.get("https://ok.ru/dk?st.cmd=anonymMain&st.layer.cmd=PopLayerLoginPhoneEmail")
    human_delay(2.0, 3.0)
    
    try:
        # 输入用户名密码
        driver.find_element(By.ID, "field_email").send_keys(username)
        human_delay(0.5, 1.0)
        driver.find_element(By.ID, "field_password").send_keys(password)
        human_delay(0.5, 1.0)
        driver.find_element(By.XPATH, "//input[@value='登录' or @value='Log in']").click()
        human_delay(5.0, 8.0)  # 登录后等待较长时间
        
        # 验证是否登录成功
        if "ok.ru/feed" in driver.current_url or "ok.ru/profile" in driver.current_url:
            log_activity("✅ OK.ru登录成功！")
            return True
        else:
            log_activity("⚠️ OK.ru可能登录失败，请检查...", "WARNING")
            return False
            
    except Exception as e:
        log_activity(f"❌ OK.ru登录过程出错: {e}", "ERROR")
        return False

# ===== 内容发布功能 =====

# 发布到Instagram
def post_to_instagram(image_path, caption):
    log_activity("开始发布内容到Instagram...")
    try:
        # 点击创建按钮
        create_button = driver.find_element(By.XPATH, "//div[@role='button' and @aria-label='新帖子']")
        create_button.click()
        human_delay(2.0, 3.0)
        
        # 上传图片(需要处理文件上传对话框)
        file_input = driver.find_element(By.XPATH, "//input[@type='file']")
        file_input.send_keys(os.path.abspath(image_path))
        human_delay(3.0, 5.0)
        
        # 点击下一步
        next_button = driver.find_element(By.XPATH, "//button[text()='下一步' or text()='Next']")
        next_button.click()
        human_delay(1.0, 2.0)
        
        # 可能还有一个"下一步"按钮
        try:
            next_button = driver.find_element(By.XPATH, "//button[text()='下一步' or text()='Next']")
            next_button.click()
            human_delay(1.0, 2.0)
        except:
            pass
        
        # 输入文案
        caption_field = driver.find_element(By.XPATH, "//div[@role='textbox']")
        caption_field.click()
        human_delay(0.5, 1.0)
        
        # 逐字输入，模拟真人(防止检测)
        for char in caption:
            caption_field.send_keys(char)
            human_delay(0.01, 0.05)
        
        human_delay(1.0, 2.0)
        
        # 点击分享
        share_button = driver.find_element(By.XPATH, "//button[text()='分享' or text()='Share']")
        share_button.click()
        human_delay(5.0, 8.0)
        
        # 验证是否发布成功
        if "instagram.com/p/" in driver.current_url or "instagram.com" in driver.current_url:
            log_activity("✅ Instagram内容发布成功！")
            return True
        else:
            log_activity("⚠️ Instagram内容可能发布失败，请检查...", "WARNING")
            return False
            
    except Exception as e:
        log_activity(f"❌ Instagram发布过程出错: {e}", "ERROR")
        return False

# 发布到Facebook
def post_to_facebook(image_path, caption):
    log_activity("开始发布内容到Facebook...")
    try:
        # 确保在主页
        driver.get("https://www.facebook.com/")
        human_delay(2.0, 3.0)
        
        # 点击"创建帖子"框
        create_post = driver.find_element(By.XPATH, "//span[text()='创建帖子' or text()='Create post' or text()='写点什么' or text()='What\\'s on your mind']")
        create_post.click()
        human_delay(2.0, 3.0)
        
        # 输入文案
        post_box = driver.find_element(By.XPATH, "//div[@role='textbox' and @contenteditable='true']")
        
        # 逐字输入，模拟真人
        for char in caption:
            post_box.send_keys(char)
            human_delay(0.01, 0.05)
        
        human_delay(1.0, 2.0)
        
        # 添加图片
        add_photo = driver.find_element(By.XPATH, "//div[@aria-label='照片/视频' or @aria-label='Photo/Video']")
        add_photo.click()
        human_delay(1.0, 2.0)
        
        # 上传图片
        file_input = driver.find_element(By.XPATH, "//input[@type='file']")
        file_input.send_keys(os.path.abspath(image_path))
        human_delay(3.0, 5.0)
        
        # 点击发布
        post_button = driver.find_element(By.XPATH, "//span[text()='发布' or text()='Post']")
        post_button.click()
        human_delay(5.0, 8.0)
        
        log_activity("✅ Facebook内容发布成功！")
        return True
            
    except Exception as e:
        log_activity(f"❌ Facebook发布过程出错: {e}", "ERROR")
        return False

# 发布到Twitter
def post_to_twitter(image_path, caption):
    log_activity("开始发布内容到Twitter...")
    try:
        # 确保在主页
        driver.get("https://twitter.com/home")
        human_delay(3.0, 4.0)
        
        # 点击发推按钮（可能有多种可能的选择器）
        try:
            tweet_button = driver.find_element(By.XPATH, "//a[@data-testid='SideNav_NewTweet_Button']")
            tweet_button.click()
        except:
            try:
                tweet_button = driver.find_element(By.XPATH, "//div[@role='button' and @data-testid='tweetTextarea_0']")
                tweet_button.click()
            except:
                tweet_button = driver.find_element(By.XPATH, "//div[@data-testid='tweetTextarea_0']")
                tweet_button.click()
                
        human_delay(1.0, 2.0)
        
        # 输入文案
        tweet_box = driver.find_element(By.XPATH, "//div[@data-testid='tweetTextarea_0']")
        
        # 逐字输入，模拟真人
        for char in caption:
            tweet_box.send_keys(char)
            human_delay(0.01, 0.05)
        
        human_delay(1.0, 2.0)
        
        # 添加图片
        media_button = driver.find_element(By.XPATH, "//div[@data-testid='imageOrGifImage']")
        media_button.click()
        human_delay(1.0, 2.0)
        
        # 上传图片
        file_input = driver.find_element(By.XPATH, "//input[@type='file' and @accept='image/jpeg,image/png,image/webp,image/gif']")
        file_input.send_keys(os.path.abspath(image_path))
        human_delay(3.0, 5.0)
        
        # 点击发布
        post_button = driver.find_element(By.XPATH, "//div[@data-testid='tweetButton']")
        post_button.click()
        human_delay(3.0, 5.0)
        
        log_activity("✅ Twitter内容发布成功！")
        return True
            
    except Exception as e:
        log_activity(f"❌ Twitter发布过程出错: {e}", "ERROR")
        return False

# 发布到Reddit
def post_to_reddit(image_path, caption):
    log_activity("开始发布内容到Reddit...")
    try:
        # 确保在主页
        driver.get("https://www.reddit.com/")
        human_delay(2.0, 3.0)
        
        # 点击创建帖子按钮
        create_post = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Create Post') or contains(text(), '创建帖子')]")
        create_post.click()
        human_delay(2.0, 3.0)
        
        # 选择一个子社区
        try:
            # 点击选择子社区
            community_selector = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Choose a community') or contains(@placeholder, '选择社区')]")
            community_selector.click()
            human_delay(1.0, 2.0)
            
            # 选择第一个推荐的社区
            first_community = driver.find_element(By.XPATH, "//div[contains(@role, 'option')]")
            first_community.click()
            human_delay(1.0, 2.0)
        except Exception as e:
            log_activity(f"选择社区过程出错，尝试继续: {e}", "WARNING")
        
        # 选择图片发布模式
        image_tab = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Image') or contains(text(), '图片')]")
        image_tab.click()
        human_delay(1.0, 2.0)
        
        # 输入标题
        title_field = driver.find_element(By.XPATH, "//textarea[contains(@placeholder, 'Title') or contains(@placeholder, '标题')]")
        for char in caption.split('\n')[0][:300]:  # 使用第一行作为标题，Reddit标题有长度限制
            title_field.send_keys(char)
            human_delay(0.01, 0.03)
        
        # 上传图片
        file_input = driver.find_element(By.XPATH, "//input[@type='file']")
        file_input.send_keys(os.path.abspath(image_path))
        human_delay(3.0, 5.0)
        
        # 发布
        post_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Post') or contains(text(), '发布')]")
        post_button.click()
        human_delay(5.0, 8.0)
        
        # 验证是否发布成功
        if "/comments/" in driver.current_url:
            log_activity("✅ Reddit内容发布成功！")
            return True
        else:
            log_activity("⚠️ Reddit内容可能发布失败，请检查...", "WARNING")
            return False
            
    except Exception as e:
        log_activity(f"❌ Reddit发布过程出错: {e}", "ERROR")
        return False

# 发布到OK.ru
def post_to_okru(image_path, caption):
    log_activity("开始发布内容到OK.ru...")
    try:
        # 确保在主页
        driver.get("https://ok.ru/feed")
        human_delay(2.0, 3.0)
        
        # 点击创建帖子
        create_post = driver.find_element(By.XPATH, "//div[contains(@data-action, 'text') or contains(@data-module, 'postingForm/mediaMentions')]")
        create_post.click()
        human_delay(2.0, 3.0)
        
        # 输入文案
        post_textarea = driver.find_element(By.XPATH, "//div[contains(@class, 'posting_itx')]")
        
        # 逐字输入，模拟真人
        for char in caption:
            post_textarea.send_keys(char)
            human_delay(0.01, 0.05)
        
        human_delay(1.0, 2.0)
        
        # 添加图片
        photo_button = driver.find_element(By.XPATH, "//input[@name='photo']")
        photo_button.send_keys(os.path.abspath(image_path))
        human_delay(3.0, 5.0)
        
        # 点击发布
        post_button = driver.find_element(By.XPATH, "//button[contains(@data-action, 'submit') or contains(text(), '分享')]")
        post_button.click()
        human_delay(5.0, 8.0)
        
        log_activity("✅ OK.ru内容发布成功！")
        return True
            
    except Exception as e:
        log_activity(f"❌ OK.ru发布过程出错: {e}", "ERROR")
        return False

# ===== 配置管理功能 =====

# 加载配置文件
def load_config(config_file="config.json"):
    """
    从配置文件加载设置
    config_file: 配置文件路径
    返回: 配置字典
    """
    config_path = os.path.join("credentials", config_file)
    
    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        # 默认配置
        default_config = {
            "accounts": {
                "instagram": [],
                "facebook": [],
                "twitter": [],
                "vk": [],
                "tiktok": [],
                "reddit": [],
                "okru": []
            },
            "topics": ["旅行", "美食", "科技", "生活方式", "健康", "时尚"],
            "post_frequency": {
                "instagram": 24,  # 小时
                "facebook": 48,
                "twitter": 8,
                "vk": 48,
                "tiktok": 24,
                "reddit": 12,
                "okru": 36
            },
            "proxy": ""  # 代理设置
        }
        
        # 创建配置文件
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        
        log_activity(f"已创建默认配置文件: {config_path}")
        return default_config
    
    # 加载配置
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        log_activity(f"已加载配置: {config_path}")
        return config
    except Exception as e:
        log_activity(f"加载配置失败: {str(e)}", "ERROR")
        return None

# 保存账号信息
def save_account(platform, username, password):
    """
    保存账号信息到配置文件
    platform: 平台名称
    username: 用户名
    password: 密码
    """
    config = load_config()
    if not config:
        return False
    
    # 检查账号是否已存在
    for account in config["accounts"].get(platform, []):
        if account.get("username") == username:
            account["password"] = password
            break
    else:
        # 添加新账号
        config["accounts"].setdefault(platform, []).append({
            "username": username,
            "password": password,
            "last_posted": None
        })
    
    # 保存配置
    config_path = os.path.join("credentials", "config.json")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        log_activity(f"已保存{platform}账号: {username}")
        return True
    except Exception as e:
        log_activity(f"保存账号失败: {str(e)}", "ERROR")
        return False

# 选择账号
def select_account(platform, config):
    """
    为指定平台选择一个可用账号
    platform: 平台名称
    config: 配置字典
    返回: (username, password) 元组或 None
    """
    accounts = config["accounts"].get(platform, [])
    if not accounts:
        return None
    
    # 按上次发布时间排序，优先选择最久未发布的账号
    sorted_accounts = sorted(accounts, key=lambda x: x.get("last_posted", "1970-01-01"))
    if sorted_accounts:
        account = sorted_accounts[0]
        return account.get("username"), account.get("password")
    
    return None

# 更新账号发布时间
def update_account_post_time(platform, username):
    """
    更新账号最后发布时间
    platform: 平台名称
    username: 用户名
    """
    config = load_config()
    if not config:
        return False
    
    for account in config["accounts"].get(platform, []):
        if account.get("username") == username:
            account["last_posted"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break
    
    # 保存配置
    config_path = os.path.join("credentials", "config.json")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        log_activity(f"已更新{platform}账号{username}的发布时间")
        return True
    except Exception as e:
        log_activity(f"更新账号发布时间失败: {str(e)}", "ERROR")
        return False

# 随机选择主题
def select_random_topic(config):
    """
    从配置中随机选择一个主题
    config: 配置字典
    返回: 主题字符串
    """
    topics = config.get("topics", ["生活方式"])
    return random.choice(topics)

# ===== 主函数 =====
if __name__ == "__main__":
    log_activity("===== 社交媒体自动化工具 V3.0 =====")
    log_activity("注意：首次运行会自动下载ChromeDriver")
    log_activity("请确保已安装Chrome浏览器")
    
    # 加载配置
    config = load_config()
    if not config:
        log_activity("无法加载配置，程序退出", "ERROR")
        exit(1)
    
    # 选择操作模式
    print("\n请选择操作模式：")
    print("1. 添加/管理账号")
    print("2. 自动生成内容并发布")
    print("3. 设置定时发布")
    print("4. 修改配置")
    print("5. 查看统计数据")
    
    choice = input("请输入选项编号(1-5): ").strip()
    
    if choice == "1":
        # 添加/管理账号
        while True:
            print("\n账号管理：")
            print("1. 添加账号")
            print("2. 查看已有账号")
            print("3. 返回主菜单")
            
            account_choice = input("请输入选项编号(1-3): ").strip()
            
            if account_choice == "1":
                # 添加账号
                platform = input("请输入平台名称(instagram/facebook/twitter/vk/tiktok/reddit/okru): ").strip().lower()
                if platform not in ["instagram", "facebook", "twitter", "vk", "tiktok", "reddit", "okru"]:
                    log_activity(f"不支持的平台: {platform}", "WARNING")
                    continue
                
                username = input(f"请输入{platform}用户名: ").strip()
                password = input(f"请输入{platform}密码: ").strip()
                
                if save_account(platform, username, password):
                    log_activity(f"账号添加成功: {platform}/{username}")
                
            elif account_choice == "2":
                # 查看账号
                log_activity("\n当前配置的账号：")
                for platform, accounts in config["accounts"].items():
                    if accounts:
                        log_activity(f"\n{platform.upper()}:")
                        for i, account in enumerate(accounts, 1):
                            last_posted = account.get("last_posted", "从未")
                            log_activity(f"  {i}. {account['username']} (上次发布: {last_posted})")
                
            elif account_choice == "3":
                # 重新加载配置并返回
                config = load_config()
                break
            
            else:
                log_activity("无效选项，请重新输入", "WARNING")
        
        # 重新提示选择模式
        print("\n请选择操作模式：")
        print("1. 添加/管理账号 (刚才已完成)")
        print("2. 自动生成内容并发布")
        print("3. 设置定时发布")
        print("4. 修改配置")
        print("5. 查看统计数据")
        
        choice = input("请输入选项编号(1-5): ").strip()
    
    if choice == "4":
        # 修改配置
        print("\n配置管理：")
        print("1. 添加/修改主题")
        print("2. 修改发布频率")
        print("3. 返回主菜单")
        
        config_choice = input("请输入选项编号(1-3): ").strip()
        
        if config_choice == "1":
            # 显示当前主题
            current_topics = ", ".join(config["topics"])
            log_activity(f"当前主题: {current_topics}")
            
            # 添加/修改主题
            new_topic = input("请输入要添加的主题(多个主题用逗号分隔): ").strip()
            if new_topic:
                new_topics = [t.strip() for t in new_topic.split(",")]
                config["topics"].extend([t for t in new_topics if t])
                
                # 去重
                config["topics"] = list(set(config["topics"]))
                
                # 保存配置
                config_path = os.path.join("credentials", "config.json")
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                
                log_activity(f"主题已更新: {', '.join(config['topics'])}")
        
        elif config_choice == "2":
            # 显示当前频率
            log_activity("当前发布频率（小时）：")
            for platform, hours in config["post_frequency"].items():
                log_activity(f"{platform}: {hours}小时")
            
            # 修改频率
            platform = input("请输入要修改的平台名称(instagram/facebook/twitter/vk/tiktok/reddit/okru): ").strip().lower()
            if platform in config["post_frequency"]:
                hours = input(f"请输入{platform}的发布频率（小时）: ").strip()
                try:
                    hours = int(hours)
                    if hours > 0:
                        config["post_frequency"][platform] = hours
                        
                        # 保存配置
                        config_path = os.path.join("credentials", "config.json")
                        with open(config_path, "w", encoding="utf-8") as f:
                            json.dump(config, f, ensure_ascii=False, indent=4)
                        
                        log_activity(f"{platform}发布频率已更新: {hours}小时")
                    else:
                        log_activity("频率必须大于0", "WARNING")
                except:
                    log_activity("请输入有效的数字", "WARNING")
        
        # 重新加载配置
        config = load_config()
        
        # 重新提示选择模式
        print("\n请选择操作模式：")
        print("1. 添加/管理账号")
        print("2. 自动生成内容并发布 (建议选择)")
        print("3. 设置定时发布")
        print("4. 修改配置 (刚才已完成)")
        print("5. 查看统计数据")
        
        choice = input("请输入选项编号(1-5): ").strip()
    
    if choice == "2":
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            log_activity("✅ 浏览器初始化成功")
        except Exception as e:
            log_activity(f"❌ 浏览器初始化失败: {e}", "ERROR")
            log_activity("请确保已安装Chrome浏览器并重试")
            exit(1)
        
        # 选择要使用的平台
        available_platforms = [p for p, accounts in config["accounts"].items() if accounts]
        
        if not available_platforms:
            log_activity("没有配置任何账号，请先添加账号", "WARNING")
            driver.quit()
            exit(1)
        
        print("\n可用平台：")
        for i, platform in enumerate(available_platforms, 1):
            account_count = len(config["accounts"][platform])
            log_activity(f"{i}. {platform} ({account_count}个账号)")
        
        selected_platforms = input("请选择要发布的平台编号(多个用逗号分隔，全部请输入'all'): ").strip()
        
        # 处理选择
        if selected_platforms.lower() == 'all':
            platforms_to_use = available_platforms
        else:
            try:
                indices = [int(i.strip()) - 1 for i in selected_platforms.split(",")]
                platforms_to_use = [available_platforms[i] for i in indices if 0 <= i < len(available_platforms)]
            except:
                log_activity("选择无效，将使用所有可用平台", "WARNING")
                platforms_to_use = available_platforms
        
        # 设置主题
        use_random_topic = input("是否使用随机主题？(y/n): ").strip().lower() == 'y'
        if use_random_topic:
            topic = select_random_topic(config)
            log_activity(f"已随机选择主题: {topic}")
        else:
            topic = input("请输入要发布的内容主题: ").strip()
            if not topic:
                topic = select_random_topic(config)
                log_activity(f"未输入主题，已随机选择: {topic}")
        
        # 为主题下载图片
        image_path = download_image(topic)
        if not image_path:
            log_activity("无法下载图片，请检查网络连接", "ERROR")
            image_path = input("请输入图片路径（留空则退出）: ")
            if not image_path:
                driver.quit()
                exit(1)
        
        # 生成文案
        captions = {}
        for platform in platforms_to_use:
            length = "long" if platform in ["facebook", "vk"] else "short"
            captions[platform] = generate_caption(platform, topic, length)
        
        # 依次登录选择的平台并发布
        login_results = {}
        publish_results = {}
        
        for platform in platforms_to_use:
            # 选择账号
            account = select_account(platform, config)
            if not account:
                log_activity(f"未找到{platform}可用账号", "WARNING")
                continue
            
            username, password = account
            log_activity(f"使用{platform}账号: {username}")
            
            # 登录
            login_func = globals().get(f"login_{platform}")
            if login_func:
                login_results[platform] = login_func(username, password)
                human_delay(2.0, 4.0)
            else:
                log_activity(f"未找到{platform}登录函数", "ERROR")
                continue
            
            # 如果登录成功，发布内容
            if login_results.get(platform, False):
                log_activity(f"已为{platform}生成文案：\n{captions[platform]}")
                
                # 发布
                publish_func = globals().get(f"post_to_{platform}")
                if publish_func:
                    publish_results[platform] = publish_func(image_path, captions[platform])
                    if publish_results[platform]:
                        # 更新账号发布时间
                        update_account_post_time(platform, username)
                else:
                    log_activity(f"未找到{platform}发布函数", "ERROR")
            
            # 如果配置了多个账号，切换账号前进行清理
            if len(config["accounts"][platform]) > 1:
                # 清理Cookies
                driver.delete_all_cookies()
                human_delay(1.0, 2.0)
        
        # 输出结果汇总
        log_activity("\n===== 操作结果汇总 =====")
        for platform in platforms_to_use:
            login_status = "✅ 成功" if login_results.get(platform, False) else "❌ 失败"
            publish_status = "✅ 成功" if publish_results.get(platform, False) else "❌ 失败"
            log_activity(f"{platform}: 登录 {login_status} | 发布 {publish_status}")
        
        # 保存会话信息到JSON文件
        session_info = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topic": topic,
            "image_path": image_path,
            "captions": captions,
            "login_results": {k: "成功" if v else "失败" for k, v in login_results.items()},
            "publish_results": {k: "成功" if v else "失败" for k, v in publish_results.items()}
        }
        
        session_file = os.path.join("logs", f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_info, f, ensure_ascii=False, indent=2)
        
        log_activity(f"会话信息已保存至: {session_file}")
        log_activity("\n所有平台操作已完成！")
        
        input("按回车键退出程序...")
        
        # 关闭浏览器
        driver.quit()
    
    elif choice == "3":
        # 设置定时发布
        print("\n定时发布设置：")
        
        # 选择要使用的平台
        available_platforms = [p for p, accounts in config["accounts"].items() if accounts]
        
        if not available_platforms:
            log_activity("没有配置任何账号，请先添加账号", "WARNING")
            exit(1)
        
        print("\n可用平台：")
        for i, platform in enumerate(available_platforms, 1):
            account_count = len(config["accounts"][platform])
            log_activity(f"{i}. {platform} ({account_count}个账号)")
        
        selected_platforms = input("请选择要发布的平台编号(多个用逗号分隔，全部请输入'all'): ").strip()
        
        # 处理选择
        if selected_platforms.lower() == 'all':
            platforms_to_use = available_platforms
        else:
            try:
                indices = [int(i.strip()) - 1 for i in selected_platforms.split(",")]
                platforms_to_use = [available_platforms[i] for i in indices if 0 <= i < len(available_platforms)]
            except:
                log_activity("选择无效，将使用所有可用平台", "WARNING")
                platforms_to_use = available_platforms
        
        # 设置发布时间
        use_random_time = input("是否使用平台推荐的发布频率？(y/n): ").strip().lower() == 'y'
        
        if use_random_time:
            delay_hours = None
            log_activity("将使用平台推荐的发布频率，并添加随机偏移量")
        else:
            try:
                hours = float(input("请输入延迟发布时间（小时）: ").strip())
                delay_hours = hours
            except:
                log_activity("输入无效，将使用平台推荐的发布频率", "WARNING")
                delay_hours = None
        
        # 设置代理（如果需要）
        use_proxy = input("是否使用代理？(y/n): ").strip().lower() == 'y'
        if use_proxy:
            proxy = input("请输入代理地址(如http://127.0.0.1:8080或socks5://127.0.0.1:9050): ").strip()
            config["proxy"] = proxy
            
            # 保存配置
            config_path = os.path.join("credentials", "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            log_activity(f"代理设置已保存: {proxy}")
        
        # 设置定时任务
        if schedule_post(config, platforms_to_use, delay_hours):
            log_activity("定时发布任务已设置，程序将在后台运行")
            log_activity("请勿关闭此窗口，可以最小化")
            log_activity("按Ctrl+C终止程序")
            
            try:
                # 保持程序运行
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                log_activity("程序已终止")
    
    elif choice == "5":
        # 查看统计数据
        stats_summary = get_stats_summary()
        print("\n" + stats_summary + "\n")
        
        detailed_view = input("是否查看详细统计？(y/n): ").strip().lower() == 'y'
        if detailed_view:
            stats_file = os.path.join("stats", "post_stats.json")
            if os.path.exists(stats_file):
                try:
                    with open(stats_file, "r", encoding="utf-8") as f:
                        stats = json.load(f)
                    
                    # 平台统计
                    for platform, platform_stats in stats.items():
                        if platform == "global" or platform == "last_updated":
                            continue
                        
                        print(f"\n==== {platform.upper()} 统计 ====")
                        for username, user_stats in platform_stats.items():
                            success_rate = 0
                            if user_stats["total"] > 0:
                                success_rate = (user_stats["success"] / user_stats["total"]) * 100
                            
                            print(f"用户: {username}")
                            print(f"- 总发布次数: {user_stats['total']}")
                            print(f"- 成功次数: {user_stats['success']}")
                            print(f"- 失败次数: {user_stats['failed']}")
                            print(f"- 成功率: {success_rate:.2f}%")
                            
                            # 主题统计
                            if user_stats["topics"]:
                                top_topics = sorted(user_stats["topics"].items(), key=lambda x: x[1], reverse=True)[:3]
                                print("- 热门主题:")
                                for topic, count in top_topics:
                                    print(f"  * {topic}: {count}次")
                            
                            print()
                
                except Exception as e:
                    log_activity(f"统计数据读取失败: {str(e)}", "ERROR")
            else:
                log_activity("暂无详细统计数据", "INFO")
    
    log_activity("程序已退出。") 