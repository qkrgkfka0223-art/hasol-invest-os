from __future__ import annotations

import pandas as pd


def load_price_mover_seed_candidates() -> pd.DataFrame:
    """Expanded discovery candidates for price/RS/momentum screening.

    This is not a verified buy list. It is a broad candidate source used so the
    detector can fetch prices and then eliminate overextended names.
    """
    rows = [
        ("RXT", "Rackspace Technology", "AI compute/data-center price follow-through watch"),
        ("INMD", "InMode", "quiet relative strength medical devices watch"),
        ("ATHM", "Autohome", "ADR stabilization relative strength watch"),
        ("UAA", "Under Armour", "turnaround retail relative strength watch"),
        ("SOUN", "SoundHound AI", "AI software momentum watch"),
        ("LUNR", "Intuitive Machines", "space contract momentum watch"),
        ("RKLB", "Rocket Lab", "space launch/defense relative strength watch"),
        ("ASTS", "AST SpaceMobile", "satellite-to-phone momentum watch"),
        ("BEEM", "Beam Global", "energy storage/patent momentum watch"),
        ("CRVO", "CervoMed", "biotech relative strength watch"),
        ("IVDA", "Iveda Solutions", "AI video analytics low-cap momentum watch"),
        ("SUGP", "SU Group", "contract/distribution low-cap momentum watch"),
        ("VRT", "Vertiv", "AI data center power/cooling relative strength watch"),
        ("ANET", "Arista Networks", "AI data center networking relative strength watch"),
        ("DELL", "Dell Technologies", "AI server backlog relative strength watch"),
        ("HPE", "Hewlett Packard Enterprise", "AI server/networking relative strength watch"),
        ("SMCI", "Super Micro Computer", "AI server infrastructure watch"),
        ("MU", "Micron", "memory cycle relative strength watch"),
        ("WDC", "Western Digital", "storage cycle relative strength watch"),
        ("STX", "Seagate", "storage cycle relative strength watch"),
        ("MRVL", "Marvell", "AI custom silicon/networking watch"),
        ("ARM", "Arm Holdings", "AI semiconductor architecture watch"),
        ("AVGO", "Broadcom", "AI accelerator/networking relative strength watch"),
        ("AMD", "Advanced Micro Devices", "AI compute partner momentum watch"),
        ("NVDA", "NVIDIA", "AI leader benchmark watch, widely known"),
        ("PLTR", "Palantir", "AI software benchmark watch, widely known"),
        ("IESC", "IES Holdings", "electrical infrastructure earnings momentum watch"),
        ("LOAR", "Loar Holdings", "aerospace/defense component relative strength watch"),
        ("MIRM", "Mirum Pharmaceuticals", "biotech commercial execution strength watch"),
        ("CAI", "Caris Life Sciences", "diagnostics IPO/healthcare strength watch"),
        ("NPB", "Northpointe Bancshares", "regional bank quiet relative strength watch"),
        ("TER", "Teradyne", "semiconductor test equipment rebound watch"),
        ("RBC", "RBC Bearings", "industrial/aerospace quiet relative strength watch"),
        ("AMAT", "Applied Materials", "semiconductor equipment rebound watch"),
        ("KLAC", "KLA", "semiconductor process control rebound watch"),
        ("LRCX", "Lam Research", "semiconductor equipment rebound watch"),
        ("QCOM", "Qualcomm", "edge AI/mobile chip rebound watch"),
        ("ORCL", "Oracle", "AI cloud/data center backlog watch"),
        ("CEG", "Constellation Energy", "AI data center power demand watch"),
        ("ETN", "Eaton", "electrical infrastructure/data center demand watch"),
        ("PWR", "Quanta Services", "grid/electrical infrastructure demand watch"),
    ]
    return pd.DataFrame([
        {
            "ticker": t,
            "company": c,
            "candidate_source": "price_mover_seed",
            "source_reason": reason,
            "headline": reason,
            "source_confidence": "DISCOVERY_ONLY",
            "requires_web_validation": True,
        }
        for t, c, reason in rows
    ])
