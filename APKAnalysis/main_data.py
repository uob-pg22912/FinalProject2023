import asyncio
import gc
import os
from typing import Callable

from apk_analysis.dataset import get_all_apk_dump_english_strings, get_clean_all_raw_apk_dump_english_strings, dump_dataset, load_dataset, get_dataset_path
from apk_analysis.graph import load_graph, get_category_labels
from apk_analysis.nlp import calculate_cosine_similarity, calculate_n_gram_jaccard_similarity, calculate_n_gram_similarity, calculate_transformer_cosine_similarity

RESOURCES_DIR = os.path.join(".", "resources")
APK_DUMP_DIR = os.path.join(RESOURCES_DIR, "apk_dump")
DATASET_DIR = os.path.join(RESOURCES_DIR, "dataset")

RAW_EN_STRING_PATH = os.path.join(DATASET_DIR, "raw_en_strings")
CLEAN_EN_STRING_PATH = os.path.join(DATASET_DIR, "clean_en_strings")

PRIVACY_TYPES_DIR = os.path.join(DATASET_DIR, "privacy_types")
DATA_PROTECTION_TYPES_DIR = os.path.join(DATASET_DIR, "data_protection_types")

PRIVACY_TYPES_PATH = os.path.join(PRIVACY_TYPES_DIR, "privacy_types.json")
PRIVACY_TYPES_CATEGORY_LABELS_PATH = os.path.join(PRIVACY_TYPES_DIR, "category_labels.json")

DATA_PROTECTION_TYPES_PATH = os.path.join(DATA_PROTECTION_TYPES_DIR, "data_protection_types.json")
DATA_PROTECTION_TYPES_CATEGORY_LABELS_PATH = os.path.join(DATA_PROTECTION_TYPES_DIR, "category_labels.json")

COSINE_DATASET_FILE = "cosine_dataset"
N_GRAM_JACCARD_DATASET_FILE = "n_gram_jaccard_dataset"
N_GRAM_DATASET_FILE = "n_gram_dataset"
TRANSFORMER_DATASET_FILE = "transformer_dataset"

MODEL_EN_LG = "en_core_web_lg"
# noinspection SpellCheckingInspection
MODEL_TRANSFORMER_SIMILARITY = "MSMARCO-distilbert-base-v4"

PRIVACY_TYPES = True
DATA_PROTECTION_TYPES = True

COSINE_SIMILARITY = True
N_GRAM_JACCARD_SIMILARITY = True
N_GRAM_SIMILARITY = True
TRANSFORMER_SIMILARITY = True

DUMP_PICKLE = True


def prepare_dir():
    if not os.path.exists(DATASET_DIR):
        os.makedirs(DATASET_DIR)
    if not os.path.exists(PRIVACY_TYPES_DIR):
        os.makedirs(PRIVACY_TYPES_DIR)
    if not os.path.exists(DATA_PROTECTION_TYPES_DIR):
        os.makedirs(DATA_PROTECTION_TYPES_DIR)


async def calculate_similarities(
        clean_en_strings: list[str],
        categories: dict[str, set[str]],
        output_dir: str,
        dump_pickle: bool
):
    async def _calculate_similarity(task_name: str, file_name: str, func: Callable[[], dict[int, dict[str, float]]]):
        dataset_path = get_dataset_path(output_dir, file_name, dump_pickle)
        if not os.path.exists(dataset_path):
            print(f"Calculating {task_name} ...")
            result = func()
            print(f"Dumping {task_name} dataset ...")
            dataset_result = await dump_dataset(dataset_path, result, dump_pickle)
            del result
        else:
            print(f"Found {task_name} dataset")
            dataset_result = load_dataset(dataset_path)
        print("Total:", len(dataset_result.labels))
        print("Empty:", sum([1 if all([j == 0.0 for j in i]) else 0 for i in dataset_result.labels]))
        del dataset_result
        gc.collect()

    if COSINE_SIMILARITY:
        await _calculate_similarity(
            "cosine similarity",
            COSINE_DATASET_FILE,
            lambda: calculate_cosine_similarity(clean_en_strings, categories, MODEL_EN_LG)
        )
        print()

    if N_GRAM_JACCARD_SIMILARITY:
        await _calculate_similarity(
            "n gram jaccard similarity",
            N_GRAM_JACCARD_DATASET_FILE,
            lambda: calculate_n_gram_jaccard_similarity(clean_en_strings, categories)
        )
        print()

    if N_GRAM_SIMILARITY:
        await _calculate_similarity(
            "n gram",
            N_GRAM_DATASET_FILE,
            lambda: calculate_n_gram_similarity(clean_en_strings, categories)
        )
        print()

    if TRANSFORMER_SIMILARITY:
        await _calculate_similarity(
            "transformer",
            TRANSFORMER_DATASET_FILE,
            lambda: calculate_transformer_cosine_similarity(
                clean_en_strings,
                categories,
                MODEL_TRANSFORMER_SIMILARITY
            )
        )
        print()


async def main():
    print("Preparing dirs")
    prepare_dir()

    print("Loading privacy types categories ...")
    privacy_types_categories = await get_category_labels(
        graph=await load_graph(PRIVACY_TYPES_PATH),
        category_labels_path=PRIVACY_TYPES_CATEGORY_LABELS_PATH,
        model=MODEL_EN_LG
    )
    print("Total categories:", len(privacy_types_categories))

    print()

    print("Loading data protection types categories ...")
    data_protection_types_categories = await get_category_labels(
        graph=await load_graph(DATA_PROTECTION_TYPES_PATH),
        category_labels_path=DATA_PROTECTION_TYPES_CATEGORY_LABELS_PATH,
        model=MODEL_EN_LG
    )
    print("Total categories:", len(data_protection_types_categories))

    print()

    print("Loading strings ...")
    raw_en_strings = await get_all_apk_dump_english_strings(APK_DUMP_DIR, RAW_EN_STRING_PATH, DUMP_PICKLE)
    print("Raw strings size:", len(raw_en_strings))

    print()

    print("Cleaning english strings ...")
    clean_en_strings = await get_clean_all_raw_apk_dump_english_strings(raw_en_strings, CLEAN_EN_STRING_PATH, MODEL_EN_LG, DUMP_PICKLE)
    print("Clean strings size:", len(clean_en_strings))
    print("Max text length:", max([len(i.split()) for i in clean_en_strings]))
    del raw_en_strings
    gc.collect()

    print()

    if PRIVACY_TYPES:
        print("----- Calculating private types similarities -----")
        await calculate_similarities(clean_en_strings, privacy_types_categories, PRIVACY_TYPES_DIR, DUMP_PICKLE)

        print()

    if DATA_PROTECTION_TYPES:
        print("----- Calculating data protection types similarities -----")
        await calculate_similarities(clean_en_strings, data_protection_types_categories, DATA_PROTECTION_TYPES_DIR, DUMP_PICKLE)

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
