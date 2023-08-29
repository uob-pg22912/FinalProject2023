import math
import multiprocessing
import re
from typing import Collection, Optional

import spacy
import torch
from lingua import Language, LanguageDetectorBuilder
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

from apk_analysis.utils import get_workers_size


def _filter_language_text(texts: Collection[str], language: Language, accuracy: bool = False) -> set[str]:
    detector_builder = LanguageDetectorBuilder.from_all_spoken_languages()
    if accuracy:
        detector_builder = detector_builder.with_low_accuracy_mode()
    detector = detector_builder.build()
    result = set()
    for text in texts:
        detect_language = detector.detect_language_of(text)
        if detect_language == language:
            result.add(text)
    return result


def filter_english_text(texts: Collection[str], batch_size: int = 50, workers: Optional[int] = None, accuracy: bool = False) -> set[str]:
    texts = list(texts)
    result = set()
    with multiprocessing.Pool(processes=get_workers_size(0.5, workers)) as pool:
        with tqdm(total=math.ceil(len(texts) / batch_size), desc=f"Filtering {Language.ENGLISH.name} text") as pbar:
            batch_tasks = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_result = pool.apply_async(_filter_language_text, (batch_texts, Language.ENGLISH, accuracy), callback=lambda _: pbar.update(1))
                batch_tasks.append(batch_result)
            for batch_task in batch_tasks:
                result.update(batch_task.get())
    return result


# noinspection SpellCheckingInspection
def clean_text(strings: list[str], model: str, show_bar: bool = False, workers: int = 1) -> list[str]:
    nlp = spacy.load(model)
    re_strings = []
    for string in strings:
        string = re.sub(r"https?://\S+", "", string)
        string = re.sub(r"<.*?>", " ", string)
        string = re.sub(r"\b[0-9]+\b\s*", "", string)
        string = re.sub(r"([a-z]|\d)([A-Z])", r"\1 \2", string)
        string = " ".join(string.split())
        string = string.lower().strip()
        if len(string) > 2:
            re_strings.append(string)
    iter_data = nlp.pipe(re_strings, n_process=workers)
    if show_bar:
        iter_data = tqdm(iter_data, total=len(re_strings), desc="Cleaning text")
    clean_texts = []
    for doc in iter_data:
        for sentence_doc in doc.sents:
            sentence = []
            for token in sentence_doc:
                if not token.is_punct and not token.is_stop and \
                        not token.like_num and not token.like_email and not token.like_url and \
                        not token.is_space and token.is_alpha and len(token.lemma_) > 1:
                    sentence.append(token.lemma_)
            if len(sentence) > 0:
                clean_texts.append(" ".join(sentence))
    return clean_texts


def n_gram(tokens: Collection[str], n: int) -> list[tuple[str]]:
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def jaccard_similarity(set1: set[tuple[str]], set2: set[tuple[str]]) -> float:
    intersection = len(set1.intersection(set2))
    union = len(set1) + len(set2) - intersection
    return intersection / union


def n_gram_jaccard_similarity(tokens1: Collection[str], tokens2: Collection[str], n: int) -> float:
    return jaccard_similarity(set(n_gram(tokens1, n)), set(n_gram(tokens2, n)))


def _calculate_n_gram_jaccard_similarity(strings: list[str], categories_docs: dict[str, list[tuple[str]]]) -> list[dict[str, float]]:
    all_scores: list[dict[str, float]] = []
    for idx, text in enumerate(strings):
        tokens: list[str] = text.split()
        scores: dict[str, float] = {}
        for category, category_words in categories_docs.items():
            similarities = []
            for category_tokens in category_words:
                if len(category_tokens) <= len(tokens):
                    similarities.append(n_gram_jaccard_similarity(tokens, category_tokens, len(category_tokens)))
                else:
                    similarities.append(0.0)
            scores[category] = sum(similarities) / len(similarities)
        all_scores.append(scores)
    return all_scores


def calculate_n_gram_jaccard_similarity(
        strings: list[str],
        categories: dict[str, set[str]],
        batch_size: int = 500,
        workers: Optional[int] = None
) -> dict[int, dict[str, float]]:
    result: dict[int, dict[str, float]] = {}
    categories_docs: dict[str, list[tuple[str]]] = {k: [tuple(i.split()) for i in v] for k, v in categories.items()}
    with multiprocessing.Pool(processes=get_workers_size(1 / 2, workers)) as pool:
        with tqdm(total=math.ceil(len(strings) / batch_size), desc=f"Calculating batch similarity") as pbar:
            batch_tasks: dict = {}
            for i in range(0, len(strings), batch_size):
                batch_texts = strings[i:i + batch_size]
                batch_result = pool.apply_async(_calculate_n_gram_jaccard_similarity, (batch_texts, categories_docs), callback=lambda _: pbar.update(1))
                batch_tasks[i] = batch_result
            for start_idx, batch_task in batch_tasks.items():
                for score_idx, score in enumerate(batch_task.get()):
                    result[start_idx + score_idx] = score
    return result


def calculate_cosine_similarity(strings: list[str], categories: dict[str, set[str]], model: str, workers: int = 1) -> dict[int, dict[str, float]]:
    nlp = spacy.load(model)
    all_scores: dict[int, dict[str, float]] = {}
    with nlp.select_pipes(enable=["tok2vec"]):
        docs = nlp.pipe(strings, n_process=workers)
        category_docs = {k: nlp(" ".join(sorted([j for i in v for j in i.split()]))) for k, v in categories.items()}
        for idx, doc in enumerate(tqdm(docs, total=len(strings))):
            if doc.has_vector:
                all_scores[idx] = dict({c: doc.similarity(category_doc) for c, category_doc in category_docs.items()})
            else:
                all_scores[idx] = dict({c: 0.0 for c in category_docs})
    return all_scores


def _calculate_n_gram_similarity(strings: list[str], categories_docs: dict[str, list[tuple[str]]]) -> list[dict[str, float]]:
    all_scores: list[dict[str, float]] = []
    for idx, text in enumerate(strings):
        tokens: list[str] = text.split()
        scores: dict[str, float] = {}
        for category, category_words in categories_docs.items():
            similarities = []
            for category_tokens in category_words:
                if len(category_tokens) <= len(tokens):
                    tokens_pairs = n_gram(tokens, len(category_tokens))
                    similarities.append(tokens_pairs.count(category_tokens))
                else:
                    similarities.append(0.0)
            scores[category] = sum(similarities) / len(similarities)
        all_scores.append(scores)
    return all_scores


def calculate_n_gram_similarity(
        strings: list[str],
        categories: dict[str, set[str]],
        batch_size: int = 500,
        workers: Optional[int] = None
) -> dict[int, dict[str, float]]:
    result: dict[int, dict[str, float]] = {}
    categories_docs: dict[str, list[tuple[str]]] = {k: [tuple(i.split()) for i in v] for k, v in categories.items()}
    with multiprocessing.Pool(processes=get_workers_size(1 / 2, workers)) as pool:
        with tqdm(total=math.ceil(len(strings) / batch_size), desc=f"Calculating batch similarity") as pbar:
            batch_tasks: dict = {}
            for i in range(0, len(strings), batch_size):
                batch_texts = strings[i:i + batch_size]
                batch_result = pool.apply_async(_calculate_n_gram_similarity, (batch_texts, categories_docs), callback=lambda _: pbar.update(1))
                batch_tasks[i] = batch_result
            for start_idx, batch_task in batch_tasks.items():
                for score_idx, score in enumerate(batch_task.get()):
                    result[start_idx + score_idx] = score
    return result


def calculate_transformer_cosine_similarity(
        strings: list[str],
        categories: dict[str, set[str]],
        model: str,
        batch_size: int = 80000
) -> dict[int, dict[str, float]]:
    model = SentenceTransformer(model)

    print("Preparing categories embeddings")
    categories_embeddings = dict({c: model.encode(list(sorted(v)), convert_to_tensor=True) for c, v in categories.items()})

    result: dict[int, dict[str, float]] = {}
    total_text_batch = math.ceil(len(strings) / batch_size)
    for b, i in enumerate(range(0, len(strings), batch_size)):
        batch_texts = strings[i:i + batch_size]

        print(f"Preparing strings embeddings: {b + 1}/{total_text_batch}")
        strings_embeddings = model.encode(batch_texts, batch_size=256, convert_to_tensor=True, show_progress_bar=True)

        for category, category_embedding in tqdm(categories_embeddings.items(), total=len(categories_embeddings), desc=f"Calculating similarity"):
            matrix = util.cos_sim(strings_embeddings, category_embedding).tolist()
            for idx in range(len(matrix)):
                score = sum(matrix[idx]) / len(matrix[idx])
                key = i + idx
                if key in result:
                    result[key][category] = score
                else:
                    result[key] = {category: score}

        del strings_embeddings
        torch.cuda.empty_cache()
    del categories_embeddings
    torch.cuda.empty_cache()
    return result
