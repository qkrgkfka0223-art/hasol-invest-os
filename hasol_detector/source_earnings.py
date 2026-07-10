from __future__ import annotations

import pandas as pd


def load_earnings_seed_candidates() -> pd.DataFrame:
    """Earnings-led discovery candidates.

    These names are added to force the detector to watch the event class that
    HASOL ranks highest: earnings surprise / guidance / backlog / margin.
    """
    rows = [
        ("ANF", "Abercrombie & Fitch", "earnings beat and retail margin expansion watch"),
        ("GAP", "Gap", "earnings beat and retail turnaround watch"),
        ("CROX", "Crocs", "earnings beat/value rebound watch"),
        ("ONON", "On Holding", "earnings growth and consumer momentum watch"),
        ("DECK", "Deckers Outdoor", "earnings quality consumer momentum watch"),
        ("ELF", "e.l.f. Beauty", "earnings growth consumer product catalyst watch"),
        ("CELH", "Celsius", "earnings growth and distribution catalyst watch"),
        ("CAVA", "Cava", "earnings growth restaurant momentum watch"),
        ("SHAK", "Shake Shack", "earnings margin expansion restaurant watch"),
        ("WING", "Wingstop", "earnings growth restaurant momentum watch"),
        ("AXON", "Axon Enterprise", "earnings beat and public safety contract watch"),
        ("HUBB", "Hubbell", "earnings strength electrical infrastructure watch"),
        ("FIX", "Comfort Systems", "earnings backlog data center/HVAC watch"),
        ("EME", "EMCOR", "earnings backlog electrical infrastructure watch"),
        ("STRL", "Sterling Infrastructure", "earnings backlog infrastructure watch"),
        ("GVA", "Granite Construction", "earnings backlog infrastructure watch"),
        ("ATRO", "Astronics", "earnings aerospace recovery watch"),
        ("HWM", "Howmet Aerospace", "earnings aerospace supply chain strength watch"),
        ("TDG", "TransDigm", "earnings aerospace margin strength watch"),
        ("HEI", "HEICO", "earnings aerospace component strength watch"),
        ("FTAI", "FTAI Aviation", "earnings aviation aftermarket catalyst watch"),
        ("APP", "AppLovin", "earnings beat AI ad software watch"),
        ("TTD", "Trade Desk", "earnings digital advertising catalyst watch"),
        ("SHOP", "Shopify", "earnings commerce platform catalyst watch"),
        ("MELI", "MercadoLibre", "earnings ecommerce/fintech strength watch"),
        ("SE", "Sea Limited", "earnings gaming/ecommerce turnaround watch"),
        ("DUOL", "Duolingo", "earnings AI product growth watch"),
        ("TOST", "Toast", "earnings restaurant software growth watch"),
        ("IOT", "Samsara", "earnings IoT/software growth watch"),
        ("ESTC", "Elastic", "earnings AI search/data platform watch"),
    ]
    return pd.DataFrame([
        {
            "ticker": t,
            "company": c,
            "candidate_source": "earnings_seed",
            "source_reason": reason,
            "headline": reason,
            "source_confidence": "DISCOVERY_ONLY",
            "requires_web_validation": True,
        }
        for t, c, reason in rows
    ])
