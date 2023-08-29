import asyncio
import json
import multiprocessing
import os
import pickle
import re
from itertools import zip_longest
from typing import Optional, Union

import aiofiles


def get_workers_size(ratio: float = 1 / 2, workers: Optional[int] = None) -> int:
    return workers if workers is not None else max(1, int(multiprocessing.cpu_count() * ratio))


async def dump_strings(strings: list[str], dump_path: str, is_pickle: bool):
    await dump_data(strings, dump_path, is_pickle)


async def load_strings(dump_path: str) -> list[str]:
    return await load_data(dump_path)


async def dump_data(data: any, dump_path: str, is_pickle: bool = False):
    if is_pickle:
        async with aiofiles.open(dump_path, "wb") as f:
            content = pickle.dumps(data)
            await f.write(content)
    else:
        async with aiofiles.open(dump_path, "w", encoding="utf-8") as f:
            content = json.dumps(data, ensure_ascii=False)
            await f.write(content)


async def load_data(dump_path: str) -> any:
    if os.path.exists(dump_path):
        file_name = os.path.basename(dump_path)
        if file_name.endswith(".json"):
            async with aiofiles.open(dump_path, "r", encoding="utf-8") as f:
                return json.loads(await f.read())
        elif file_name.endswith(".pkl"):
            async with aiofiles.open(dump_path, "rb") as f:
                return pickle.loads(await f.read())
        else:
            raise ValueError(f"Unknown extension from file: {file_name}")
    raise FileNotFoundError(f"File {dump_path} not exists!")


def list_all_json(dir_path: str) -> list[str]:
    return [
        os.path.join(dir_path, name)
        for name in os.listdir(dir_path)
        if not name.startswith(".") and name.endswith(".json")
    ]


class VersionCompare:
    _INSTANCE: Optional['VersionCompare'] = None

    @staticmethod
    def instance() -> 'VersionCompare':
        if VersionCompare._INSTANCE is None:
            VersionCompare._INSTANCE = VersionCompare()
        return VersionCompare._INSTANCE

    def __init__(self):
        self._version_pattern: re.Pattern = re.compile(r"(\d+)([a-zA-Z]*)")

    def compare(self, v1: str, v2: str) -> int:
        if v1 == v2:
            return 0

        m1 = self._version_pattern.findall(v1)
        m2 = self._version_pattern.findall(v2)

        for p1, p2 in zip_longest(m1, m2):
            c1, s1 = p1 if p1 is not None else (0, "")
            c2, s2 = p2 if p2 is not None else (0, "")
            c1, c2 = int(c1), int(c2)

            if c1 < c2:
                return -1
            elif c1 > c2:
                return 1
            elif s1 < s2:
                return -1
            elif s1 > s2:
                return 1

        return 0


async def run_commands(*commands: str, cwd: Optional[str] = None, output: bool = True) -> Union[int, tuple[int, bytes, bytes]]:
    process = await asyncio.create_subprocess_shell(
        ";".join(commands),
        stdout=asyncio.subprocess.PIPE if output else asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE if output else asyncio.subprocess.DEVNULL,
        cwd=cwd
    )
    if output:
        stdout, stderr = await process.communicate()
        await process.wait()
        return process.returncode, stdout, stderr
    else:
        await process.wait()
        return process.returncode


async def check_java_version(min_version: str):
    # noinspection PyBroadException
    try:
        code, _, output_bytes = await run_commands("java -version")
        if code == 0:
            output_content: str = output_bytes.decode()
            matcher = re.search(r"version \"(.*?)\"", output_content)
            if matcher is not None:
                java_version = matcher.group(1).strip()
                if VersionCompare.instance().compare(min_version, java_version) > 0:
                    raise EnvironmentError(f"Current java version {java_version}. Require java version >= {min_version}!")
            else:
                raise EnvironmentError("Unknown java version")
        else:
            raise EnvironmentError("No java running environment")
    except UnicodeDecodeError:
        raise EnvironmentError("No java running environment")
