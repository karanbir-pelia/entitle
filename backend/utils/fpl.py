# backend/utils/fpl.py
# 2026 Federal Poverty Level guidelines (contiguous 48 states + DC)

FPL_2026: dict[int, int] = {
    1: 15650,
    2: 21150,
    3: 26650,
    4: 32150,
    5: 37650,
    6: 43150,
    7: 48650,
    8: 54150,
}
FPL_2026_ADDITIONAL = 5500  # Each additional person beyond 8


def get_fpl(household_size: int) -> int:
    """Return the 2026 FPL annual income threshold for the given household size."""
    if household_size <= 8:
        return FPL_2026[max(1, household_size)]
    return FPL_2026[8] + (household_size - 8) * FPL_2026_ADDITIONAL


def get_fpl_percentage(annual_income: float, household_size: int) -> float:
    """Return the household's income as a percentage of the FPL."""
    fpl = get_fpl(household_size)
    if fpl == 0:
        return 0.0
    return (annual_income / fpl) * 100
