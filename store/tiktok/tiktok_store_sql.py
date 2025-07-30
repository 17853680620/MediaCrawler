# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

from typing import Dict, List, Union

from async_db import AsyncMysqlDB
from async_sqlite_db import AsyncSqliteDB
from var import media_crawler_db_var


async def query_content_by_content_id(content_id: str) -> Dict:
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from tiktok_video where video_id = '{content_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    return rows[0] if len(rows) > 0 else {}


async def add_new_content(content_item: Dict) -> int:
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    return await async_db_conn.item_to_table("tiktok_video", content_item)


async def update_content_by_content_id(content_id: str, content_item: Dict) -> int:
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    return await async_db_conn.update_table("tiktok_video", content_item, "video_id", content_id)


async def query_comment_by_comment_id(comment_id: str) -> Dict:
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from tiktok_video_comment where comment_id = '{comment_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    return rows[0] if len(rows) > 0 else {}


async def add_new_comment(comment_item: Dict) -> int:
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    return await async_db_conn.item_to_table("tiktok_video_comment", comment_item)


async def update_comment_by_comment_id(comment_id: str, comment_item: Dict) -> int:
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    return await async_db_conn.update_table("tiktok_video_comment", comment_item, "comment_id", comment_id)


async def query_creator_by_user_id(user_id: str) -> Dict:
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from tiktok_creator where user_id = '{user_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    return rows[0] if len(rows) > 0 else {}


async def add_new_creator(creator_item: Dict) -> int:
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    return await async_db_conn.item_to_table("tiktok_creator", creator_item)


async def update_creator_by_user_id(user_id: str, creator_item: Dict) -> int:
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    return await async_db_conn.update_table("tiktok_creator", creator_item, "user_id", user_id)