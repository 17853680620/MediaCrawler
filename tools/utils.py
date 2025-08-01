# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


import argparse
import logging
import httpx
import aiofiles
import os

from .crawler_util import *
from .slider_util import *
from .time_util import *


def init_loging_config():
    level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    _logger = logging.getLogger("MediaCrawler")
    _logger.setLevel(level)
    return _logger


logger = init_loging_config()


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


async def download_file_async(url: str, folder: str, file_name: str, headers: dict, referer: str = ""):
    """
    Asynchronously downloads a file from a URL and saves it to a folder.
    Args:
        url (str): The URL of the file to download.
        folder (str): The folder where the file will be saved.
        file_name (str): The name of the file to save.
        headers (dict): The request headers to use for downloading.
        referer (str): The referer URL for the request.
    """
    if not url:
        logger.warning(f"[download_file_async] Download URL is empty for {file_name}")
        return

    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, file_name)

    request_headers = headers.copy()
    if referer:
        request_headers["Referer"] = referer

    try:
        async with httpx.AsyncClient(headers=request_headers, follow_redirects=True, timeout=120) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()  # 如果状态码不是 2xx，则会引发异常
                async with aiofiles.open(file_path, 'wb') as f:
                    async for chunk in response.aiter_bytes(): # <--- 流式读取
                        await f.write(chunk) # <--- 分块写入
                logger.info(f"✅ Successfully downloaded {file_path}")
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error downloading {url}: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"❌ Failed to download {url}: {e}")
