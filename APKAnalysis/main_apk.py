import asyncio
import dataclasses
import json
import os
from typing import Optional
from urllib.parse import urlparse

import aiofiles
import aiofiles.os
from dataclasses_json import DataClassJsonMixin

from apk_analysis.analysis import run_analysis_tools
from apk_analysis.data import AndroidPermissions, AndroidAPILevel
from apk_analysis.dataset import clean_raw_apk_dump_english_strings, generate_dataset, load_apk_dump, load_strings_from_dump
from apk_analysis.nlp import calculate_transformer_cosine_similarity, filter_english_text
from apk_analysis.utils import check_java_version, load_data

WORK_DIR = os.path.join(".", "workspace")

APK_DIR = os.path.join(WORK_DIR, "apks")
APK_DUMP_DIR = os.path.join(WORK_DIR, "apk_dump")
RESULT_DIR = os.path.join(WORK_DIR, "result")

DATASET_DIR = os.path.join(".", "resources", "dataset")
PRIVACY_TYPES_PATH = os.path.join(DATASET_DIR, "privacy_types", "category_labels.json")
DATA_PROTECTION_PATH = os.path.join(DATASET_DIR, "data_protection_types", "category_labels.json")
PERMISSIONS_REL_PATH = os.path.join(DATASET_DIR, "constants", "permissions", "permissions-REL.json")
API_LEVELS_PATH = os.path.join(DATASET_DIR, "constants", "api_levels.json")

MIN_JAVA_VERSION = "11"
PRIVACY_TYPE_SIMILARITY_THRESHOLD = 0.15
DATA_COLLECTION_TYPE_SIMILARITY_THRESHOLD = 0.3

MODEL_EN_LG = "en_core_web_lg"
# noinspection SpellCheckingInspection
MODEL_TRANSFORMER_SIMILARITY = "MSMARCO-distilbert-base-v4"

DANGEROUS_PERMISSION_LEVELS = {"dangerous", "signature", "signatureOrSystem", "privileged"}
REMOTE_HOST_SCHEMES = {"http", "https", "wss", "ftp", "ssl", "tcp", "udp", "telnet", "ldap", "rtp"}


@dataclasses.dataclass(frozen=True)
class APKTracker(DataClassJsonMixin):
    name: str
    website: Optional[str]
    categories: list[str]


@dataclasses.dataclass(frozen=True)
class APKPermission(DataClassJsonMixin):
    name: str
    description: Optional[str]
    label: Optional[str]
    is_dangerous: bool


@dataclasses.dataclass(frozen=True)
class RemoteHost(DataClassJsonMixin):
    protocol: str
    host: str


@dataclasses.dataclass(frozen=True)
class APKReport(DataClassJsonMixin):
    application_name: str
    package_name: str
    min_sdk_version: int
    min_sdk_version_name: Optional[str]
    target_sdk_version: int
    target_sdk_version_name: Optional[str]
    version_code: int
    version_name: str
    use_permissions: list[APKPermission]
    api_call_permissions: list[APKPermission]
    content_provider_permissions: list[APKPermission]
    ip_list: list[str]
    uri_list: list[str]
    host_list: list[RemoteHost]
    http_ssl_ratio: Optional[float]
    trackers: list[APKTracker]
    privacy_data_collections: list[str]
    privacy_protection_measures: list[str]


async def get_categories(category_labels_path: str) -> dict[str, set[str]]:
    if await aiofiles.os.path.exists(category_labels_path):
        content: dict[str, list[str]] = await load_data(category_labels_path)
        return {k: set(v) for k, v in content.items()}
    else:
        raise FileNotFoundError(category_labels_path)


async def load_permissions(path: str) -> AndroidPermissions:
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        return AndroidPermissions.from_json(await f.read())


async def load_api_levels(path: str) -> dict[int, AndroidAPILevel]:
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        data: dict = json.loads(await f.read())
        return {int(k): AndroidAPILevel.from_dict(v) for k, v in data.items()}


async def output_apk_report(apk_report: APKReport):
    file_name = f"{apk_report.package_name}_{apk_report.version_name}({apk_report.version_code}).json"
    output_path = os.path.join(RESULT_DIR, file_name)
    async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
        await f.write(apk_report.to_json(ensure_ascii=False, indent=2))


def reformat_text(text: str) -> str:
    text = text.strip()
    text = text[0].upper() + text[1:]
    return text


def get_apk_permission(permission: str, permissions: AndroidPermissions) -> APKPermission:
    if permission in permissions.permissions:
        data = permissions.permissions[permission]
        return APKPermission(
            name=permission,
            description=reformat_text(data.description) if data.description is not None else None,
            label=reformat_text(data.label) if data.label is not None else None,
            is_dangerous=len(DANGEROUS_PERMISSION_LEVELS & set(data.protection_levels)) > 0
        )
    else:
        return APKPermission(name=permission, description=None, label=None, is_dangerous=False)


def get_api_version_name(version: int, api_levels: dict[int, AndroidAPILevel]) -> Optional[str]:
    if version in api_levels:
        name = api_levels[version].name
        if name is None:
            return f"Android {version}"
        else:
            if name.startswith("Android"):
                return f"Android {name[7:]} ({api_levels[version].version_range})"
            else:
                return f"Android {name} ({api_levels[version].version_range})"
    else:
        return None


def filter_remote_hosts(uris: list[str]) -> tuple[list[RemoteHost], list[str]]:
    remote_hosts: list[RemoteHost] = []
    other_uris: list[str] = []
    for i in [urlparse(uri) for uri in uris]:
        if i.scheme.lower() in REMOTE_HOST_SCHEMES:
            remote_hosts.append(RemoteHost(protocol=i.scheme.lower(), host=i.hostname))
        else:
            other_uris.append(i.geturl())
    return sorted(set(remote_hosts), key=lambda x: x.host), sorted(set(other_uris))


def calculate_http_ssl_ratio(hosts: list[RemoteHost]) -> Optional[float]:
    total = 0
    https = 0
    for i in hosts:
        if i.protocol == "http":
            total += 1
        elif i.protocol == "https":
            total += 1
            https += 1
    if total == 0:
        return None
    else:
        return https / total


def analyze_category_types(clean_en_strings: list[str], category_types: dict[str, set[str]], threshold: float) -> list[str]:
    similarities = calculate_transformer_cosine_similarity(clean_en_strings, category_types, MODEL_TRANSFORMER_SIMILARITY)
    df = generate_dataset(similarities).to_pandas()
    result = [(col.replace("_", " "), df[col][df[col] >= threshold].count()) for col in df]
    result = sorted([i for i in result if i[1] > 0], key=lambda x: x[1], reverse=True)
    return [i[0] for i in result]


async def main():
    print("Init environment ...")
    await check_java_version(MIN_JAVA_VERSION)
    api_levels = await load_api_levels(API_LEVELS_PATH)
    permissions = await load_permissions(PERMISSIONS_REL_PATH)
    privacy_types = await get_categories(PRIVACY_TYPES_PATH)
    data_protection_types = await get_categories(DATA_PROTECTION_PATH)

    apk_paths = [os.path.join(APK_DIR, i) for i in os.listdir(APK_DIR) if not i.startswith(".") and i.endswith(".apk")]
    print(f"Found {len(apk_paths)} APK")

    print()

    print("Running code analysis ...")
    analysis_results = await run_analysis_tools(APK_DUMP_DIR, apk_paths)
    success_analysis_results = [i for b, i in analysis_results.values() if b]
    print(f"Success: {len(success_analysis_results)}   Failed: {len(analysis_results) - len(success_analysis_results)}")

    print()

    print("Analysing strings ...")
    for dump_path in success_analysis_results:
        apk_dump = await load_apk_dump(dump_path)
        print(f"App: {apk_dump.manifest.application_name} ({apk_dump.manifest.version_code}) - {apk_dump.manifest.package_name}")

        print()

        raw_strings = load_strings_from_dump(apk_dump)
        print(f"Get {len(raw_strings)} raw text")

        raw_en_strings = list(filter_english_text(raw_strings, accuracy=True))
        print(f"Get {len(raw_en_strings)} raw english text")

        clean_en_strings = clean_raw_apk_dump_english_strings(raw_en_strings, MODEL_EN_LG)
        print(f"Get {len(clean_en_strings)} clean text")

        print()

        print("Analysing data collections ...")
        app_privacy_types = analyze_category_types(clean_en_strings, privacy_types, PRIVACY_TYPE_SIMILARITY_THRESHOLD)
        print()

        print("Analysing data protections ...")
        app_data_protection_types = analyze_category_types(clean_en_strings, data_protection_types, DATA_COLLECTION_TYPE_SIMILARITY_THRESHOLD)
        print()

        print(f"Exporting report ...")
        remote_hosts, other_uris = filter_remote_hosts(apk_dump.strings.uris)
        apk_report = APKReport(
            application_name=apk_dump.manifest.application_name,
            package_name=apk_dump.manifest.package_name,
            min_sdk_version=apk_dump.manifest.min_sdk_version,
            min_sdk_version_name=get_api_version_name(apk_dump.manifest.min_sdk_version, api_levels),
            target_sdk_version=apk_dump.manifest.target_sdk_version,
            target_sdk_version_name=get_api_version_name(apk_dump.manifest.target_sdk_version, api_levels),
            version_code=apk_dump.manifest.version_code,
            version_name=apk_dump.manifest.version_name,
            use_permissions=[get_apk_permission(i, permissions) for i in apk_dump.manifest.use_permissions],
            api_call_permissions=[get_apk_permission(i, permissions) for i in apk_dump.dex_api_permissions.api_call_permissions],
            content_provider_permissions=[get_apk_permission(i, permissions) for i in apk_dump.dex_api_permissions.content_provider_permissions],
            ip_list=apk_dump.strings.ipv4,
            uri_list=other_uris,
            host_list=remote_hosts,
            http_ssl_ratio=calculate_http_ssl_ratio(remote_hosts),
            trackers=[APKTracker(name=i.name, website=i.website, categories=i.categories) for i in apk_dump.trackers],
            privacy_data_collections=[reformat_text(i) for i in app_privacy_types],
            privacy_protection_measures=[reformat_text(i) for i in app_data_protection_types]
        )
        await output_apk_report(apk_report)
        print()


if __name__ == "__main__":
    looper = asyncio.get_event_loop()
    try:
        looper.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        if not looper.is_closed:
            looper.close()
