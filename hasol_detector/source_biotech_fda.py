from __future__ import annotations

import pandas as pd


def load_biotech_fda_seed_candidates() -> pd.DataFrame:
    """Biotech/FDA discovery candidates.

    Biotech names are discovery-only by default. Execution remains locked until
    event timing, cash runway, dilution risk, and trial/FDA text are validated.
    """
    rows = [
        ("VKTX", "Viking Therapeutics", "Phase 2/Phase 3 obesity drug clinical catalyst watch"),
        ("TGTX", "TG Therapeutics", "biotech commercial execution/FDA label catalyst watch"),
        ("IOVA", "Iovance Biotherapeutics", "FDA approval/commercial launch biotech catalyst watch"),
        ("CRSP", "CRISPR Therapeutics", "gene editing clinical/FDA catalyst watch"),
        ("NTLA", "Intellia Therapeutics", "gene editing clinical catalyst watch"),
        ("EDIT", "Editas Medicine", "gene editing clinical catalyst watch"),
        ("BEAM", "Beam Therapeutics", "base editing clinical catalyst watch"),
        ("RXRX", "Recursion Pharmaceuticals", "AI drug discovery partnership catalyst watch"),
        ("SDGR", "Schrodinger", "AI drug discovery earnings/partnership watch"),
        ("KURA", "Kura Oncology", "Phase 3/oncology clinical catalyst watch"),
        ("ARWR", "Arrowhead Pharmaceuticals", "RNA therapeutics clinical catalyst watch"),
        ("AKRO", "Akero Therapeutics", "MASH/NASH clinical catalyst watch"),
        ("ETNB", "89bio", "MASH/NASH clinical catalyst watch"),
        ("MDGL", "Madrigal Pharmaceuticals", "FDA/commercial launch biotech catalyst watch"),
        ("CYTK", "Cytokinetics", "FDA/NDA cardiac drug catalyst watch"),
        ("BBIO", "BridgeBio Pharma", "FDA/commercial launch rare disease catalyst watch"),
        ("ALNY", "Alnylam", "RNA therapeutics clinical/FDA catalyst watch"),
        ("RARE", "Ultragenyx", "rare disease clinical/FDA catalyst watch"),
        ("SRPT", "Sarepta Therapeutics", "gene therapy FDA/commercial catalyst watch"),
        ("QURE", "uniQure", "gene therapy clinical/FDA catalyst watch"),
        ("PRTA", "Prothena", "neurodegenerative clinical catalyst watch"),
        ("SAGE", "Sage Therapeutics", "CNS biotech clinical/strategic catalyst watch"),
        ("ACAD", "ACADIA Pharmaceuticals", "CNS commercial/FDA catalyst watch"),
        ("HALO", "Halozyme", "biotech royalty/product catalyst watch"),
        ("MRTX", "Mirati placeholder", "oncology catalyst watch"),
        ("VIR", "Vir Biotechnology", "infectious disease clinical catalyst watch"),
        ("MRNA", "Moderna", "vaccine pipeline/FDA catalyst watch"),
        ("BNTX", "BioNTech", "oncology/vaccine clinical catalyst watch"),
        ("GERN", "Geron", "FDA/commercial launch hematology catalyst watch"),
        ("SWTX", "SpringWorks Therapeutics", "oncology/FDA commercial catalyst watch"),
    ]
    return pd.DataFrame([
        {
            "ticker": t,
            "company": c,
            "candidate_source": "biotech_fda_seed",
            "source_reason": reason,
            "headline": reason,
            "source_confidence": "DISCOVERY_ONLY_BIOTECH_LOCKED",
            "requires_web_validation": True,
        }
        for t, c, reason in rows
    ])
