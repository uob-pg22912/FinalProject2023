import asyncio
import dataclasses
import http
import os
from typing import Optional

import aiofiles
import aiofiles.os
import aiohttp
from dataclasses_json import DataClassJsonMixin
from lxml import etree
# noinspection PyProtectedMember
from lxml.etree import _Element
from tqdm import tqdm

from .consts import ANDROID_MANIFEST_NS, SOURCE_CODE_QUERY_EXCLUDE_PATH
from .source_code import AndroidSourceCodePath, AndroidSourceCodeQuery
from .utils import android_attrib


@dataclasses.dataclass(frozen=True)
class AndroidUriPermission(DataClassJsonMixin):
    type: str
    path: str


@dataclasses.dataclass(frozen=True)
class AndroidProvider(DataClassJsonMixin):
    package: str
    name: str
    authorities: list[str]
    exported: bool
    read_permission: Optional[str]
    write_permission: Optional[str]
    has_uri_permission: bool
    grant_uri_permissions: list[AndroidUriPermission]

    @property
    def all_permissions(self) -> list[str]:
        result = []
        if self.read_permission is not None:
            result.append(self.read_permission)
        if self.write_permission is not None:
            result.append(self.write_permission)
        return result

    def need_permission(self) -> bool:
        return self.read_permission is not None or self.write_permission is not None

    def __hash__(self) -> int:
        return hash(frozenset(self.authorities))


class AndroidProviderManifests:
    _PROVIDER_XPATH = "//application/provider[@android:authorities and (@android:exported='true' or @android:grantUriPermissions='true')]"

    _QUERY_PROJECT = "android"
    # noinspection SpellCheckingInspection
    _QUERY_REPO = "platform/superproject/main"
    # noinspection SpellCheckingInspection
    _QUERY_STRING = "lang:xml file:AndroidManifest.xml " + \
                    "content:<provider content:android\\:authorities " + \
                    "(content:android\\:exported=\"true\" OR content:android\\:grantUriPermissions=\"true\") " + \
                    SOURCE_CODE_QUERY_EXCLUDE_PATH

    _REQUEST_DELAY = 1

    def __init__(self, client: aiohttp.ClientSession, manifest_tmp_dir: Optional[str] = None):
        self._query: AndroidSourceCodeQuery = AndroidSourceCodeQuery(client)
        self._manifest_tmp_dir: Optional[str] = manifest_tmp_dir
        self._query_config: dict = self._query.get_query_config(
            query_string=self._QUERY_STRING,
            project=self._QUERY_PROJECT,
            repository=self._QUERY_REPO
        )

    async def get_latest_provider_manifest_path(self) -> dict[str, list[AndroidSourceCodePath]]:
        query_results = await self._query.query_pages(self._query_config)
        path_results = await self._query.extract_source_code_path(query_results)
        path_results = set(path_results)
        result: dict[str, list[AndroidSourceCodePath]] = {}
        for path in path_results:
            result.setdefault(path.project, []).append(path)
        return result

    @staticmethod
    def get_providers(manifest_content: str) -> list[AndroidProvider]:
        def _get_android_attr(element, name: str, default: str) -> str:
            if android_attrib(name) in element.attrib:
                return element.attrib[android_attrib(name)]
            else:
                return default

        def _get_uri_permission_path(element) -> list[AndroidUriPermission]:
            uri_permission_result: list[AndroidUriPermission] = []
            for uri_element in element.xpath("grant-uri-permission", namespaces=ANDROID_MANIFEST_NS):
                for name in ["path", "pathPrefix", "pathPattern"]:
                    if android_attrib(name) in uri_element.attrib:
                        uri_permission_result.append(AndroidUriPermission(name, uri_element.attrib[android_attrib(name)]))
                        break
            return uri_permission_result

        def _fix_pkg_or_app_name(package: str, content: str) -> str:
            return content.replace("${packageName}", package).replace("${applicationId}", package)

        def _fix_name(package: str, name: str) -> str:
            if name.startswith("."):
                return package + name
            elif "." not in name:
                return package + "." + name
            else:
                return name

        def _transform_authorities(package: str, authorities: str) -> list[str]:
            if ";" in authorities:
                return [_fix_pkg_or_app_name(package, i) for i in authorities.split(";")]
            else:
                return [_fix_pkg_or_app_name(package, authorities)]

        def _convert_bool(text: str) -> bool:
            if text == "true":
                return True
            elif text == "false":
                return False
            else:
                raise ValueError(f"Unknown boolean string: {text}")

        tree: _Element = etree.fromstring(manifest_content.encode("utf-8"))
        providers = tree.xpath(
            AndroidProviderManifests._PROVIDER_XPATH,
            namespaces=ANDROID_MANIFEST_NS
        )

        package_name = tree.attrib["package"]
        result: list[AndroidProvider] = []
        for provider in providers:
            read_permission: Optional[str] = None
            write_permission: Optional[str] = None

            if android_attrib("permission") in provider.attrib:
                read_permission = provider.attrib[android_attrib("permission")]
                write_permission = read_permission
            if android_attrib("readPermission") in provider.attrib:
                read_permission = provider.attrib[android_attrib("readPermission")]
            if android_attrib("writePermission") in provider.attrib:
                write_permission = provider.attrib[android_attrib("writePermission")]

            result.append(
                AndroidProvider(
                    package=package_name,
                    name=_fix_name(package_name, provider.attrib[android_attrib("name")]),
                    authorities=_transform_authorities(package_name, provider.attrib[android_attrib("authorities")]),
                    exported=_convert_bool(_get_android_attr(provider, "exported", "false")),
                    read_permission=read_permission,
                    write_permission=write_permission,
                    has_uri_permission=_convert_bool(_get_android_attr(provider, "grantUriPermissions", "false")),
                    grant_uri_permissions=_get_uri_permission_path(provider)
                )
            )
        return result

    def _get_manifest_tmp_path(self, code_path: AndroidSourceCodePath, refs: str) -> str:
        return os.path.join(self._manifest_tmp_dir, refs.replace("/", "_"), code_path.full_path)

    def _has_manifest_tmp(self, code_path: AndroidSourceCodePath, refs: str) -> bool:
        if self._manifest_tmp_dir is None:
            return False
        else:
            return os.path.isfile(self._get_manifest_tmp_path(code_path, refs))

    async def get_providers_from_manifest(self, code_path: AndroidSourceCodePath, refs: str, load_cache: bool = False) -> list[AndroidProvider]:
        local_path = self._get_manifest_tmp_path(code_path, refs)
        if load_cache and self._manifest_tmp_dir is not None and os.path.isfile(local_path):
            async with aiofiles.open(local_path, "r", encoding="utf-8") as f:
                manifest_content = await f.read()
        else:
            manifest_content = await (await self._query.get_source()).get_source_code(code_path, refs)
            if self._manifest_tmp_dir is not None:
                if not os.path.isdir(os.path.dirname(local_path)):
                    await aiofiles.os.makedirs(os.path.dirname(local_path))
                async with aiofiles.open(local_path, "w", encoding="utf-8") as f:
                    await f.write(manifest_content)

        return self.get_providers(manifest_content)

    async def get_all_android_providers(self, refs: str, load_cache: bool = False) -> list[AndroidProvider]:
        provider_path_dict = await self.get_latest_provider_manifest_path()
        result: set[AndroidProvider] = set()
        with tqdm(desc=refs, total=sum([len(i) for i in provider_path_dict.values()])) as pbar:
            for project, provider_path_list in provider_path_dict.items():
                for i, provider_path in enumerate(provider_path_list):
                    has_cache = load_cache and self._has_manifest_tmp(provider_path, refs)
                    if not has_cache and not await (await self._query.get_source()).exists(project, refs):
                        await asyncio.sleep(self._REQUEST_DELAY / 2)
                        break
                    fetch_success = False
                    while not fetch_success:
                        try:
                            pbar.set_postfix_str("Fetching")
                            providers = await self.get_providers_from_manifest(provider_path, refs, load_cache)
                            result.update(providers)
                            fetch_success = True
                            pbar.update(1)
                        except aiohttp.ClientResponseError as e:
                            if e.status == http.HTTPStatus.TOO_MANY_REQUESTS:
                                pbar.set_postfix_str("Sleep 20 seconds")
                                await asyncio.sleep(20)
                            elif e.status == http.HTTPStatus.NOT_FOUND:
                                fetch_success = True
                            else:
                                raise
                        if not has_cache and i != len(provider_path_list) - 1:
                            pbar.set_postfix_str(f"Delay {self._REQUEST_DELAY} seconds")
                            await asyncio.sleep(self._REQUEST_DELAY)
        return sorted(result, key=lambda x: (x.package, x.name))

    @staticmethod
    def filter_permission_providers(providers: list[AndroidProvider]) -> list[AndroidProvider]:
        return [p for p in providers if p.need_permission()]
