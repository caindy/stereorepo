"""Brownfield repository adoption planning library (stereorepo's DR-344).

Provides data structures, path classification, and collision-aware planning
to adapt existing Product repositories into stereorepo management.
"""

from __future__ import annotations

from lib.adapt.plan import (
    DEFAULT_IGNORES,
    DEFAULT_INTEGRATIONS,
    AdoptionPlan,
    PathClassification,
    PlannedAction,
    ProductConfig,
    build_adoption_plan,
    load_product_config,
)
from lib.bundle import load_bundle

__all__ = [
    "DEFAULT_IGNORES",
    "DEFAULT_INTEGRATIONS",
    "AdoptionPlan",
    "PathClassification",
    "PlannedAction",
    "ProductConfig",
    "build_adoption_plan",
    "load_bundle",
    "load_product_config",
]
