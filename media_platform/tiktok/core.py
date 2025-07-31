import asyncio
import os
import random
import urllib.parse
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    Response,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import tiktok as tiktok_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import TikTokClient
from .login import TikTokLogin


class TikTokCrawler(AbstractCrawler):
    context_page: Page
    tk_client: TikTokClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://www.tiktok.com"
        self.cdp_manager = None
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(
                ip_proxy_info
            )

        async with async_playwright() as playwright:
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[TikTokCrawler] Using CDP mode to launch browser")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright, playwright_proxy_format, self.user_agent, headless=config.CDP_HEADLESS
                )
            else:
                utils.logger.info("[TikTokCrawler] Using standard mode to launch browser")
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium, playwright_proxy_format, user_agent=self.user_agent, headless=config.HEADLESS
                )

            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.tk_client = await self.create_tiktok_client(httpx_proxy_format)
            if not await self.tk_client.pong(browser_context=self.browser_context):
                login_obj = TikTokLogin(
                    login_type=config.LOGIN_TYPE,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.tk_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_videos()
            elif config.CRAWLER_TYPE == "creator":
                await self.get_creators_and_videos()

            utils.logger.info("[TikTokCrawler.start] TikTok Crawler finished.")

    async def get_creators_and_videos(self) -> None:
        utils.logger.info("[TikTokCrawler.get_creators_and_videos] Begin getting creators' videos")
        for creator_id in config.TIKTOK_CREATOR_ID_LIST:
            utils.logger.info(f"[TikTokCrawler.get_creators_and_videos] Processing creator: {creator_id}")

            creator_info = await self.tk_client.get_creator_info_by_id(creator_id)

            if creator_info:
                # 传递完整的 creator_info 对象，而不是只传递 creator_info.get("user")
                await tiktok_store.save_creator(creator_info)
            else:
                utils.logger.warning(f"Could not fetch creator info for: {creator_id}")

            creator_url = f"{self.index_url}/@{creator_id}"
            scroll_times = (config.CRAWLER_MAX_NOTES_COUNT // 12) + 1

            video_list = await self._fetch_data_from_browse(
                url=creator_url,
                api_path="/api/post/item_list/",
                scroll_times=scroll_times
            )

            if not video_list:
                utils.logger.warning(f"Could not fetch videos for creator: {creator_id}")
                continue

            video_ids = [item.get("id") for item in video_list if item and item.get("id")]
            for item in video_list:
                await tiktok_store.update_tiktok_video(item)

            await self.batch_get_video_comments(video_ids)

    async def _fetch_data_from_browse(self, url: str, api_path: str, scroll_times: int, page_type: str = "video") -> \
    List[Dict]:
        all_items = []
        seen_ids = set()
        continuous_no_new_data_count = 0

        async def response_handler(response: Response):
            nonlocal continuous_no_new_data_count
            if api_path in response.url and response.status == 200:
                try:
                    data = await response.json()
                    if config.CRAWLER_TYPE == "search":
                        items = data.get("item_list") or data.get("comments") or data.get("items") or []
                    elif config.CRAWLER_TYPE == "detail":
                        items = data.get("itemList") or data.get("comments") or data.get("items") or []
                    elif config.CRAWLER_TYPE == "creator":
                        items = data.get("itemList") or data.get("comments") or data.get("items") or []
                    else:
                        items = data.get("itemList") or data.get("comments") or data.get("items") or []
                    new_items_found = False
                    for item in items:
                        item_id = item.get("id") or item.get("cid")
                        if item_id and item_id not in seen_ids:
                            all_items.append(item)
                            seen_ids.add(item_id)
                            new_items_found = True

                    if new_items_found:
                        utils.logger.info(f"✅ Captured {len(items)} new items from: {response.url}")
                        continuous_no_new_data_count = 0
                    else:
                        utils.logger.info(f"✅ Captured API response from {response.url}, but no new items were found.")

                except Exception:
                    utils.logger.warning(f"⚠️ Failed to parse JSON from: {response.url}")

        self.context_page.on("response", response_handler)

        try:
            await self.context_page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self.context_page.wait_for_timeout(3000)

            for i in range(scroll_times):
                if continuous_no_new_data_count >= 3:
                    utils.logger.info("No new data found after 3 consecutive scrolls. Ending scroll.")
                    break

                if page_type == "comment":
                    comment_selector = 'div[class*="DivCommentListContainer"]'
                    if await self.context_page.locator(comment_selector).count() > 0:
                        await self.context_page.evaluate(
                            f"document.querySelector('{comment_selector}').scrollTop = document.querySelector('{comment_selector}').scrollHeight")
                    else:
                        await self.context_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                else:
                    await self.context_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                utils.logger.info(f"Scrolled down {i + 1}/{scroll_times} times for {url}")
                continuous_no_new_data_count += 1
                await self.context_page.wait_for_timeout(random.randint(2500, 4000))

        except Exception as e:
            utils.logger.error(f"Error while fetching data from {url}: {e}")
        finally:
            self.context_page.remove_listener("response", response_handler)

        return all_items

    async def search(self) -> None:
        utils.logger.info("[TikTokCrawler.search] Begin search TikTok keywords")
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[TikTokCrawler.search] Current keyword: {keyword}")

            search_url = f"{self.index_url}/search/video?q={urllib.parse.quote(keyword)}"
            scroll_times = (config.CRAWLER_MAX_NOTES_COUNT // 12) + 1

            video_list = await self._fetch_data_from_browse(
                url=search_url,
                api_path="/api/search/item/full/",
                scroll_times=scroll_times
            )

            if not video_list:
                utils.logger.warning(f"[TikTokCrawler.search] Did not find any videos for keyword: {keyword}")
                continue

            video_ids = [item.get("id") for item in video_list if item.get("id")]
            for item in video_list:
                await tiktok_store.update_tiktok_video(item)

            await self.batch_get_video_comments(video_ids)

    async def get_specified_videos(self):
        utils.logger.info("[TikTokCrawler.get_specified_videos] Begin fetching specified videos")
        video_ids_to_fetch_comments = []
        for video_url in config.TIKTOK_SPECIFIED_ID_LIST:
            try:
                path_parts = urllib.parse.urlparse(video_url).path.strip('/').split('/')
                video_id = path_parts[2]
                video_detail = await self.tk_client.get_video_by_id(video_id)
                if video_detail:
                    await tiktok_store.update_tiktok_video(video_detail)
                    video_ids_to_fetch_comments.append(video_id)
            except Exception as e:
                utils.logger.error(f"Failed to process specified video URL {video_url}: {e}")
        await self.batch_get_video_comments(video_ids_to_fetch_comments)

    async def batch_get_video_comments(self, video_ids: List[str]):
        if not config.ENABLE_GET_COMMENTS:
            return
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        tasks = [self.get_comments(video_id, semaphore) for video_id in video_ids if video_id]
        if tasks:
            await asyncio.gather(*tasks)

    async def get_comments(self, video_id: str, semaphore: asyncio.Semaphore):
        async with semaphore:
            utils.logger.info(f"[TikTokCrawler.get_comments] Fetching comments for video {video_id}")
            user_unique_id = self.tk_client.cookie_dict.get('user_unique_id', 'tiktok')
            video_url = f"{self.index_url}/@{user_unique_id}/video/{video_id}"

            scroll_times = (config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES // 20) + 1
            comment_list = await self._fetch_data_from_browse(
                url=video_url,
                api_path="/api/comment/list/",
                scroll_times=scroll_times,
                page_type="comment"
            )

            if comment_list:
                await tiktok_store.batch_update_tiktok_video_comments(video_id, comment_list)

    async def create_tiktok_client(self, httpx_proxy: Optional[str]) -> TikTokClient:
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        return TikTokClient(
            proxies=httpx_proxy,
            headers={"User-Agent": self.user_agent, "Cookie": cookie_str},
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        playwright_proxy = {"server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
                            "username": ip_proxy_info.user, "password": ip_proxy_info.password}
        httpx_proxy = {
            f"{ip_proxy_info.protocol}": f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"}
        return playwright_proxy, httpx_proxy

    async def launch_browser(self, chromium: BrowserType, playwright_proxy: Optional[Dict], user_agent: Optional[str],
                             headless: bool = True) -> BrowserContext:
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % "tiktok")
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir, accept_downloads=True, headless=headless, proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080}, user_agent=user_agent
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browser_context

    async def launch_browser_with_cdp(self, playwright: Playwright, playwright_proxy: Optional[Dict],
                                      user_agent: Optional[str], headless: bool = True) -> BrowserContext:
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright, playwright_proxy=playwright_proxy, user_agent=user_agent, headless=headless
            )
            return browser_context
        except Exception as e:
            utils.logger.error(f"[TikTokCrawler] CDP mode failed, fallback to standard mode: {e}")
            return await self.launch_browser(playwright.chromium, playwright_proxy, user_agent, headless)

    async def close(self):
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
        elif self.browser_context and not self.browser_context.is_closed():
            await self.browser_context.close()
        utils.logger.info("[TikTokCrawler.close] Browser context closed.")
