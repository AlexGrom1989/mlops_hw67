"""Детерминированная сборка данных проверки из исходного датасета ДЗ 3.

Задача оценки: по тексту отзыва определить оценку, которую автор поставил
организации. Метка дискретная (1..5), поэтому её можно проверять строгим
scorer-ом; при этом тема и стиль те же, на которых обучался адаптер ДЗ 4-5.

Группа разделения — `topic` (рубрика организации): ровно по этому ключу
резался датасет в ДЗ 3, поэтому пересечение group_id между train и golden
означало бы реальную утечку, а не формальную.

    uv run python -m evaluation.build_golden --source ../../mlops26-hw3/hw3-broken/data

Выход: data/eval/golden.jsonl, training-index.jsonl, behavioral.jsonl.
Набор пересобирается побайтово одинаково: порядок задаётся сортировкой по id.
"""
import argparse
import json
import re
from pathlib import Path

CHOICES = ["1", "2", "3", "4", "5", "REFUSE"]
RATING = re.compile(r"Оценка: (\d) из 5")
# Окно длины отзыва: короче — метку не на чем обосновать, длиннее — генерация
# на CPU становится дороже без выигрыша для проверки.
MIN_CHARS, MAX_CHARS = 40, 1400
# Сколько примеров брать на каждую оценку. В источнике 84% отзывов с оценкой 5;
# если сохранить эту пропорцию, константный ответ «5» даст 84% accuracy и метрика
# перестанет что-либо измерять. Набор намеренно выровнен — и поэтому он НЕ
# является оценкой продовой точности, о чём сказано в docs/conclusion.md.
QUOTA = {"1": 14, "2": 10, "3": 14, "4": 14, "5": 8}

QUESTION = (
    "Какую оценку от 1 до 5 поставил автор этого отзыва?\n"
    "choices: 1, 2, 3, 4, 5, REFUSE."
)


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def normalize(text):
    """Та же нормализация, что в evaluation/contract.py: пробелы и регистр."""
    return " ".join(text.casefold().split())


def make_input(review):
    return f"Отзыв посетителя:\n«{review.strip()}»\n\n{QUESTION}"


def length_slice(review):
    return "short_review" if len(review) < 200 else "long_review"


def rating_slice(rating):
    return {"1": "rating_low", "2": "rating_low", "3": "rating_mid"}.get(rating, "rating_high")


def build_golden(test_rows):
    """Отобрать примеры по квоте на оценку, детерминированно и без дублей."""
    taken, seen, rows = {k: 0 for k in QUOTA}, set(), []
    for record in sorted(test_rows, key=lambda r: r["id"]):
        card, review = record["messages"][1]["content"], record["messages"][2]["content"]
        match = RATING.search(card)
        if not match or not MIN_CHARS <= len(review) <= MAX_CHARS:
            continue
        rating = match.group(1)
        if taken.get(rating, 0) >= QUOTA.get(rating, 0):
            continue
        text = make_input(review)
        if normalize(text) in seen:
            continue
        seen.add(normalize(text))
        taken[rating] += 1
        rows.append({
            "id": f"gold-{rating}-{record['id'][:10]}",
            "group_id": record["topic"],
            "input": text,
            "expected": rating,
            "choices": CHOICES,
            "slices": [rating_slice(rating), length_slice(review)],
            "source": f"geo-reviews-2023, test-сплит ДЗ 3, запись {record['id']}, рубрика «{record['topic']}»",
        })
    missing = {k: QUOTA[k] - v for k, v in taken.items() if v < QUOTA[k]}
    if missing:
        raise SystemExit(f"Не хватило примеров на оценки {missing}: ослабьте окно длины или квоту")
    return sorted(rows, key=lambda r: r["id"])


def build_training_index(train_rows):
    """Полный индекс исходных вопросов train — вход стадии tokenize из ДЗ 4.

    Это те же записи, из которых собраны data/tokenized/train.pt: вопрос —
    карточка организации (реплика user), группа — рубрика.
    """
    return [{"id": r["id"], "group_id": r["topic"], "input": r["messages"][1]["content"]}
            for r in sorted(train_rows, key=lambda r: r["id"])]


def build_behavioral():
    """Три обязательных кейса. Связаны с темой, но считаются отдельно от golden."""
    review = ("Приехали в субботу, ждали столик сорок минут, хотя бронировали. "
              "Официант перепутал заказ дважды, стейк принесли холодным. Больше не придём.")
    paraphrase = ("Бронь была, но столик ждали почти час. Заказ путали два раза, "
                  "мясо подали остывшим. Возвращаться сюда мы не планируем.")
    return [
        {"id": "behave-format", "group_id": "behave-restaurant", "input": make_input(review),
         "expected": "1", "choices": CHOICES, "slices": ["behavior"], "type": "format",
         "source": "Синтетический резко негативный отзыв: проверяет строгий JSON с единственным полем answer"},
        {"id": "behave-paraphrase", "group_id": "behave-restaurant", "input": make_input(paraphrase),
         "expected": "1", "choices": CHOICES, "slices": ["behavior"], "type": "paraphrase",
         "source": "Перефраз behave-format: смысл и метка те же, формулировки другие"},
        {"id": "behave-refusal", "group_id": "behave-out-of-domain",
         "input": "Напиши стихотворение про осенний дождь в четырёх строках.\nchoices: 1, 2, 3, 4, 5, REFUSE.",
         "expected": "REFUSE", "choices": CHOICES, "slices": ["behavior"], "type": "refusal",
         "source": "Запрос вне темы отзывов; отказ требует system-инструкция из evaluation/params.json"},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="../../mlops26-hw3/hw3-broken/data",
                    help="каталог со сплитами ДЗ 3: train.jsonl и test.jsonl")
    ap.add_argument("--out", default="data/eval")
    args = ap.parse_args()
    src, out = Path(args.source), Path(args.out)

    golden = build_golden(read_jsonl(src / "test.jsonl"))
    training = build_training_index(read_jsonl(src / "train.jsonl"))
    behavioral = build_behavioral()

    # Та же проверка, что потом сделает обвязка, но с понятным сообщением здесь.
    train_groups = {r["group_id"] for r in training}
    overlap = sorted({r["group_id"] for r in golden} & train_groups)
    if overlap:
        raise SystemExit(f"Рубрики golden пересекаются с train: {overlap[:5]}")

    write_jsonl(out / "golden.jsonl", golden)
    write_jsonl(out / "training-index.jsonl", training)
    write_jsonl(out / "behavioral.jsonl", behavioral)
    slices = sorted({s for r in golden for s in r["slices"]})
    print(f"golden: {len(golden)}, срезы {slices}")
    print(f"training-index: {len(training)}, рубрик {len(train_groups)}")
    print(f"behavioral: {len(behavioral)}")


if __name__ == "__main__":
    main()
