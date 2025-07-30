# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

import config
from base.base_crawler import AbstractLogin
from tools import utils


class TikTokLogin(AbstractLogin):
    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 cookie_str: str = ""
                 ):
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.cookie_str = cookie_str

    async def begin(self):
        """Start login TikTok"""
        utils.logger.info("[TikTokLogin.begin] Begin login TikTok ...")
        if self.login_type == "qrcode":
            await self.login_by_qrcode()
        elif self.login_type == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError("[TikTokLogin.begin] Invalid Login Type Currently only supported qrcode or cookie ...")

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        """Check if the current login status is successful"""
        current_cookies = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookies)
        # 检查关键的登录cookies
        return "sessionid_ss" in cookie_dict and "tt_chain_token" in cookie_dict

    async def login_by_qrcode(self):
        """Login TikTok by scanning a QR code"""
        utils.logger.info("[TikTokLogin.login_by_qrcode] Begin login TikTok by qrcode ...")

        login_button = self.context_page.get_by_test_id("header-login-button")
        if await login_button.is_visible():
            await login_button.click()
            await self.context_page.wait_for_selector("iframe[data-tt='LoginIframe']", state="visible", timeout=15000)

        login_iframe = self.context_page.frame_locator("iframe[data-tt='LoginIframe']")

        qr_code_div = login_iframe.locator("div[data-e2e='qr-code']")
        await qr_code_div.wait_for(state="visible", timeout=15000)

        screenshot = await qr_code_div.screenshot()
        base64_qrcode_img = utils.base64.b64encode(screenshot).decode('utf-8')

        partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
        asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)

        utils.logger.info("[TikTokLogin.login_by_qrcode] Waiting for scan code login...")
        try:
            await self.check_login_state()
        except RetryError:
            utils.logger.error("[TikTokLogin.login_by_qrcode] Login TikTok failed by qrcode login method.")
            sys.exit()

        utils.logger.info("[TikTokLogin.login_by_qrcode] Login successful!")

    async def login_by_mobile(self):
        pass

    async def login_by_cookies(self):
        utils.logger.info("[TikTokLogin.login_by_cookies] Begin login TikTok by cookie ...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                'name': key, 'value': value, 'domain': ".tiktok.com", 'path': "/"
            }])