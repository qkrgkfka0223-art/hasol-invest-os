from __future__ import annotations

import pandas as pd


def load_news_catalyst_seed_candidates() -> pd.DataFrame:
    """Broad thematic/news-catalyst discovery candidates.

    These rows are discovery inputs only. They intentionally require web
    validation before any execution decision.
    """
    rows = [
        ("OKLO", "Oklo", "nuclear power and AI data center power supply catalyst watch"),
        ("SMR", "NuScale Power", "small modular reactor policy/data center power catalyst watch"),
        ("NNE", "Nano Nuclear Energy", "nuclear microreactor policy catalyst watch"),
        ("LEU", "Centrus Energy", "uranium fuel supply shortage and government contract watch"),
        ("UUUU", "Energy Fuels", "uranium/rare earth supply-chain catalyst watch"),
        ("CCJ", "Cameco", "uranium supply shortage catalyst watch"),
        ("MP", "MP Materials", "rare earth supply-chain policy catalyst watch"),
        ("LAC", "Lithium Americas", "lithium policy/supply-chain catalyst watch"),
        ("ALB", "Albemarle", "lithium supply recovery catalyst watch"),
        ("KTOS", "Kratos Defense", "defense drone/DoD contract catalyst watch"),
        ("AVAV", "AeroVironment", "defense drone contract catalyst watch"),
        ("ACHR", "Archer Aviation", "eVTOL aviation certification/partnership catalyst watch"),
        ("JOBY", "Joby Aviation", "eVTOL aviation certification/partnership catalyst watch"),
        ("PL", "Planet Labs", "space/data contract catalyst watch"),
        ("RDW", "Redwire", "space infrastructure NASA contract catalyst watch"),
        ("BKSY", "BlackSky", "space intelligence government contract catalyst watch"),
        ("IRDM", "Iridium", "satellite communications contract catalyst watch"),
        ("GSAT", "Globalstar", "satellite communications partnership catalyst watch"),
        ("IONQ", "IonQ", "quantum computing government/enterprise contract catalyst watch"),
        ("QBTS", "D-Wave Quantum", "quantum computing contract catalyst watch"),
        ("RGTI", "Rigetti Computing", "quantum computing contract catalyst watch"),
        ("ARQQ", "Arqit Quantum", "cybersecurity/quantum contract catalyst watch"),
        ("CRDO", "Credo Technology", "AI data center connectivity catalyst watch"),
        ("COHR", "Coherent", "AI optical networking/data center catalyst watch"),
        ("LITE", "Lumentum", "AI optical networking/data center catalyst watch"),
        ("FN", "Fabrinet", "AI optical manufacturing catalyst watch"),
        ("CLS", "Celestica", "AI hardware manufacturing catalyst watch"),
        ("JBL", "Jabil", "AI hardware manufacturing catalyst watch"),
        ("FLEX", "Flex", "AI hardware manufacturing catalyst watch"),
        ("APLD", "Applied Digital", "AI data center hosting catalyst watch"),
        ("IREN", "IREN", "AI data center/compute hosting catalyst watch"),
        ("CORZ", "Core Scientific", "AI data center/compute hosting catalyst watch"),
        ("WULF", "TeraWulf", "AI data center power/hosting catalyst watch"),
        ("BTDR", "Bitdeer", "AI compute/mining infrastructure catalyst watch"),
        ("HIMS", "Hims & Hers Health", "consumer health growth/product launch catalyst watch"),
        ("RBRK", "Rubrik", "cybersecurity/data protection catalyst watch"),
        ("CRWD", "CrowdStrike", "cybersecurity platform catalyst watch"),
        ("NET", "Cloudflare", "AI edge/security platform catalyst watch"),
        ("DDOG", "Datadog", "cloud observability AI product catalyst watch"),
        ("SNOW", "Snowflake", "AI data platform product catalyst watch"),
    ]
    return pd.DataFrame([
        {
            "ticker": t,
            "company": c,
            "candidate_source": "news_catalyst_seed",
            "source_reason": reason,
            "headline": reason,
            "source_confidence": "DISCOVERY_ONLY",
            "requires_web_validation": True,
        }
        for t, c, reason in rows
    ])
