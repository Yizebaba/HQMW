# 社交媒体自动化工具

## 项目描述

这是一个强大的社交媒体自动化工具，可以帮助您管理和自动发布内容到多个社交媒体平台，包括：

- Instagram
- Facebook
- Twitter/X
- VK (VKontakte)
- TikTok
- Reddit
- OK.ru (Odnoklassniki)

该工具支持内容生成、发布调度、多账号管理以及代理设置，大大简化了跨平台社交媒体营销工作。

## 功能特点

- 多平台支持：一次配置，在多个社交媒体平台上发布内容
- 自动生成内容：根据主题自动生成适合不同平台的标题和描述
- 图片下载：根据关键词自动下载相关图片用于发布
- 灵活调度：为不同平台设置不同的发布频率和时间
- 模拟人类行为：引入随机延迟和互动模式，减少被识别为机器人的风险
- 代理支持：通过代理服务器进行连接，提高隐私和安全性
- 详细日志：记录所有操作，便于追踪和分析

## 安装步骤

1. 确保已安装Python 3.8+
2. 克隆仓库或下载源代码
3. 创建虚拟环境（推荐）
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
4. 安装依赖包
   ```
   pip install -r requirements.txt
   ```
5. 下载并配置适合您浏览器的WebDriver（Chrome, Firefox等）

## 使用方法

1. 在credentials文件夹中创建config.json配置文件（首次运行会自动创建）
2. 运行主程序
   ```
   python social_media_auto.py
   ```
3. 使用交互式菜单：
   - 添加和管理社交媒体账号
   - 计划和发布内容
   - 查看发布统计
   - 配置系统设置

## 配置说明

配置文件(config.json)结构如下：

```json
{
    "accounts": {
        "instagram": [{"username": "user1", "password": "pass1"}],
        "facebook": [{"username": "user2", "password": "pass2"}],
        // 其他平台...
    },
    "topics": ["旅行", "美食", "科技", "生活方式", "健康", "时尚"],
    "post_frequency": {
        "instagram": 24,  // 小时
        "facebook": 48,
        // 其他平台...
    },
    "proxy": "http://user:pass@host:port"  // 可选
}
```

## 注意事项

- 请遵守各平台的使用条款和政策
- 避免过度频繁的发布，以免账号受到限制
- 定期更新代理设置，提高安全性
- 保管好您的凭据和配置文件 