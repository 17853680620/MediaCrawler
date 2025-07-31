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
        # 用于 CDP 模式下的浏览器管理
        self.cdp_manager = None
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

    async def start(self) -> None:
        """
        启动爬虫并执行爬取的主要逻辑：
            如果启用了代理，创建代理池并设置代理。
            根据配置选择是否使用 CDP 模式启动浏览器。
            登录 TikTok，如果需要的话，更新 Cookies。
            根据爬虫类型（search、detail、creator）决定爬取的内容。
        """
        playwright_proxy_format, httpx_proxy_format = None, None
        # 是否启用 IP 代理
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(
                ip_proxy_info
            )

        # 启动浏览器并选择 CDP 模式或标准模式
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

            # 初始化浏览器页面
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            # 创建 TikTok 客户端并进行登录检查
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

            # 根据配置的爬虫类型执行相应的爬取任务
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_videos()
            elif config.CRAWLER_TYPE == "creator":
                await self.get_creators_and_videos()

            utils.logger.info("[TikTokCrawler.start] TikTok Crawler finished.")

    async def get_creators_and_videos(self) -> None:
        """
        获取指定创作者的视频内容：
            遍历创作者 ID 列表，获取创作者信息并保存。
            获取创作者的视频列表并更新视频数据。
            获取视频评论。
        """
        utils.logger.info("[TikTokCrawler.get_creators_and_videos] Begin getting creators' videos")
        for creator_id in config.TIKTOK_CREATOR_ID_LIST:
            utils.logger.info(f"[TikTokCrawler.get_creators_and_videos] Processing creator: {creator_id}")

            creator_info = await self.tk_client.get_creator_info_by_id(creator_id)

            if creator_info:
                await tiktok_store.save_creator(creator_info)
            else:
                utils.logger.warning(f"Could not fetch creator info for: {creator_id}")

            creator_url = f"{self.index_url}/@{creator_id}"
            scroll_times = (config.CRAWLER_MAX_NOTES_COUNT // 12) + 1

            # 获取创作者的视频列表
            video_list = await self._fetch_data_from_browse(
                url=creator_url,
                api_path="/api/post/item_list/",
                scroll_times=scroll_times
            )

            if not video_list:
                utils.logger.warning(f"Could not fetch videos for creator: {creator_id}")
                continue

            # 保存视频数据
            # video_ids = [item.get("id") for item in video_list if item and item.get("id")]
            # 构造包含 (video_id, video_url) 的元组列表
            videos_to_fetch_comments = []
            for item in video_list:
                await tiktok_store.update_tiktok_video(item)
                video_id = item.get("id")
                author_unique_id = item.get("author", {}).get("uniqueId")
                if video_id and author_unique_id:
                    video_url = f"{self.index_url}/@{author_unique_id}/video/{video_id}"
                    videos_to_fetch_comments.append((video_id, video_url))

            # 获取视频评论
            # await self.batch_get_video_comments(video_ids)
            await self.batch_get_video_comments(videos_to_fetch_comments)

    async def search(self) -> None:
        """
        执行 TikTok 视频的关键词搜索：
            遍历关键词并搜索相关视频。
            使用 _fetch_data_from_browse 获取视频列表，并更新视频数据。
        """
        utils.logger.info("[TikTokCrawler.search] Begin search TikTok keywords")
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[TikTokCrawler.search] Current keyword: {keyword}")

            search_url = f"{self.index_url}/search/video?q={urllib.parse.quote(keyword)}"
            scroll_times = (config.CRAWLER_MAX_NOTES_COUNT // 12) + 1

            # 获取搜索结果的视频列表
            video_list = await self._fetch_data_from_browse(
                url=search_url,
                api_path="/api/search/item/full/",
                scroll_times=scroll_times
            )

            if not video_list:
                utils.logger.warning(f"[TikTokCrawler.search] Did not find any videos for keyword: {keyword}")
                continue

            # 保存视频信息
            # video_ids = [item.get("id") for item in video_list if item.get("id")]
            # 构造包含 (video_id, video_url) 的元组列表
            videos_to_fetch_comments = []
            for item in video_list:
                await tiktok_store.update_tiktok_video(item)
                video_id = item.get("id")
                author_unique_id = item.get("author", {}).get("uniqueId")
                if video_id and author_unique_id:
                    video_url = f"{self.index_url}/@{author_unique_id}/video/{video_id}"
                    videos_to_fetch_comments.append((video_id, video_url))

            # 获取视频评论
            # await self.batch_get_video_comments(video_ids)
            await self.batch_get_video_comments(videos_to_fetch_comments)

    async def get_specified_videos(self):
        """通过完整的URL获取指定视频的信息和评论"""
        utils.logger.info("[TikTokCrawler.get_specified_videos] Begin fetching specified videos")
        video_ids_to_fetch_comments = []
        for video_url in config.TIKTOK_SPECIFIED_ID_LIST:
            try:
                # 1. 从完整的URL中解析出视频ID
                path_parts = urllib.parse.urlparse(video_url).path.strip('/').split('/')
                if len(path_parts) < 3 or path_parts[1] != 'video':
                    utils.logger.warning(f"Invalid TikTok video URL format: {video_url}")
                    continue
                video_id = path_parts[2]

                # 2. 调用 get_video_by_id_not_creator (现在它使用URL导航，而不是监听)
                video_detail = await self.tk_client.get_video_by_id_not_creator(video_url, video_id)
                if video_detail:
                    await tiktok_store.update_tiktok_video(video_detail)
                    video_ids_to_fetch_comments.append((video_id, video_url))  # 此处已是 (id, url) 元组
                else:
                    utils.logger.warning(f"Failed to get details for video URL: {video_url}")
            except Exception as e:
                utils.logger.error(f"Failed to process specified video URL {video_url}: {e}")

        # 3. 批量获取评论
        await self.batch_get_video_comments(video_ids_to_fetch_comments)

    async def _fetch_data_from_browse(self, url: str, api_path: str, scroll_times: int, page_type: str = "video") -> \
    List[Dict]:
        """
        负责向 TikTok 页面发起请求并滚动页面加载更多内容：
            使用 response_handler 监听 API 响应并解析数据。
            滚动页面以加载更多数据，并检查是否有新的数据。
        """
        all_items = []
        seen_ids = set()  # 用于防止重复数据
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

            # 滚动页面
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

    async def batch_get_video_comments(self, videos: List[Tuple[str, str]]):
        """
        批量获取视频的评论：
            为每个视频 ID 启动一个异步任务来获取评论。
        """
        if not config.ENABLE_GET_COMMENTS:
            return
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        tasks = [self.get_comments(video_id, video_url, semaphore) for video_id, video_url in videos if video_id]
        if tasks:
            await asyncio.gather(*tasks)

    async def get_comments(self, video_id: str, video_url: str, semaphore: asyncio.Semaphore):
        """
        获取单个视频的评论：
            滚动页面加载更多评论并保存评论数据。
        """
        async with semaphore:
            utils.logger.info(f"[TikTokCrawler.get_comments] Fetching comments for video {video_id}")
            # user_unique_id = self.tk_client.cookie_dict.get('user_unique_id', 'tiktok')
            # video_url = f"{self.index_url}/@{user_unique_id}/video/{video_id}"
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
        """
        创建 TikTok 客户端，并设置代理和 Cookies。
        """
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        return TikTokClient(
            proxies=httpx_proxy,
            headers={"User-Agent": self.user_agent, "Cookie": cookie_str},
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        格式化代理信息，用于 Playwright 和 HTTPX。
        """
        playwright_proxy = {"server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
                            "username": ip_proxy_info.user, "password": ip_proxy_info.password}
        httpx_proxy = {
            f"{ip_proxy_info.protocol}": f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"}
        return playwright_proxy, httpx_proxy

    async def launch_browser(self, chromium: BrowserType, playwright_proxy: Optional[Dict], user_agent: Optional[str],
                             headless: bool = True) -> BrowserContext:
        """
        启动一个新的浏览器实例（使用标准模式）。
        """
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
        """
        使用 Chrome DevTools 协议启动浏览器。
        """
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
        """
        关闭浏览器并清理资源。
        """
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
        elif self.browser_context and not self.browser_context.is_closed():
            await self.browser_context.close()
        utils.logger.info("[TikTokCrawler.close] Browser context closed.")
