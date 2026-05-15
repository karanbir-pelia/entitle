"""Generate missing state_programs JSON files from state_metadata.json.

Each generated state file includes SNAP, Medicaid, and TANF programs derived
from the metadata. States that already have hand-curated files are skipped,
so this is safe to re-run.

Usage:
    python backend/scripts/generate_state_programs.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BENEFITS_DIR = os.path.normpath(os.path.join(HERE, "..", "data", "benefits"))
META_PATH = os.path.join(BENEFITS_DIR, "state_metadata.json")
OUT_DIR = os.path.join(BENEFITS_DIR, "state_programs")

MEDICAID_BRAND = {
    "AL": "Alabama Medicaid",
    "AK": "Alaska Medicaid (DenaliCare)",
    "AR": "Arkansas Medicaid (ARHOME)",
    "AZ": "AHCCCS",
    "CA": "Medi-Cal",
    "CO": "Health First Colorado",
    "CT": "HUSKY Health",
    "DE": "Delaware Medicaid",
    "DC": "DC Medicaid",
    "FL": "Florida Medicaid",
    "GA": "Georgia Medicaid",
    "HI": "Med-QUEST",
    "ID": "Idaho Medicaid",
    "IL": "Illinois Medicaid (HFS)",
    "IN": "Hoosier Healthwise / HIP",
    "IA": "Iowa Health Link",
    "KS": "KanCare",
    "KY": "Kentucky Medicaid",
    "LA": "Healthy Louisiana",
    "ME": "MaineCare",
    "MD": "Maryland Medicaid",
    "MA": "MassHealth",
    "MI": "Healthy Michigan Plan",
    "MN": "Medical Assistance (MA)",
    "MS": "Mississippi Medicaid",
    "MO": "MO HealthNet",
    "MT": "Montana Medicaid",
    "NE": "Heritage Health",
    "NV": "Nevada Medicaid",
    "NH": "NH Medicaid",
    "NJ": "NJ FamilyCare",
    "NM": "Centennial Care",
    "NY": "New York Medicaid",
    "NC": "NC Medicaid",
    "ND": "ND Medicaid",
    "OH": "Ohio Medicaid",
    "OK": "SoonerCare",
    "OR": "Oregon Health Plan (OHP)",
    "PA": "Medical Assistance (PA)",
    "RI": "RIte Care",
    "SC": "Healthy Connections",
    "SD": "South Dakota Medicaid",
    "TN": "TennCare",
    "TX": "Texas Medicaid",
    "UT": "Utah Medicaid",
    "VT": "Green Mountain Care / Medicaid",
    "VA": "Virginia Medicaid (Cardinal Care)",
    "WA": "Apple Health",
    "WV": "WV Medicaid",
    "WI": "BadgerCare Plus",
    "WY": "Wyoming Medicaid",
}

MEDICAID_AGENCY = {
    "AL": "Alabama Medicaid Agency",
    "AK": "Alaska DPA",
    "AR": "DHS",
    "CO": "HCPF",
    "CT": "DSS",
    "DE": "DHSS",
    "DC": "DHCF",
    "HI": "Med-QUEST Division",
    "ID": "DHW",
    "IN": "FSSA",
    "IA": "Iowa HHS",
    "KS": "KDHE",
    "KY": "DMS",
    "LA": "LDH",
    "ME": "DHHS / OMS",
    "MD": "MDH",
    "MA": "EOHHS",
    "MN": "DHS",
    "MS": "DOM",
    "MO": "DSS / MHD",
    "MT": "DPHHS",
    "NE": "DHHS",
    "NV": "DHCFP",
    "NH": "DHHS",
    "NM": "HCA",
    "ND": "DHS",
    "OK": "OHCA",
    "OR": "OHA",
    "RI": "EOHHS",
    "SC": "SCDHHS",
    "SD": "DSS",
    "TN": "TennCare",
    "UT": "DHHS",
    "VT": "DVHA",
    "WV": "BMS",
    "WI": "DHS",
    "WY": "WDH",
}

HUMAN_SERVICES_AGENCY = {
    "AL": "Alabama DHR",
    "AK": "Alaska DPA",
    "AR": "Arkansas DHS",
    "CO": "CDHS",
    "CT": "CT DSS",
    "DE": "Delaware DHSS",
    "DC": "DC DHS",
    "HI": "Hawaii DHS",
    "ID": "Idaho DHW",
    "IN": "Indiana FSSA / DFR",
    "IA": "Iowa HHS",
    "KS": "Kansas DCF",
    "KY": "Kentucky CHFS",
    "LA": "Louisiana DCFS",
    "ME": "Maine DHHS / OFI",
    "MD": "Maryland DHS",
    "MA": "MA DTA",
    "MN": "Minnesota DHS",
    "MS": "Mississippi DHS",
    "MO": "Missouri DSS / FSD",
    "MT": "Montana DPHHS",
    "NE": "Nebraska DHHS",
    "NV": "Nevada DWSS",
    "NH": "NH DHHS",
    "NM": "New Mexico HCA",
    "ND": "ND DHS",
    "OK": "Oklahoma DHS",
    "OR": "Oregon ODHS",
    "RI": "RI DHS",
    "SC": "SCDSS",
    "SD": "SD DSS",
    "TN": "TN DHS",
    "UT": "Utah DWS",
    "VT": "Vermont DCF",
    "WV": "WV DoHS",
    "WI": "Wisconsin DHS",
    "WY": "WY DFS",
}

TANF_BRAND = {
    "AL": "Family Assistance",
    "AK": "Alaska Temporary Assistance Program (ATAP)",
    "AR": "TEA",
    "CO": "Colorado Works",
    "CT": "Temporary Family Assistance (TFA)",
    "DE": "TANF (Delaware)",
    "DC": "TANF (DC)",
    "HI": "Hawaii TANF / First-To-Work",
    "ID": "Temporary Assistance for Families in Idaho (TAFI)",
    "IN": "Indiana TANF",
    "IA": "Family Investment Program (FIP)",
    "KS": "TANF Cash Assistance",
    "KY": "Kentucky Transitional Assistance Program (K-TAP)",
    "LA": "Family Independence Temporary Assistance Program (FITAP)",
    "ME": "TANF (Maine)",
    "MD": "Temporary Cash Assistance (TCA)",
    "MA": "Transitional Aid to Families with Dependent Children (TAFDC)",
    "MN": "Minnesota Family Investment Program (MFIP)",
    "MS": "TANF (Mississippi)",
    "MO": "Temporary Assistance (TA)",
    "MT": "TANF Cash Assistance",
    "NE": "Aid to Dependent Children (ADC)",
    "NV": "TANF (Nevada)",
    "NH": "Family Assistance Program (FAP)",
    "NM": "New Mexico Works",
    "ND": "TANF (ND)",
    "OK": "TANF (Oklahoma)",
    "OR": "Temporary Assistance for Needy Families (TANF)",
    "RI": "Rhode Island Works (RIW)",
    "SC": "Family Independence (FI)",
    "SD": "TANF (South Dakota)",
    "TN": "Families First",
    "UT": "Family Employment Program (FEP)",
    "VT": "Reach Up",
    "WV": "WV WORKS",
    "WI": "Wisconsin Works (W-2)",
    "WY": "POWER",
}


def slug(state_code: str) -> str:
    return state_code.lower()


def build_snap(state_code: str, state_name: str, meta: dict) -> dict:
    portal = meta.get("snap_portal", "")
    return {
        "id": f"{slug(state_code)}_snap",
        "name": f"SNAP ({state_name})",
        "full_name": f"Supplemental Nutrition Assistance Program — {state_name}",
        "agency": HUMAN_SERVICES_AGENCY.get(state_code, f"{state_name} human services agency"),
        "category": "food",
        "description": f"{state_name} administers federal SNAP with standard federal eligibility rules.",
        "monthly_benefit_range": {
            "min_usd": 23,
            "max_usd": 1751,
            "note": "Standard federal benefit amounts (FY2025 maximum allotments)",
        },
        "eligibility_rules": {
            "income": {
                "limit_pct_of_fpl": 130,
                "note": "Federal gross income limit; net income must be at or below 100% FPL",
            }
        },
        "application": {
            "method": ["online", "in_person", "phone", "mail"],
            "where": portal or f"{state_name} human services office",
            "processing_time_days": "30 (7 for expedited)",
        },
        "required_documents": [
            "Photo ID",
            "Proof of residency",
            "Proof of income",
            "Social Security numbers",
        ],
        "tags": ["food", "ebt_card", "state", state_name.lower().replace(" ", "_")],
    }


def build_medicaid(state_code: str, state_name: str, meta: dict) -> dict:
    expansion = bool(meta.get("medicaid_expansion"))
    chip_limit = meta.get("chip_income_limit_pct_fpl", 200)
    portal = meta.get("medicaid_portal", "")
    brand = MEDICAID_BRAND.get(state_code, f"{state_name} Medicaid")
    agency = MEDICAID_AGENCY.get(state_code, f"{state_name} Medicaid agency")
    if expansion:
        adults_limit = 138
        desc = (
            f"{state_name} has expanded Medicaid under the ACA. Adults are covered up to 138% FPL. "
            f"Children and pregnant women have higher income limits (CHIP up to {chip_limit}% FPL)."
        )
    else:
        adults_limit = None
        desc = (
            f"{state_name} has NOT expanded Medicaid. Coverage for non-disabled adults without children is very limited. "
            f"Children, pregnant women, the elderly, and people with disabilities may qualify (CHIP up to {chip_limit}% FPL)."
        )
    income_rules: dict = {
        "children_limit_pct_of_fpl": chip_limit,
    }
    if adults_limit is not None:
        income_rules["adults_limit_pct_of_fpl"] = adults_limit
    else:
        income_rules["adults_note"] = "No Medicaid expansion; eligibility for adults is very narrow"
    return {
        "id": f"{slug(state_code)}_medicaid",
        "name": brand,
        "full_name": f"{brand} (Medicaid)",
        "agency": agency,
        "category": "healthcare",
        "description": desc,
        "monthly_benefit_range": {
            "min_usd": 0,
            "max_usd": 0,
            "note": "No premium for most enrollees. Covers doctor visits, hospital, prescriptions, and more.",
        },
        "eligibility_rules": {
            "income": income_rules,
            "medicaid_expansion": expansion,
        },
        "application": {
            "method": ["online", "in_person", "phone", "mail"],
            "where": portal or f"{state_name} Medicaid agency",
            "processing_time_days": 45,
        },
        "required_documents": [
            "Photo ID",
            "Proof of income",
            f"Proof of {state_name} residency",
            "Social Security number or immigration documents",
        ],
        "tags": [
            "healthcare",
            "insurance",
            "state",
            state_name.lower().replace(" ", "_"),
            "expansion" if expansion else "non_expansion",
        ],
    }


def build_tanf(state_code: str, state_name: str, meta: dict) -> dict:
    max_amount = meta.get("tanf_max_monthly_family3")
    portal = meta.get("benefits_portal", "")
    brand = TANF_BRAND.get(state_code, "TANF")
    return {
        "id": f"{slug(state_code)}_tanf",
        "name": f"{brand}",
        "full_name": f"{brand} — Temporary Assistance for Needy Families",
        "agency": HUMAN_SERVICES_AGENCY.get(state_code, f"{state_name} human services agency"),
        "category": "cash",
        "description": (
            f"{state_name}'s TANF program provides time-limited cash assistance to low-income families with children. "
            f"Maximum monthly benefit for a family of 3 is approximately ${max_amount}."
        ),
        "monthly_benefit_range": {
            "min_usd": 0,
            "max_usd": max_amount if isinstance(max_amount, int) else 0,
            "note": f"Family of 3 maximum: ${max_amount}/month",
        },
        "eligibility_rules": {
            "who": "Families with dependent children under 18 (or 19 if still in high school)",
            "income": {
                "note": "Very low income limits; varies by family size. Generally well below 100% FPL.",
            },
            "time_limit": "60-month lifetime limit (federal); some states have shorter limits",
        },
        "application": {
            "method": ["online", "in_person", "phone"],
            "where": portal or f"{state_name} human services office",
            "processing_time_days": 45,
        },
        "required_documents": [
            "Birth certificates for all children",
            "Social Security numbers",
            "Photo ID",
            "Proof of income",
            "Proof of residency",
        ],
        "tags": ["cash", "families", "children", "state", state_name.lower().replace(" ", "_")],
    }


def build_state_file(state_code: str, meta: dict) -> dict:
    state_name = meta["name"]
    expansion = bool(meta.get("medicaid_expansion"))
    out: dict = {
        "state": state_code,
        "state_name": state_name,
        "medicaid_expansion": expansion,
    }
    if not expansion:
        out["note"] = (
            f"{state_name} has NOT expanded Medicaid. Working-age adults without dependent children "
            f"generally do not qualify for Medicaid unless they have a disability."
        )
    out["programs"] = [
        build_snap(state_code, state_name, meta),
        build_medicaid(state_code, state_name, meta),
        build_tanf(state_code, state_name, meta),
    ]
    return out


def main() -> None:
    with open(META_PATH, "r") as f:
        meta_all = json.load(f)["states"]
    existing = {fn.replace(".json", "") for fn in os.listdir(OUT_DIR) if fn.endswith(".json")}
    created = []
    for code, meta in meta_all.items():
        if code in existing:
            continue
        data = build_state_file(code, meta)
        out_path = os.path.join(OUT_DIR, f"{code}.json")
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        created.append(code)
    print(f"Created {len(created)} state files: {sorted(created)}")
    total = len([fn for fn in os.listdir(OUT_DIR) if fn.endswith(".json")])
    print(f"Total state files now: {total}")


if __name__ == "__main__":
    main()
