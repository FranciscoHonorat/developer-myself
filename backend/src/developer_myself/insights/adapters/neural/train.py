"""Treina o modelo-base empacotado (`model.json`) só com dados sintéticos: `make train`.

É o modelo que a API usa antes de existir qualquer modelo no registro (cold start).
Com rótulos reais, quem treina é o retreino automático (`retrain.py`).
"""

import argparse
import json
from pathlib import Path

from developer_myself.insights.adapters.neural.recommender import DEFAULT_MODEL_PATH
from developer_myself.insights.adapters.neural.training import TrainingConfig, train_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--epochs", type=int, default=TrainingConfig().epochs)
    parser.add_argument("--hidden", type=int, default=TrainingConfig().hidden)
    args = parser.parse_args()

    trained = train_model([], TrainingConfig(epochs=args.epochs, hidden=args.hidden))
    args.out.write_text(json.dumps(trained.payload(), indent=1))
    metrics = trained.metrics
    width = max(map(len, metrics))
    for key, value in metrics.items():
        print(f"{key:<{width}}  {value}")
    gain = 1 - metrics["test_log_loss"] / metrics["baseline_log_loss"]
    print(f"\nModelo salvo em {args.out}")
    print(f"A rede erra {gain:.0%} menos que chutar a média (log loss: quanto menor, melhor).")


if __name__ == "__main__":
    main()
