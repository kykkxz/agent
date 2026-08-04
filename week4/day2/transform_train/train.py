import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
from datasets import Dataset, DatasetDict
from torch.utils.data import DataLoader
from transformers import (
    BertForSequenceClassification,
    BertTokenizerFast,
    DataCollatorWithPadding,
    get_linear_schedule_with_warmup,
    set_seed,
)


MODEL_NAME = "bert-base-uncased"
LABEL_NAMES = {0: "negative", 1: "positive"}
SEED = 42
LEARNING_RATE = 2e-5
EPOCHS = 2
BATCH_SIZE = 16
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.1
MAX_LENGTH = 192


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-file", type=Path, default=Path("yelp_train.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--train-size", type=int, default=2000)
    parser.add_argument("--validation-size", type=int, default=500)
    parser.add_argument("--seed", type=int, default=SEED)
    return parser.parse_args()


def load_data(args: argparse.Namespace) -> DatasetDict:
    """Read only the requested JSON Lines rows and make a fixed split."""
    if not args.train_file.exists():
        raise FileNotFoundError(f"数据文件不存在: {args.train_file.resolve()}")
    if args.train_size <= 0 or args.validation_size <= 0:
        raise ValueError("train-size 和 validation-size 必须为正数")

    rows = []
    required = args.train_size + args.validation_size
    with args.train_file.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
            if len(rows) == required:
                break
    if len(rows) < required:
        raise ValueError(f"{args.train_file} 中的样本数不足")

    random.Random(args.seed).shuffle(rows)
    data = Dataset.from_list(rows)
    split = data.train_test_split(
        train_size=args.train_size,
        test_size=args.validation_size,
        seed=args.seed,
    )
    return DatasetDict(train=split["train"], validation=split["test"])


def tokenize_data(dataset: DatasetDict, tokenizer: BertTokenizerFast) -> DatasetDict:
    def tokenize_batch(batch: dict[str, list[str]]) -> dict[str, list[list[int]]]:
        return tokenizer(batch["text"], truncation=True, max_length=MAX_LENGTH)

    dataset = dataset.rename_column("label", "labels")
    return dataset.map(tokenize_batch, batched=True, remove_columns=["text"])


def macro_f1(predictions: np.ndarray, labels: np.ndarray) -> float:
    scores = []
    for label_id in (0, 1):
        true_positive = np.sum((predictions == label_id) & (labels == label_id))
        false_positive = np.sum((predictions == label_id) & (labels != label_id))
        false_negative = np.sum((predictions != label_id) & (labels == label_id))
        precision = true_positive / max(true_positive + false_positive, 1)
        recall = true_positive / max(true_positive + false_negative, 1)
        scores.append(2 * precision * recall / max(precision + recall, 1e-12))
    return float(np.mean(scores))


def evaluate(model, dataset, collator, device) -> dict[str, float]:
    loader = DataLoader(dataset, batch_size=32, collate_fn=collator)
    predictions, labels = [], []
    total_loss = 0.0
    total_examples = 0
    model.eval()
    with torch.no_grad():
        for batch in loader:
            batch_labels = batch["labels"]
            batch = {key: value.to(device) for key, value in batch.items()}
            output = model(**batch)
            count = batch_labels.shape[0]
            total_loss += output.loss.item() * count
            total_examples += count
            predictions.append(torch.argmax(output.logits, dim=-1).cpu().numpy())
            labels.append(batch_labels.numpy())

    predictions = np.concatenate(predictions)
    labels = np.concatenate(labels)
    return {
        "loss": total_loss / total_examples,
        "f1": macro_f1(predictions, labels),
        "accuracy": float(np.mean(predictions == labels)),
    }


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    data = load_data(args)
    tokenizer = BertTokenizerFast.from_pretrained(MODEL_NAME, local_files_only=True)
    data = tokenize_data(data, tokenizer)
    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = BertForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        id2label=LABEL_NAMES,
        label2id={name: label_id for label_id, name in LABEL_NAMES.items()},
        local_files_only=True,
    ).to(device)
    loader = DataLoader(
        data["train"],
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=collator,
        generator=torch.Generator().manual_seed(args.seed),
    )
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )
    total_steps = len(loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * WARMUP_RATIO),
        num_training_steps=total_steps,
    )

    print(f"device={device}; train={len(data['train'])}; validation={len(data['validation'])}")
    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0
        for batch in loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()
            train_loss += loss.item()

        metrics = evaluate(model, data["validation"], collator, device)
        print(
            f"epoch {epoch}: train_loss={train_loss / len(loader):.4f}, "
            f"val_loss={metrics['loss']:.4f}, val_f1={metrics['f1']:.4f}, "
            f"val_accuracy={metrics['accuracy']:.4f}"
        )

    output_dir = args.output_dir / "final_model"
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"模型已保存到: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
