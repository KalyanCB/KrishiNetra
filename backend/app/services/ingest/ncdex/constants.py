"""NCDEX public EOD bhav ingest constants (FUTURES_SIGNAL_PROTOTYPE §5)."""

from __future__ import annotations

from decimal import Decimal

from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID

# KAPAS Shankar contract symbols (legacy KAPASSRNR excluded per NCDEX circulars).
KAPAS_SYMBOLS: frozenset[str] = frozenset({"KAPAS", "SHANKRKPAS"})

# NCDEX KAPAS seasonal launch months (Nov / Feb / Apr).
KAPAS_EXPIRY_MONTHS: frozenset[int] = frozenset({11, 2, 4})

SOURCE_NCDEX_PUBLIC_BHAV = "ncdex_public_bhav_prototype"
ENVIRONMENT_PROTOTYPE = "prototype"

# NCDEX KAPAS quote unit: ₹ per 20 kg → ₹/quintal multiplier.
INR_PER_20KG_TO_QUINTAL = Decimal("5")
DEFAULT_QUOTE_UNIT = "INR_per_20kg"
DEFAULT_QUINTAL_UNIT = "INR_per_quintal"

COMMODITY_ID = COTTON_COMMODITY_ID

# UDiFF bhav series filter.
FUTURES_SERIES = frozenset({"FUT", "FUTCOM", "FUTIDX"})
