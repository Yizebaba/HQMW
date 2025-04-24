import streamlit as st
import streamlit_antd_components as sac
import os
import random
import json

# 加载配置函数
def load_config(config_file="HQMW/credentials/config.json"):
    """加载配置文件"""
    try:
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # 创建默认配置
            default_config = {
                "accounts": {},
                "topics": ["旅行", "美食", "科技", "生活方式", "健康", "时尚"],
                "post_frequency": {
                    "min_hours": 4,
                    "max_hours": 12
                }
            }
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config
    except Exception as e:
        st.error(f"加载配置文件时出错: {str(e)}")
        return None

# 保存账号函数
def save_account(platform, username, password, config_file="HQMW/credentials/config.json"):
    """保存账号信息到配置文件"""
    try:
        config = load_config(config_file)
        if not config:
            return False
        
        # 确保账号部分存在
        if "accounts" not in config:
            config["accounts"] = {}
        
        # 添加账号
        account_info = {
            "username": username,
            "password": password,
            "last_posted": "从未"
        }
        
        config["accounts"].setdefault(platform, []).append(account_info)
        
        # 保存配置
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        st.error(f"保存账号时出错: {str(e)}")
        return False

# 页面设置
st.set_page_config(page_title="社交媒体自动化工具", layout="wide")

# 标题和简介
st.title("✨ 社交媒体自动化工具")
st.markdown("轻松管理多平台社交媒体账号，自动发布内容")

# 使用分割线美化界面
st.markdown("---")

# 加载配置
config = load_config()
if not config:
    st.error("无法加载配置，请检查权限或文件路径")
    st.stop()

# 使用按钮代替主菜单下拉框
st.subheader("请选择操作模式")

# 使用sac.buttons作为主菜单
operation_mode = sac.buttons([
    sac.ButtonsItem(label='添加/管理账号', icon='person-plus-fill'),
    sac.ButtonsItem(label='自动生成内容并发布', icon='send-fill'),
    sac.ButtonsItem(label='设置定时发布', icon='clock-fill'),
    sac.ButtonsItem(label='修改配置', icon='gear-fill'),
    sac.ButtonsItem(label='查看统计数据', icon='graph-up-arrow')
], align='center', format_func='title', size='md', color='blue', return_index=True)

# 根据选择的操作模式显示不同内容
if operation_mode == 0:  # 添加/管理账号
    st.header("添加/管理账号")
    
    # 使用按钮代替平台下拉框
    st.subheader("选择平台")
    platform = sac.buttons([
        sac.ButtonsItem(label='Instagram', icon='instagram'),
        sac.ButtonsItem(label='Facebook', icon='facebook'),
        sac.ButtonsItem(label='Twitter/X', icon='twitter'),
        sac.ButtonsItem(label='VK', icon='chat-fill'),
        sac.ButtonsItem(label='TikTok', icon='music-note'),
        sac.ButtonsItem(label='Reddit', icon='reddit'),
        sac.ButtonsItem(label='OK.ru', icon='person-circle')
    ], index=None, format_func='title', align='start', direction='horizontal', size='sm', color='cyan', return_index=True)
    
    # 根据选择的平台显示账号表单
    if platform is not None:
        platforms = ['Instagram', 'Facebook', 'Twitter/X', 'VK', 'TikTok', 'Reddit', 'OK.ru']
        selected_platform = platforms[platform]
        
        st.write(f"您选择了: {selected_platform}")
        
        # 创建两列布局
        col1, col2 = st.columns(2)
        
        # 账号信息表单
        with col1:
            with st.form(key=f"{selected_platform}_account_form"):
                st.subheader(f"{selected_platform} 账号信息")
                username = st.text_input("用户名")
                password = st.text_input("密码", type="password")
                submit_button = st.form_submit_button("添加账号")
                
                if submit_button:
                    if username and password:
                        if save_account(selected_platform.lower(), username, password):
                            st.success(f"已成功添加 {selected_platform} 账号: {username}")
                        else:
                            st.error("保存账号时出错")
                    else:
                        st.error("请填写所有必填信息")
        
        # 显示账号列表
        with col2:
            st.subheader("已添加的账号")
            accounts = config.get("accounts", {}).get(selected_platform.lower(), [])
            if accounts:
                for i, account in enumerate(accounts, 1):
                    st.info(f"{i}. {account['username']} (上次发布: {account.get('last_posted', '从未')})")
            else:
                st.info("暂无添加的账号")

elif operation_mode == 1:  # 自动生成内容并发布
    st.header("自动生成内容并发布")
    
    # 使用列布局美化界面
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # 使用按钮选择平台
        st.subheader("选择发布平台")
        publish_platforms = sac.checkbox_group([
            sac.CheckboxItem(label='Instagram', icon='instagram'),
            sac.CheckboxItem(label='Facebook', icon='facebook'),
            sac.CheckboxItem(label='Twitter/X', icon='twitter'),
            sac.CheckboxItem(label='其他平台', icon='three-dots')
        ], format_func='title', align='start')
        
        # 使用按钮选择主题
        st.subheader("内容主题")
        theme = sac.buttons([
            sac.ButtonsItem(label='旅行', icon='geo-alt'),
            sac.ButtonsItem(label='美食', icon='cup-hot'),
            sac.ButtonsItem(label='科技', icon='laptop'),
            sac.ButtonsItem(label='生活方式', icon='house-heart'),
            sac.ButtonsItem(label='健康', icon='heart-pulse'),
            sac.ButtonsItem(label='时尚', icon='tag')
        ], format_func='title', direction='horizontal', align='start', size='sm', color='green', return_index=True)
    
    with col2:
        # 图片上传区域
        st.subheader("上传图片 (可选)")
        uploaded_file = st.file_uploader("选择图片", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            st.image(uploaded_file, caption="上传的图片", use_column_width=True)
        else:
            st.info("如果不上传图片，系统将自动生成相关图片")
    
    # 发布按钮
    if st.button("开始发布", type="primary"):
        st.success("内容发布任务已启动！")
        with st.spinner("正在处理中..."):
            # 模拟处理过程
            st.info("这里将集成social_media_auto.py中的发布功能")
            st.info("实际应用中需要将social_media_auto.py重构为可导入的模块")

elif operation_mode == 2:  # 设置定时发布
    st.header("设置定时发布")
    
    st.info("定时发布功能将在后台运行，无需保持浏览器打开")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("选择平台")
        schedule_platforms = sac.checkbox_group([
            sac.CheckboxItem(label='Instagram', icon='instagram'),
            sac.CheckboxItem(label='Facebook', icon='facebook'),
            sac.CheckboxItem(label='Twitter/X', icon='twitter')
        ], format_func='title')
    
    with col2:
        st.subheader("设置发布频率")
        min_hours = st.slider("最小间隔(小时)", 1, 24, 4)
        max_hours = st.slider("最大间隔(小时)", min_hours, 48, 12)
    
    if st.button("设置定时发布", type="primary"):
        # 保存定时设置
        config["post_frequency"] = {
            "min_hours": min_hours,
            "max_hours": max_hours
        }
        
        with open("HQMW/credentials/config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
        st.success("定时发布已设置！")
        st.info(f"系统将在{min_hours}到{max_hours}小时内随机时间发布内容")

elif operation_mode == 3:  # 修改配置
    st.header("修改配置")
    
    tab1, tab2 = st.tabs(["主题管理", "其他设置"])
    
    with tab1:
        st.subheader("内容主题管理")
        
        # 显示现有主题
        st.write("现有主题:")
        topics = config.get("topics", [])
        for topic in topics:
            st.info(topic)
        
        # 添加新主题
        with st.form(key="add_topic_form"):
            new_topic = st.text_input("新主题名称")
            submit_topic = st.form_submit_button("添加主题")
            
            if submit_topic and new_topic:
                if new_topic not in topics:
                    topics.append(new_topic)
                    config["topics"] = topics
                    
                    with open("HQMW/credentials/config.json", "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    
                    st.success(f"已添加主题: {new_topic}")
                else:
                    st.warning("该主题已存在")
    
    with tab2:
        st.subheader("其他设置")
        st.info("更多设置功能正在开发中...")

elif operation_mode == 4:  # 查看统计数据
    st.header("发布统计数据")
    
    # 模拟一些统计数据
    stats_data = {
        "platforms": {
            "instagram": {"success": 12, "failed": 2},
            "facebook": {"success": 8, "failed": 1},
            "twitter": {"success": 15, "failed": 3}
        },
        "topics": {
            "旅行": 10,
            "美食": 8,
            "科技": 6,
            "生活方式": 12
        },
        "timeline": [
            {"date": "2023-10-01", "count": 2},
            {"date": "2023-10-02", "count": 1},
            {"date": "2023-10-03", "count": 3},
            {"date": "2023-10-04", "count": 2},
            {"date": "2023-10-05", "count": 4}
        ]
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("平台发布统计")
        for platform, data in stats_data["platforms"].items():
            success_rate = data["success"] / (data["success"] + data["failed"]) * 100
            st.metric(f"{platform.capitalize()}", f"{data['success']}次成功", f"{success_rate:.1f}% 成功率")
    
    with col2:
        st.subheader("主题分布")
        for topic, count in stats_data["topics"].items():
            st.metric(topic, f"{count}篇")
    
    st.subheader("发布时间线")
    timeline_data = [[item["date"], item["count"]] for item in stats_data["timeline"]]
    timeline_data.insert(0, ["日期", "发布数量"])
    st.line_chart(stats_data["timeline"], x="date", y="count")

# 添加页脚
st.markdown("---")
st.markdown("🔧 社交媒体自动化工具 | 版本 3.0") 