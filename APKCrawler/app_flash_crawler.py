import aiofiles
import aiohttp
import aioshutil
import asyncio
import http
import os
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm import tqdm
from typing import Optional
from urllib.parse import urlparse

BS4_PARSER = "lxml"


class APKFlashCrawler:
    FETCH_PERIOD = 0.3
    FROM_PAGE = 1
    MAX_PAGE_SIZE = 200
    DOWNLOAD_PAGE_RETRY_TIME = 3

    UA = UserAgent()
    HOST = "https://apkflash.com"
    # Category: finance
    PAGE_URL = f"{HOST}/apk/finance/top-popular?page=%d"
    CHECK_IN_URL = f"{HOST}/checkin/"

    DOWNLOAD_CHUNK_SIZE = 1024 * 1024 * 8
    DOWNLOAD_SEMAPHORE = asyncio.Semaphore(10)

    def _get_headers(self, referer: Optional[str] = None) -> dict[str, str]:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en;q=0.8",
            "Cache-Control": "no-cache",
            "Dnt": "1",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.UA.chrome
        }
        if referer is not None:
            headers["Referer"] = referer
        return headers

    async def _fetch_page(self, session: aiohttp.ClientSession, page: int) -> Optional[list[dict[str, str]]]:
        async with session.get(self.PAGE_URL % page, headers=self._get_headers(self.HOST)) as response:
            if response.status == http.HTTPStatus.NOT_FOUND:
                return None
            response.raise_for_status()
            content = await response.text()
            soup = BeautifulSoup(content, BS4_PARSER)
            info_list = soup.select("#webpage > div.container > div > main > div.box > div.article_left_apps > a.lapp")
            app_list = []
            if info_list is not None and len(info_list) > 0:
                for info in info_list:
                    # Filter category again
                    if "Finance" in info.select_one("span.author").get_text():
                        app_list.append(
                            {
                                "name": info.select_one("span.name").text.strip(),
                                "package": info["href"].split("/")[3],
                                "info_page_url": self.HOST + info["href"],
                                "download_page_url": self.HOST + info["href"] + "/download"
                            }
                        )
            return app_list

    async def _fetch_app_download_url(self, session: aiohttp.ClientSession, info: dict[str, str]) -> Optional[str]:
        async with session.get(info["download_page_url"], headers=self._get_headers(info["info_page_url"])) as response:
            if response.status == http.HTTPStatus.NOT_FOUND:
                return None
            response.raise_for_status()
            content = await response.text()
            soup = BeautifulSoup(content, BS4_PARSER)
            download_element = soup.select_one("#download > div > ul > li > a")
        if download_element is None:
            retry_time = 0
            download_headers = self._get_headers(info["download_page_url"])
            while download_element is None and retry_time < self.DOWNLOAD_PAGE_RETRY_TIME:
                async with session.post(info["download_page_url"], headers=download_headers) as response:
                    if response.status == http.HTTPStatus.NOT_FOUND:
                        return None
                    response.raise_for_status()
                    content = await response.text()
                    soup = BeautifulSoup(content, BS4_PARSER)
                    download_element = soup.select_one("#download > div > ul > li > a")
                retry_time += 1
        if download_element is None or not download_element.has_attr("href"):
            raise ValueError("Can't find download info!")
        return download_element["href"]

    @staticmethod
    def _get_downloaded_packages(output_dir: str, delete_tmp: bool = True) -> set[str]:
        package_names = []
        removed = []
        if os.path.isdir(output_dir):
            for f_name in os.listdir(output_dir):
                if not f_name.startswith(".") and f_name.endswith(".apk"):
                    package_names.append(f_name[:-len(".apk")])
                elif delete_tmp and not f_name.startswith(".") and f_name.endswith(".apk.tmp"):
                    os.remove(os.path.join(output_dir, f_name))
                    removed.append(f_name[:-len(".apk.tmp")])
                elif delete_tmp:
                    os.remove(os.path.join(output_dir, f_name))
        return set([i for i in package_names if i not in removed])

    async def _checkin(self, session: aiohttp.ClientSession) -> str:
        async with session.post(self.CHECK_IN_URL, headers=self._get_headers(self.HOST)) as response:
            response.raise_for_status()
            return (await response.text()).strip()

    async def _download_app(self, session: aiohttp.ClientSession, output_dir: str, info: dict[str, str], url: str, checkin_params: str):
        original_name = os.path.basename(urlparse(url).path)
        ext = os.path.splitext(original_name)[1]
        file_name = info["package"] + ext
        file_path = os.path.join(output_dir, file_name)
        tmp_file_path = os.path.join(output_dir, file_name + ".tmp")

        async with self.DOWNLOAD_SEMAPHORE:
            async with session.get(url + "&" + checkin_params, headers=self._get_headers(info["download_page_url"])) as response:
                response.raise_for_status()
                async with aiofiles.open(tmp_file_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(self.DOWNLOAD_CHUNK_SIZE):
                        await f.write(chunk)
        if os.path.isfile(tmp_file_path):
            await aioshutil.move(tmp_file_path, file_path)
        else:
            raise ValueError(f"Missing download file tmp: {tmp_file_path}")

    async def run(self, download_dir: str):
        current_page = self.FROM_PAGE
        local_packages = self._get_downloaded_packages(download_dir)
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as client:
            while current_page <= self.MAX_PAGE_SIZE:
                print(f"---------- Fetching page {current_page} ----------")
                app_info_list = await self._fetch_page(client, current_page)
                check_in_query = await self._checkin(client)
                if app_info_list is None:
                    print("Page end")
                    break

                download_tasks = []
                download_tasks_info = []
                with tqdm(total=len(app_info_list), desc="Adding tasks") as pbar:
                    for data in app_info_list:
                        pbar.set_postfix_str(f"{data['name']} ({data['package']})")
                        if data["package"] not in local_packages:
                            await asyncio.sleep(self.FETCH_PERIOD)
                            download_url = await self._fetch_app_download_url(client, data)
                            if download_url is not None:
                                task = asyncio.create_task(self._download_app(client, download_dir, data, download_url, check_in_query))
                                download_tasks.append(task)
                                download_tasks_info.append(data)
                        pbar.update(1)

                await asyncio.sleep(self.FETCH_PERIOD)

                if len(download_tasks) > 0:
                    exceptions = {}
                    with tqdm(total=len(download_tasks), desc=f"Downloading") as pbar:
                        for idx, task in enumerate(asyncio.as_completed(download_tasks)):
                            pbar.set_postfix_str(f"{download_tasks_info[idx]['name']} ({download_tasks_info[idx]['package']})")
                            # noinspection PyBroadException
                            try:
                                await task
                            except BaseException as e:
                                exceptions[idx] = e
                            finally:
                                pbar.update(1)
                    if len(exceptions) > 0:
                        print(f"Page {current_page} has {len(exceptions)} errors")
                        for idx, exception in exceptions.items():
                            print(f"Task {download_tasks_info[idx]['name']} ({download_tasks_info[idx]['package']}): {exception}")
                else:
                    print(f"No tasks in page {current_page}")

                current_page += 1


async def main():
    download_dir = os.path.join("download", "apk_flash")
    if not os.path.isdir(download_dir):
        os.makedirs(download_dir)
        await APKFlashCrawler().run(download_dir)
    else:
        print(f"Download dir {download_dir} already exists!")


if __name__ == '__main__':
    looper = asyncio.get_event_loop()
    try:
        looper.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        if not looper.is_closed:
            looper.close()
