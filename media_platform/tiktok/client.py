import asyncio
import json
from typing import Dict, Optional, Any
from playwright.async_api import BrowserContext, Page, Response

from base.base_crawler import AbstractApiClient
from tools import utils


class TikTokClient(AbstractApiClient):
    def __init__(
            self,
            proxies: Optional[Dict] = None,
            headers: Dict = None,
            playwright_page: Page = None,
            cookie_dict: Dict = None,
    ):
        self.proxies = proxies
        self.headers = headers
        self._host = "https://www.tiktok.com"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict or {}

    async def request(self, method, url, **kwargs):
        raise NotImplementedError("Direct requests are not used in this implementation.")

    async def pong(self, browser_context: BrowserContext) -> bool:
        _, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        return "sessionid_ss" in cookie_dict and "tt_chain_token" in cookie_dict

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def get_video_by_id(self, video_id: str) -> Optional[Dict]:
        """
       通过导航到视频详情页，捕获返回视频数据的API响应
       """
        api_url_pattern = "/api/video/detail/"
        user_name = self.cookie_dict.get('user_unique_id', 'tiktok')
        video_url = f"{self._host}/@{user_name}/video/{video_id}"
        utils.logger.info(f"[TikTokClient] Navigating to {video_url} to capture video detail...")

        async def handler(response: Response) -> Optional[Dict]:
            if api_url_pattern in response.url and response.request.method == "POST":
                try:
                    data = await response.json()
                    if data.get("statusCode") == 0 and "itemInfo" in data:
                        utils.logger.info(f"✅ Successfully captured video detail for ID: {video_id}")
                        return data["itemInfo"]["itemStruct"]
                except Exception as e:
                    utils.logger.warning(f"⚠️ Failed to parse video detail response from {response.url}: {e}")
            return None

        return await self._navigate_and_capture_response(video_url, handler)

    async def get_video_by_id_not_creator(self, video_url: str, video_id: str) -> Optional[Dict]:
        """
        通过导航到视频详情页，并从页面嵌入的 __UNIVERSAL_DATA_FOR_REHYDRATION__ JSON中提取数据
        """
        utils.logger.info(f"[TikTokClient] Fetching video info from page: {video_url}")
        try:
            await self.playwright_page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
            script_selector = "script#__UNIVERSAL_DATA_FOR_REHYDRATION__"
            await self.playwright_page.wait_for_selector(script_selector, state="attached", timeout=15000)

            if await self.playwright_page.locator(script_selector).count() > 0:
                script_content = await self.playwright_page.locator(script_selector).inner_text()
                if script_content:
                    data = json.loads(script_content)
                    video_detail_data = data.get("__DEFAULT_SCOPE__", {}).get("webapp.video-detail", {})
                    item_struct = video_detail_data.get("itemInfo", {}).get("itemStruct")

                    if item_struct and item_struct.get("id") == video_id:
                        utils.logger.info(f"✅ Successfully extracted video info for '{video_id}' from embedded page JSON.")
                        return item_struct
                    else:
                        utils.logger.warning(f"Could not find video '{video_id}' in embedded JSON data.")
            else:
                utils.logger.warning(f"Could not find script#__UNIVERSAL_DATA_FOR_REHYDRATION__ on page: {video_url}")
        except Exception as e:
            utils.logger.error(f"❌ Error fetching or parsing video detail page for {video_id}: {e}")
        return None

    async def get_creator_info_by_id(self, creator_id: str) -> Optional[Dict]:
        """
        通过导航到创作者主页，从页面嵌入的 __UNIVERSAL_DATA_FOR_REHYDRATION__ JSON数据中提取信息。
        """
        creator_url = f"{self._host}/@{creator_id}"
        utils.logger.info(f"[TikTokClient] Fetching creator info from page: {creator_url}")

        try:
            await self.playwright_page.goto(creator_url, wait_until="domcontentloaded", timeout=30000)

            # 使用你找到的正确选择器
            script_selector = "script#__UNIVERSAL_DATA_FOR_REHYDRATION__"

            if await self.playwright_page.locator(script_selector).count() > 0:
                script_content = await self.playwright_page.locator(script_selector).inner_text()
                if script_content:
                    data = json.loads(script_content)

                    # 使用你找到的正确数据路径
                    default_scope = data.get("__DEFAULT_SCOPE__", {})
                    user_detail_data = default_scope.get("webapp.user-detail", {})
                    user_info = user_detail_data.get("userInfo")

                    if user_info and user_info.get("user", {}).get("uniqueId") == creator_id:
                        utils.logger.info(
                            f"✅ Successfully extracted creator info for '{creator_id}' from embedded page JSON.")
                        return user_info
                    else:
                        utils.logger.warning(f"Could not find creator '{creator_id}' in embedded JSON data.")
            else:
                utils.logger.warning(f"Could not find script#__UNIVERSAL_DATA_FOR_REHYDRATION__ on page: {creator_url}")

        except Exception as e:
            utils.logger.error(f"❌ Error fetching or parsing creator page for {creator_id}: {e}")

        return None

    async def _navigate_and_capture_response(self, url: str, handler: callable, timeout: int = 30000) -> Optional[Any]:
        """
        一个通用的函数，用于导航到一个URL，并监听网络响应，直到handler函数返回一个有效结果或超时。
        """
        future = asyncio.get_event_loop().create_future()

        async def response_handler(response: Response):
            if not future.done():
                result = await handler(response)
                if result:
                    future.set_result(result)

        self.playwright_page.on("response", response_handler)

        try:
            await self.playwright_page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await asyncio.wait_for(future, timeout=15)
        except asyncio.TimeoutError:
            utils.logger.warning(f"⏰ Timed out waiting for API response from {url}")
            if not future.done():
                future.set_result(None)
        except Exception as e:
            if not future.done():
                utils.logger.error(f"❌ Navigation or capture error for {url}: {e}")
                future.set_result(None)
        finally:
            self.playwright_page.remove_listener("response", response_handler)
        return await future
