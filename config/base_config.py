# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# 基础配置
PLATFORM = "tk"  # 平台，xhs | dy | ks | bili | wb | tieba | zhihu | tk
KEYWORDS = "俄罗斯地震海啸"  # 关键词搜索配置，以英文逗号分隔
LOGIN_TYPE = "cookie"  # qrcode or phone or cookie
COOKIES = "tt_csrf_token=XcbbQX7O-FiK5MXQOVJgFW7Eq_g1M_o5sNbs; tt_chain_token=ffXIcZzluaz5ecmOei4QZA==; passport_csrf_token=ca6669bcf43a6310ab3f09e0745f3297; passport_csrf_token_default=ca6669bcf43a6310ab3f09e0745f3297; s_v_web_id=verify_mdmrfn28_HfDOlSEX_708h_4CDh_8OwE_tkEJDeH40uHP; multi_sids=7531958306765521927%3A5bef2c168966af3c3b34eae57d368b26; cmpl_token=AgQQAPOHF-RO0ri4CosB_R0-8uaGjWMb_4UMYN5ksQ; passport_auth_status=0b11cca5321cacfd235360ddb9501fb6%2C; passport_auth_status_ss=0b11cca5321cacfd235360ddb9501fb6%2C; uid_tt=12174a4541360a8a21887b0ca7e11f7c8f485f3e7b0e2865e6ca1a377704dbd5; uid_tt_ss=12174a4541360a8a21887b0ca7e11f7c8f485f3e7b0e2865e6ca1a377704dbd5; sid_tt=5bef2c168966af3c3b34eae57d368b26; sessionid=5bef2c168966af3c3b34eae57d368b26; sessionid_ss=5bef2c168966af3c3b34eae57d368b26; store-idc=maliva; store-country-code=tw; store-country-code-src=uid; tt-target-idc=alisg; tt-target-idc-sign=YCzkGUtvoxt1hPy7FBtpqFWFQK1w4lILOgAxou0p3yYo4XmJ8OjPe_mlcgxgPLhhDCBDe6HI_gAyekf8WBktCZkK-1Iy6eSGVJfU1K110u8rW5yz6g9XcEX2lwGJskjUahSc6t997V4pN55NrNMIy0c6FouQY4aARB_YcUji2CV0BpMHMvpc1uwLe-FqYXo4RD7mFXjUmt9VTAhQzKJP9SDi0muz2kNa_kO2O9mEhmwQAXgD0bv-z78dqL4kehrtG4xg2wVrxlRyQb8b7j5wW0-vEt7K6fIR6TCpP6HN6SsCo8HJqvYwdJ8NmePsRQhY1-iENtmdSaQKqmJeCAFoJ_HtJmArSz2X8SxRk3PxYpvVcSSW4mVLIP-_nxhSqGuq5aWlFnWUyTAEWwWmJxAtlajoF-hHSYopTnIBDeVamrv92lmZeqVBbUgh-RUhDN03lARxSBVJ-pm3WyhysY-4rlqhHByHkq3NJJB0zhBFA3ILE0wqZSBWRTSfm5F8HOdL; ttwid=1%7CHnYXhYGPBXgrkDeCtfCOPVXMA8X1M0Kzz-XNld0W4Is%7C1753686123%7C134c9b12d19b8125faddbcfef4f35e82c53f2fefe08bb17429a1be2c874e44cc; store-country-sign=MEIEDACrwBkOKlP9S-HU0gQgsr_9d1v_FDrUFcumYL8wsKWvak7xp2ZGYkC1jl080cIEEJyKO9Jj1K2eGXAsjVQyqek; sid_guard=5bef2c168966af3c3b34eae57d368b26%7C1753686123%7C15551996%7CSat%2C+24-Jan-2026+07%3A01%3A59+GMT; sid_ucp_v1=1.0.0-KDdlNWY4ZGRhY2I4ZjlkNDU3OWNlNjRkNWU4YzQ1OWQyNThkNWZmNjIKGQiHiL_OyIW5w2gQ68CcxAYYsws4CEASSAQQAxoCbXkiIDViZWYyYzE2ODk2NmFmM2MzYjM0ZWFlNTdkMzY4YjI2; ssid_ucp_v1=1.0.0-KDdlNWY4ZGRhY2I4ZjlkNDU3OWNlNjRkNWU4YzQ1OWQyNThkNWZmNjIKGQiHiL_OyIW5w2gQ68CcxAYYsws4CEASSAQQAxoCbXkiIDViZWYyYzE2ODk2NmFmM2MzYjM0ZWFlNTdkMzY4YjI2; odin_tt=9bb2dd0d968b6c7d04b1b975f3ec6b47f7c9cdaff92c07774097788ecee32b680dfc03ada00588b40cb2d6872306a3620bf1fd90510bbd780d70b60ea1725b26ac913468871172e6b5df8ba7996d0b39; msToken=lV6hydyAZ7LrNV6FVkA1ewlBxILsLYPXWSViCi_aoKO7wgy0tqMbRuys9xM9wwb_u1fnQejM7MLPhg6Ntpf6r95yF4lQW0xKHxV4DnAvAFencXnngjQLE9hcZdgTfur3dz2CQww4DdEaDorIajGfBE0Q7A=="
CRAWLER_TYPE = (
    "detail"  # 爬取类型，search(关键词搜索) | detail(帖子详情)| creator(创作者主页数据)
)
# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "kuaidaili"

# 设置为True不会打开浏览器（无头浏览器）
# 设置False会打开一个浏览器
# 小红书如果一直扫码登录不通过，打开浏览器手动过一下滑动验证码
# 抖音如果一直提示失败，打开浏览器看下是否扫码登录之后出现了手机号验证，如果出现了手动过一下再试。
HEADLESS = False

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# ==================== CDP (Chrome DevTools Protocol) 配置 ====================
# 是否启用CDP模式 - 使用用户现有的Chrome/Edge浏览器进行爬取，提供更好的反检测能力
# 启用后将自动检测并启动用户的Chrome/Edge浏览器，通过CDP协议进行控制
# 这种方式使用真实的浏览器环境，包括用户的扩展、Cookie和设置，大大降低被检测的风险
ENABLE_CDP_MODE = True

# CDP调试端口，用于与浏览器通信
# 如果端口被占用，系统会自动尝试下一个可用端口
CDP_DEBUG_PORT = 9222

# 自定义浏览器路径（可选）
# 如果为空，系统会自动检测Chrome/Edge的安装路径
# Windows示例: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# macOS示例: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CUSTOM_BROWSER_PATH = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"

# CDP模式下是否启用无头模式
# 注意：即使设置为True，某些反检测功能在无头模式下可能效果不佳
CDP_HEADLESS = False

# 浏览器启动超时时间（秒）
BROWSER_LAUNCH_TIMEOUT = 30

# 是否在程序结束时自动关闭浏览器
# 设置为False可以保持浏览器运行，便于调试
AUTO_CLOSE_BROWSER = True

# 数据保存类型选项配置,支持四种类型：csv、db、json、sqlite, 最好保存到DB，有排重的功能。
SAVE_DATA_OPTION = "json"  # csv or db or json or sqlite

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 爬取开始页数 默认从第一页开始
START_PAGE = 1

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 20

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 1

# 是否开启爬图片模式, 默认不开启爬图片
ENABLE_GET_IMAGES = False

# 是否开启爬视频模式, 默认不开启爬图片
ENABLE_GET_VIDEOS = True

# 是否开启爬评论模式, 默认开启爬评论
ENABLE_GET_COMMENTS = True

# 爬取一级评论的数量控制(单视频/帖子)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# 是否开启爬二级评论模式, 默认不开启爬二级评论
# 老版本项目使用了 db, 则需参考 schema/tables.sql line 287 增加表字段
ENABLE_GET_SUB_COMMENTS = False

# 词云相关
# 是否开启生成评论词云图
ENABLE_GET_WORDCLOUD = False
# 自定义词语及其分组
# 添加规则：xx:yy 其中xx为自定义添加的词组，yy为将xx该词组分到的组名。
CUSTOM_WORDS = {
    "零几": "年份",  # 将“零几”识别为一个整体
    "高频词": "专业术语",  # 示例自定义词
}

# 停用(禁用)词文件路径
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# 中文字体文件路径
FONT_PATH = "./docs/STZHONGS.TTF"

# 爬取间隔时间
CRAWLER_MAX_SLEEP_SEC = 2

from .bilibili_config import *
from .xhs_config import *
from .dy_config import *
from .ks_config import *
from .weibo_config import *
from .tieba_config import *
from .zhihu_config import *
from .tiktok_config import *
