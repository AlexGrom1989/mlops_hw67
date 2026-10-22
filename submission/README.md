# Комплект сдачи ДЗ 6+7

`metrics/` исключён `.gitignore` как генерируемый каталог, поэтому отчёты
продублированы здесь. Они воспроизводятся командами из корневого README;
руками не правились.

## Ссылки на runs в MLflow

Сервер поднимается `make up`, UI — http://127.0.0.1:5006. Эксперимент `hw6-lora` (id 1).

Родительский run sweep: `a7889e8365e24c61aa2d89bbb0a4cab5`
[открыть](http://127.0.0.1:5006/#/experiments/1/runs/a7889e8365e24c61aa2d89bbb0a4cab5)

| конфигурация | run_id | final/base val | ссылка |
|---|---|---:|---|
| all-r8-high | `0f060a1fb67447948f2c4243d9abd311` | 0.8909 | [run](http://127.0.0.1:5006/#/experiments/1/runs/0f060a1fb67447948f2c4243d9abd311) |
| qv-r8-high | `f168deeadf1e41beb72579c139f940c5` | 0.9256 | [run](http://127.0.0.1:5006/#/experiments/1/runs/f168deeadf1e41beb72579c139f940c5) |
| all-r8-low | `8fbface1321348b8969ef557bb9f7e27` | 0.9365 | [run](http://127.0.0.1:5006/#/experiments/1/runs/8fbface1321348b8969ef557bb9f7e27) |
| qv-r4-high | `df6da1ff3dd940d7b24e8892f3781123` | 0.9521 | [run](http://127.0.0.1:5006/#/experiments/1/runs/df6da1ff3dd940d7b24e8892f3781123) |
| qv-r8-low | `e388efe373684b8fa67a0e0254b34a0c` | 0.9700 | [run](http://127.0.0.1:5006/#/experiments/1/runs/e388efe373684b8fa67a0e0254b34a0c) |
| qv-r4-low | `c32ffa8e366644a7bcf39659bb902779` | 0.9830 | [run](http://127.0.0.1:5006/#/experiments/1/runs/c32ffa8e366644a7bcf39659bb902779) |

- Кандидат: `models:/my-qwen-adapter/1`, alias `candidate`, run `0f060a1fb67447948f2c4243d9abd311`
- `champion`: **не назначен** — гейт качества отказал
- Eval run (эксперимент `hw67-evaluation`): `d11b8c16c4bb459fa80e7cfc3a94b0c3`
- Probe хранения: run `bfef0f998c96446eb9f162549f863e55`
- Демонстрация сломанного sweep: эксперимент `hw6-lora-broken-demo`

## Состав

| файл | что это |
|---|---|
| `metrics/sweep.json` | шесть runs, provenance кода/конфига/данных |
| `metrics/candidate-model.json` | выбранная версия реестра |
| `metrics/baseline-outputs.json` | сырые ответы базовой модели, 63 строки |
| `metrics/candidate-outputs.json` | сырые ответы кандидата, 63 строки |
| `metrics/baseline-eval.json` | отчёт базы: overall, срезы, per_item, behavioral |
| `metrics/candidate-eval.json` | отчёт кандидата |
| `metrics/eval-diff.json` | исправленные и потерянные id |
| `metrics/quality-gate.json` | решение гейта: **passed=false** |
| `metrics/negative-gate.json` | отказ на испорченной копии ответов |
| `metrics/storage-check.json` | probe, переживший пересоздание контейнера |

Итог гейта: `Регрессия по accuracy: 0.2333 против 0.3000`

## Данные проверки

`data/eval/{golden,training-index,behavioral}.jsonl` версионируются DVC,
указатели `.dvc` лежат в Git. Восстановление:

```bash
dvc pull                      # удалённое хранилище прописано в .dvc/config
```

Если хранилище недоступно, набор пересобирается побайтово из исходных
сплитов ДЗ 3 (нужен каталог с `train.jsonl` и `test.jsonl`):

```bash
uv run python -m evaluation.build_golden --source <путь к data ДЗ 3>
```

Проверить совпадение: md5 `golden.jsonl` должен быть равен значению
в `data/eval/golden.jsonl.dvc`.
