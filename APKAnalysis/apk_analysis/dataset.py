import asyncio
import dataclasses
import math
import multiprocessing
import os
import pickle
from typing import Optional

import aiofiles
import aiofiles.os
import pandas as pd
from dataclasses_json import DataClassJsonMixin
from tqdm import tqdm

from .data import APKAnalysisResult
from .nlp import clean_text, filter_english_text
from .utils import load_strings, list_all_json, dump_strings, dump_data, get_workers_size


async def load_apk_dump(json_path: str) -> APKAnalysisResult:
    async with aiofiles.open(json_path, "r", encoding="utf-8") as f:
        return APKAnalysisResult.from_json(await f.read())


def load_strings_from_dump(analysis_result: APKAnalysisResult) -> set[str]:
    analysis_strings = set()
    analysis_strings.update(analysis_result.strings.embedded_strings)
    analysis_strings.update(analysis_result.strings.layout_strings)
    analysis_strings.update(analysis_result.strings.res_strings.values())
    analysis_strings.update({j for item in analysis_result.strings.array_strings.values() for j in item})
    return analysis_strings


async def load_all_english_strings(*apk_dumps_path: str, batch_size: int = 100) -> list[str]:
    async def _load_all(json_path: str) -> set[str]:
        return load_strings_from_dump(await load_apk_dump(json_path))

    results = set()
    with tqdm(total=len(apk_dumps_path), desc="Loading all strings") as pbar:
        for i in range(0, len(apk_dumps_path), batch_size):
            tasks = [asyncio.create_task(_load_all(path)) for path in apk_dumps_path[i:i + batch_size]]
            for task in asyncio.as_completed(tasks):
                results.update(await task)
                pbar.update(1)
    return list(filter_english_text(results, accuracy=True))


async def get_apk_dump_english_strings(apk_dump_path: str) -> list[str]:
    strings = await load_all_english_strings(apk_dump_path)
    return list(strings)


async def get_all_apk_dump_english_strings(apk_dump_dir: str, raw_string_path: str, dump_pickle: bool) -> list[str]:
    if dump_pickle:
        raw_string_path += ".pkl"
    else:
        raw_string_path += ".json"
    if await aiofiles.os.path.exists(raw_string_path):
        return await load_strings(raw_string_path)
    else:
        json_files = list_all_json(apk_dump_dir)
        strings = await load_all_english_strings(*json_files)
        await dump_strings(strings, raw_string_path, dump_pickle)
        return strings


def _clean_raw_apk_dump_english_strings(raw_strings: list[str], model: str) -> list[str]:
    return list(set([i for i in clean_text(raw_strings, model, False) if len(i) > 0]))


def clean_raw_apk_dump_english_strings(texts: list[str], model: str, workers: Optional[int] = None, batch_size: int = 10000) -> list[str]:
    result = set()
    with multiprocessing.Pool(processes=get_workers_size(0.5, workers)) as pool:
        with tqdm(total=math.ceil(len(texts) / batch_size), desc=f"Cleaning text") as pbar:
            batch_tasks = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_result = pool.apply_async(_clean_raw_apk_dump_english_strings, (batch_texts, model), callback=lambda _: pbar.update(1))
                batch_tasks.append(batch_result)
            for batch_task in batch_tasks:
                result.update(batch_task.get())
    return list(result)


async def get_clean_all_raw_apk_dump_english_strings(raw_strings: list[str], clean_string_path: str, model: str, dump_pickle: bool) -> list[str]:
    if dump_pickle:
        clean_string_path += ".pkl"
    else:
        clean_string_path += ".json"
    if await aiofiles.os.path.exists(clean_string_path):
        return await load_strings(clean_string_path)
    else:
        clean_strings = clean_raw_apk_dump_english_strings(raw_strings, model)
        await dump_strings(clean_strings, clean_string_path, dump_pickle)
        return clean_strings


@dataclasses.dataclass(frozen=True)
class TextDataset(DataClassJsonMixin):
    categories: list[str]
    labels: list[list[float]]

    def to_pandas(self) -> pd.DataFrame:
        return pd.DataFrame(self.labels, columns=self.categories)


def get_dataset_path(type_dir: str, file_name: str, is_pickle: bool) -> str:
    if is_pickle:
        file_name += ".pkl"
    else:
        file_name += ".json"
    return os.path.join(type_dir, file_name)


def load_dataset(dataset_path: str) -> TextDataset:
    if os.path.exists(dataset_path):
        file_name = os.path.basename(dataset_path)
        if file_name.endswith(".json"):
            with open(dataset_path, "r", encoding="utf-8") as f:
                return TextDataset.from_json(f.read())
        elif file_name.endswith(".pkl"):
            with open(dataset_path, "rb") as f:
                return TextDataset.from_dict(pickle.load(f))
        else:
            raise ValueError(f"Unknown extension from file: {file_name}")
    raise FileNotFoundError(f"File {dataset_path} not exists!")


def generate_dataset(similarities: dict[int, dict[str, float]]) -> TextDataset:
    categories = sorted(list(next(iter(similarities.values())).keys()))
    labels = [
        [similarities[i][c] for c in categories]
        for i in range(len(similarities))
    ]
    return TextDataset(
        categories=categories,
        labels=labels
    )


async def dump_dataset(dataset_path: str, similarities: dict[int, dict[str, float]], dump_pickle: bool):
    data = generate_dataset(similarities)
    await dump_data(data.to_dict(), dataset_path, dump_pickle)
    return data


async def try_convert_dataset_to_pickle(*dataset_paths: str):
    for dataset_path in dataset_paths:
        file_name = os.path.basename(dataset_path)
        if file_name.endswith(".json"):
            new_dataset_path = dataset_path[:-5] + ".pkl"
            if os.path.exists(new_dataset_path):
                print(f"Pickle exists! {new_dataset_path}")
            else:
                dataset = load_dataset(dataset_path)
                await dump_data(dataset.to_dict(), new_dataset_path, True)
        else:
            print(f"Not a JSON file! {dataset_path}")


async def try_convert_dataset_to_json(*dataset_paths: str):
    for dataset_path in dataset_paths:
        file_name = os.path.basename(dataset_path)
        if file_name.endswith(".pkl"):
            new_dataset_path = dataset_path[:-5] + ".json"
            if os.path.exists(new_dataset_path):
                print(f"JSON exists! {new_dataset_path}")
            else:
                dataset = load_dataset(dataset_path)
                await dump_data(dataset.to_dict(), new_dataset_path, False)
        else:
            print(f"Not a Pickle file! {dataset_path}")
