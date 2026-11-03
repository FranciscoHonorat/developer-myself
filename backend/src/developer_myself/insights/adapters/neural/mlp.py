"""Uma rede neural (MLP) do zero, só com a stdlib — para enxergar a matemática.

Arquitetura: entrada (n) → camada oculta (tanh) → 1 saída (sigmoid) = probabilidade.

    z1 = W1·x + b1        h = tanh(z1)
    z2 = w2·h + b2        y = sigmoid(z2)
    perda = entropia cruzada binária: -[t·log(y) + (1-t)·log(1-y)]

Backpropagation (regra da cadeia, de trás para frente):
    dL/dz2 = y - t                       (sigmoid + entropia cruzada se simplificam)
    dL/dw2 = dL/dz2 · h                  dL/db2 = dL/dz2
    dL/dh  = dL/dz2 · w2
    dL/dz1 = dL/dh · (1 - h²)            (derivada da tanh)
    dL/dW1 = dL/dz1 · xᵀ                 dL/db1 = dL/dz1

Melhorias de treino (v2):
- **Mini-batch**: média do gradiente de B exemplos → passos menos ruidosos que SGD puro.
- **Pesos por amostra**: um rótulo real (sua autoavaliação) vale mais que um sintético.
- **L2 (weight decay)**: soma λ·w ao gradiente dos pesos → pune pesos grandes, reduz overfitting.
- **Adam**: cada parâmetro tem seu próprio passo, adaptado pela média (m) e pela
  variância (v) dos gradientes recentes. Converge mais rápido e com menos ajuste fino.
      m = β1·m + (1-β1)·g          v = β2·v + (1-β2)·g²
      m̂ = m/(1-β1ᵗ)                v̂ = v/(1-β2ᵗ)        (correção do viés inicial)
      θ = θ - lr · m̂ / (√v̂ + ε)
- **Early stopping**: acompanha a perda num conjunto de VALIDAÇÃO (que não treina) e para
  quando ela piora por `patience` épocas, restaurando os melhores pesos.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Any

Vector = list[float]
Matrix = list[list[float]]


def sigmoid(z: float) -> float:
    if z >= 0:  # forma estável: evita overflow em exp() para z muito negativo
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def binary_cross_entropy(y: float, target: float, eps: float = 1e-12) -> float:
    y = min(max(y, eps), 1 - eps)
    return -(target * math.log(y) + (1 - target) * math.log(1 - y))


@dataclass(slots=True)
class Gradients:
    w1: Matrix
    b1: Vector
    w2: Vector
    b2: float

    def flat(self) -> Vector:
        return [g for row in self.w1 for g in row] + self.b1 + self.w2 + [self.b2]


@dataclass(slots=True)
class Adam:
    learning_rate: float = 0.01
    beta1: float = 0.9
    beta2: float = 0.999
    eps: float = 1e-8
    _m: Vector = field(default_factory=list)
    _v: Vector = field(default_factory=list)
    _t: int = 0

    def update(self, params: Vector, grads: Vector) -> Vector:
        if not self._m:
            self._m = [0.0] * len(params)
            self._v = [0.0] * len(params)
        self._t += 1
        b1, b2 = self.beta1, self.beta2
        correction1 = 1 - b1**self._t
        correction2 = 1 - b2**self._t
        updated = []
        for i, (p, g) in enumerate(zip(params, grads, strict=True)):
            self._m[i] = b1 * self._m[i] + (1 - b1) * g
            self._v[i] = b2 * self._v[i] + (1 - b2) * g * g
            m_hat = self._m[i] / correction1
            v_hat = self._v[i] / correction2
            updated.append(p - self.learning_rate * m_hat / (math.sqrt(v_hat) + self.eps))
        return updated


@dataclass(frozen=True, slots=True)
class FitResult:
    train_loss: list[float]
    val_loss: list[float]
    best_epoch: int
    stopped_early: bool


class MLP:
    def __init__(self, n_inputs: int, n_hidden: int, seed: int = 42) -> None:
        rng = random.Random(seed)
        # Inicialização de Xavier/Glorot: mantém a variância estável entre camadas.
        limit1 = math.sqrt(6 / (n_inputs + n_hidden))
        limit2 = math.sqrt(6 / (n_hidden + 1))
        self.w1: Matrix = [
            [rng.uniform(-limit1, limit1) for _ in range(n_inputs)] for _ in range(n_hidden)
        ]
        self.b1: Vector = [0.0] * n_hidden
        self.w2: Vector = [rng.uniform(-limit2, limit2) for _ in range(n_hidden)]
        self.b2: float = 0.0

    @property
    def n_inputs(self) -> int:
        return len(self.w1[0])

    @property
    def n_hidden(self) -> int:
        return len(self.w1)

    # ------------------------------------------------------------------ forward
    def hidden(self, x: Vector) -> Vector:
        return [
            math.tanh(sum(w * xi for w, xi in zip(row, x, strict=True)) + b)
            for row, b in zip(self.w1, self.b1, strict=True)
        ]

    def predict(self, x: Vector) -> float:
        h = self.hidden(x)
        return sigmoid(sum(w * hi for w, hi in zip(self.w2, h, strict=True)) + self.b2)

    def loss(self, xs: list[Vector], targets: list[float], weights: Vector | None = None) -> float:
        ws = weights or [1.0] * len(xs)
        total = sum(
            w * binary_cross_entropy(self.predict(x), t)
            for x, t, w in zip(xs, targets, ws, strict=True)
        )
        return total / sum(ws)

    # ------------------------------------------------------------------ backward
    def gradients(self, x: Vector, target: float) -> Gradients:
        h = self.hidden(x)
        y = sigmoid(sum(w * hi for w, hi in zip(self.w2, h, strict=True)) + self.b2)
        dz2 = y - target
        dw2 = [dz2 * hi for hi in h]
        dz1 = [dz2 * w * (1 - hi * hi) for w, hi in zip(self.w2, h, strict=True)]
        dw1 = [[d * xi for xi in x] for d in dz1]
        return Gradients(w1=dw1, b1=dz1, w2=dw2, b2=dz2)

    def batch_gradient(
        self, xs: list[Vector], targets: list[float], weights: Vector, l2: float
    ) -> Vector:
        """Média ponderada dos gradientes do lote + L2 só nos pesos (não nos vieses)."""
        total_weight = sum(weights)
        acc = [0.0] * self.n_params
        for x, t, w in zip(xs, targets, weights, strict=True):
            for i, g in enumerate(self.gradients(x, t).flat()):
                acc[i] += w * g
        grads = [g / total_weight for g in acc]
        params = self.params()
        for i in self._weight_indices():
            grads[i] += l2 * params[i]
        return grads

    # ------------------------------------------------------------------ parâmetros
    @property
    def n_params(self) -> int:
        return self.n_hidden * self.n_inputs + 2 * self.n_hidden + 1

    def params(self) -> Vector:
        return [w for row in self.w1 for w in row] + self.b1 + self.w2 + [self.b2]

    def set_params(self, flat: Vector) -> None:
        n_in, n_h = self.n_inputs, self.n_hidden
        k = n_in * n_h
        self.w1 = [flat[i * n_in : (i + 1) * n_in] for i in range(n_h)]
        self.b1 = flat[k : k + n_h]
        self.w2 = flat[k + n_h : k + 2 * n_h]
        self.b2 = flat[k + 2 * n_h]

    def _weight_indices(self) -> range | list[int]:
        k = self.n_inputs * self.n_hidden
        return list(range(k)) + list(range(k + self.n_hidden, k + 2 * self.n_hidden))

    def step(self, grads: Gradients, learning_rate: float) -> None:
        """Descida do gradiente simples (SGD): anda contra o gradiente."""
        self.set_params(
            [p - learning_rate * g for p, g in zip(self.params(), grads.flat(), strict=True)]
        )

    # ------------------------------------------------------------------ treino
    def fit(
        self,
        xs: list[Vector],
        targets: list[float],
        *,
        weights: Vector | None = None,
        epochs: int = 100,
        learning_rate: float = 0.01,
        batch_size: int = 32,
        l2: float = 1e-4,
        validation: tuple[list[Vector], list[float]] | None = None,
        patience: int = 8,
        seed: int = 0,
    ) -> FitResult:
        rng = random.Random(seed)
        ws = weights or [1.0] * len(xs)
        optimizer = Adam(learning_rate=learning_rate)
        order = list(range(len(xs)))
        train_hist: list[float] = []
        val_hist: list[float] = []
        best = (math.inf, 0, self.params())
        for epoch in range(epochs):
            rng.shuffle(order)
            for start in range(0, len(order), batch_size):
                idx = order[start : start + batch_size]
                grads = self.batch_gradient(
                    [xs[i] for i in idx], [targets[i] for i in idx], [ws[i] for i in idx], l2
                )
                self.set_params(optimizer.update(self.params(), grads))
            train_hist.append(self.loss(xs, targets, ws))
            if validation is None:
                continue
            val_hist.append(self.loss(*validation))
            if val_hist[-1] < best[0] - 1e-5:
                best = (val_hist[-1], epoch, self.params())
            elif epoch - best[1] >= patience:
                self.set_params(best[2])
                return FitResult(train_hist, val_hist, best[1], stopped_early=True)
        if validation is not None:
            self.set_params(best[2])
        return FitResult(train_hist, val_hist, best[1], stopped_early=False)

    # ------------------------------------------------------------------ persistência
    def to_dict(self) -> dict[str, Any]:
        return {"w1": self.w1, "b1": self.b1, "w2": self.w2, "b2": self.b2}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MLP:
        model = cls(n_inputs=len(data["w1"][0]), n_hidden=len(data["w1"]))
        model.w1 = [list(map(float, row)) for row in data["w1"]]
        model.b1 = list(map(float, data["b1"]))
        model.w2 = list(map(float, data["w2"]))
        model.b2 = float(data["b2"])
        return model
