export function formatCurrency(amount, options = {}) {
    if (
        amount === null ||
        amount === undefined ||
        Number.isNaN(Number(amount))
    ) {
        return "Varies";
    }

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: options.cents ? 2 : 0,
    }).format(amount);
}

export function hasNumericEstimate(items = []) {
    return items.some((item) =>
        (!item.value_period || item.value_period === 'monthly') &&
        Number.isFinite(Number(item.estimated_monthly_value_usd)) &&
        item.estimated_monthly_value_usd > 0,
    );
}

export function confidenceLabel(confidence) {
    const labels = {
        high: "High confidence",
        medium: "Worth checking",
        low: "Possible match",
    };

    return labels[confidence] || "Worth checking";
}

export function compactProgramName(name = "") {
    return name.replace("Supplemental Nutrition Assistance Program", "SNAP");
}
