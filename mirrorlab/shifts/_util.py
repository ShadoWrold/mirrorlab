"""Shared sampling + integrator helpers for catalog shifts."""

from __future__ import annotations

import math
from typing import Callable

import numpy as np


def loguniform(rng: np.random.Generator, lo: float, hi: float) -> float:
    return float(np.exp(rng.uniform(math.log(lo), math.log(hi))))
