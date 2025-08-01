from typing import List, Dict

import config
from var import source_keyword_var
from tools import utils
from base.base_crawler import AbstractStore
from media_platform.tiktok.client import TikTokClient
from .tiktok_store_impl import (
    TikTokCsvStoreImplement,
    TikTokDbStoreImplement,
    TikTokJsonStoreImplement,
    TikTokSqliteStoreImplement
)


class TikTokStoreFactory:
    STORES = {
        "csv": TikTokCsvStoreImplement,
        "db": TikTokDbStoreImplement,
        "json": TikTokJsonStoreImplement,
        "sqlite": TikTokSqliteStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = TikTokStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[TikTokStoreFactory.create_store] Invalid save option..."
            )
        return store_class()


async def update_tiktok_video(video_item: Dict, tk_client: TikTokClient):
    # utils.logger.info(f"[store.tiktok.update_tiktok_video] video_item:{video_item}")
    user_info = video_item.get("author", {})
    stats = video_item.get("stats", {})
    music = video_item.get("music", {})
    video_id = video_item.get("id")

    save_content_item = {
        "video_id": video_id,
        "title": video_item.get("desc", ""),
        "desc": video_item.get("desc", ""),
        "create_time": video_item.get("createTime"),
        "user_id": user_info.get("id"),
        "sec_uid": user_info.get("secUid"),
        "user_unique_id": user_info.get("uniqueId"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("avatarThumb"),
        "user_signature": user_info.get("signature"),
        "liked_count": str(stats.get("diggCount", 0)),
        "collected_count": str(stats.get("collectCount")),
        "comment_count": str(stats.get("commentCount")),
        "share_count": str(stats.get("shareCount")),
        "ip_location": video_item.get("locationCreated", ""),  # 修正: 从 locationCreated 字段获取
        "last_modify_ts": utils.get_current_timestamp(),
        "video_url": f"https://www.tiktok.com/@{user_info.get('uniqueId')}/video/{video_id}",
        "cover_url": video_item.get("video", {}).get("cover"),
        "video_download_url": video_item.get("video", {}).get("playAddr"),
        "music_download_url": music.get("playUrl"),
        "source_keyword": source_keyword_var.get(),
    }
    await TikTokStoreFactory.create_store().store_content(content_item=save_content_item)

    if config.ENABLE_GET_VIDEOS:
        video_download_url = save_content_item.get("video_download_url")
        video_page_url = save_content_item.get("video_url")  # 获取视频详情页URL
        if video_download_url:
            file_name = f"{video_id}.mp4"
            download_folder = "data/tiktok/videos"
            # ❗❗ 在调用下载函数时，传入 video_page_url 作为 referer
            await utils.download_file_async(
                url=video_download_url,
                folder=download_folder,
                file_name=file_name,
                headers=tk_client.headers,
                referer=video_page_url  # 传入 Referer
            )


async def batch_update_tiktok_video_comments(video_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_tiktok_video_comment(video_id, comment_item)


async def update_tiktok_video_comment(video_id: str, comment_item: Dict):
    # utils.logger.info(f"[store.tiktok.update_tiktok_video_comment] comment_item:{comment_item}")
    user_info = comment_item.get("user", {})
    comment_id = comment_item.get("cid")

    create_time_val = comment_item.get("create_time")
    if create_time_val is None:
        create_time_val = utils.get_unix_timestamp()

    # 安全地获取头像URL
    avatar_thumb_info = user_info.get("avatar_thumb", {})
    avatar_url = avatar_thumb_info.get("url_list", [None])[0] if avatar_thumb_info.get("url_list") else None

    save_comment_item = {
        "comment_id": comment_id,
        "video_id": video_id,
        "content": comment_item.get("text"),
        "create_time": create_time_val,
        "like_count": str(comment_item.get("digg_count", 0)),  # 注意原始数据是 digg_count
        "sub_comment_count": str(comment_item.get("reply_comment_total", 0)),  # 注意原始数据是 reply_comment_total
        "parent_comment_id": comment_item.get("reply_id", "0"), # 注意原始数据是 reply_id
        "user_id": user_info.get("uid"),  # 修正: uid
        "sec_uid": user_info.get("sec_uid"),  # 修正: sec_uid
        "user_unique_id": user_info.get("unique_id"),  # 修正: unique_id
        "nickname": user_info.get("nickname"),
        "avatar": avatar_url,  # 修正: avatar_url
        "user_signature": user_info.get("signature"),
        "ip_location": "",  # 评论API似乎不返回IP
        "last_modify_ts": utils.get_current_timestamp(),
    }
    await TikTokStoreFactory.create_store().store_comment(comment_item=save_comment_item)


async def save_creator(creator_info: Dict):
    # utils.logger.info(f"[store.tiktok.save_creator] creator_info:{creator_info}")
    # 接收的是完整的 userInfo 对象，我们需要从中提取 user 和 stats
    if not creator_info or not creator_info.get("user"):
        utils.logger.warning(f"Received invalid creator_info to save: {creator_info}")
        return

    user_data = creator_info.get("user", {})
    stats = creator_info.get("stats", {})

    save_item = {
        "user_id": user_data.get("id"),
        "nickname": user_data.get("nickname"),
        "avatar": user_data.get("avatarLarger"),
        "desc": user_data.get("signature"),
        "gender": "",
        "follows": stats.get("followingCount", 0),
        "fans": stats.get("followerCount", 0),
        "interaction": stats.get("heartCount", 0),
        "videos_count": stats.get("videoCount", 0),
        "ip_location": "",
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.tiktok.save_creator] creator:{save_item}")
    await TikTokStoreFactory.create_store().store_creator(save_item)
