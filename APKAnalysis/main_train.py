import os

import torch
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
from transformers import AutoTokenizer, AlbertForSequenceClassification, AlbertTokenizerFast

from apk_analysis.dataset import load_dataset, TextDataset

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# %%
DATASET_DIR = os.path.join(".", "resources", "dataset")
PRIVACY_TYPES_COSINE_DATASET_PATH = os.path.join(DATASET_DIR, "privacy_types_cosine_dataset.json")
PRIVACY_TYPES_N_GRAM_DATASET_PATH = os.path.join(DATASET_DIR, "privacy_types_n_gram_dataset.json")


class SimpleDataset(Dataset):
    def __init__(self, tokenizer: AlbertTokenizerFast, texts: list[str], labels: list[float], max_length: int):
        self._tokenizer = tokenizer
        self._texts = texts
        self._labels = labels
        self._max_length = max_length

    def __getitem__(self, index: int):
        input_tensors = self._tokenizer.encode_plus(self._texts[index], max_length=self._max_length, padding="max_length", truncation=True, return_tensors="pt")
        label_tensor = torch.tensor(self._labels[index], dtype=torch.float32)
        return input_tensors['input_ids'].squeeze(), input_tensors['attention_mask'].squeeze(), label_tensor

    def __len__(self) -> int:
        return len(self._texts)


def main():
    print("GPU:", [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])

    # text_dataset: TextDataset = load_dataset(PRIVACY_TYPES_COSINE_DATASET_PATH)
    text_dataset: TextDataset = load_dataset(PRIVACY_TYPES_N_GRAM_DATASET_PATH)

    category_names = text_dataset.categories

    tokenizer: AlbertTokenizerFast = AutoTokenizer.from_pretrained("albert-base-v2")

    train_texts, test_texts, train_labels, test_labels = train_test_split(text_dataset.contents, text_dataset.labels, test_size=0.4, random_state=9326)
    test_texts, val_texts, test_labels, val_labels = train_test_split(test_texts, test_labels, test_size=0.5, random_state=22912)

    max_token_vector_length = 50

    train_dataset = SimpleDataset(tokenizer, train_texts, train_labels, max_token_vector_length)
    test_dataset = SimpleDataset(tokenizer, test_texts, test_labels, max_token_vector_length)
    val_dataset = SimpleDataset(tokenizer, val_texts, val_labels, max_token_vector_length)

    batch_size = 32
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=True)

    learning_rate = 0.00001

    model: torch.nn.Module = AlbertForSequenceClassification.from_pretrained(
        "albert-base-v2",
        num_labels=len(category_names),
        problem_type="multi_label_classification"
    ).to(DEVICE)

    criterion: torch.nn.BCEWithLogitsLoss = torch.nn.BCEWithLogitsLoss().to(DEVICE)
    optimizer: torch.optim.AdamW = torch.optim.AdamW(model.parameters(), lr=learning_rate)

    epoch_num = 100

    model.train()

    for epoch in range(epoch_num):
        with tqdm(total=len(train_loader), desc=f"Epoch {epoch + 1}/{epoch_num}") as pbar:
            total_loss = []
            for input_ids, attention_mask, target_labels in train_loader:
                input_ids, attention_mask, target_labels = input_ids.to(DEVICE), attention_mask.to(DEVICE), target_labels.to(DEVICE)
                optimizer.zero_grad()

                outputs = model(input_ids, attention_mask=attention_mask)[0]

                loss = criterion(outputs, target_labels.float())
                loss.backward()

                optimizer.step()

                total_loss.append(loss.item())

                pbar.set_postfix({"Loss": loss.item(), "Avg loss": sum(total_loss) / len(total_loss)})


if __name__ == "__main__":
    main()
