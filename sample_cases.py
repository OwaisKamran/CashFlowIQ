"""Demo businesses with their expected status."""

# warning-sign answers are No unless a case says otherwise
_NO_SYMPTOMS = {
    "delaying_suppliers": False, "late_customers": False, "stock_piling": False,
    "sales_up_cash_down": False, "personal_money": False, "planning_expansion": False,
    "big_customer": False, "overdue_tax": False, "rf_maxed": False, "owes_nothing": False,
}


def _case(expected, story, symptoms=None, **inputs):
    data = dict(_NO_SYMPTOMS)
    data.update(symptoms or {})
    data.update(inputs)
    return {"expected_status": expected, "story": story, "inputs": data}


# one business per status; the tests check each expected status
SAMPLE_CASES = {
    "Al-Noor General Store (Healthy)": _case(
        "Healthy",
        "A well-run retail store: strong cash, fast collections, lean stock, light debt.",
        business_name="Al-Noor General Store", business_type="retail", season="normal",
        cash_in_hand=600_000, bank_balance=1_400_000,
        accounts_receivable=200_000, collection_days=10,
        accounts_payable=600_000, payment_days=30,
        inventory_value=1_200_000, stock_days=40,
        monthly_sales=2_400_000, gross_margin_pct=22,
        monthly_fixed_expenses=300_000,
        short_term_loans=300_000, monthly_installment=50_000,
        other_current_liabilities=100_000,
    ),
    "Hamza Textiles Wholesale (Watch)": _case(
        "Watch",
        "Growing wholesaler: sales rising but customers pay slowly and one buyer dominates.",
        symptoms={"late_customers": True, "big_customer": True, "sales_up_cash_down": True},
        business_name="Hamza Textiles Wholesale", business_type="wholesale", season="normal",
        cash_in_hand=300_000, bank_balance=900_000,
        accounts_receivable=6_400_000, collection_days=85,
        accounts_payable=3_000_000, payment_days=45,
        inventory_value=4_000_000, stock_days=60,
        monthly_sales=4_000_000, gross_margin_pct=12,
        monthly_fixed_expenses=280_000,
        short_term_loans=1_500_000, monthly_installment=60_000,
        other_current_liabilities=300_000,
    ),
    "Karachi Auto Parts Trading (Risky)": _case(
        "Risky",
        "Trader with dead stock and heavy loan installments who wants to open a second branch.",
        symptoms={"planning_expansion": True},
        business_name="Karachi Auto Parts Trading", business_type="trading", season="normal",
        cash_in_hand=400_000, bank_balance=1_400_000,
        accounts_receivable=4_000_000, collection_days=45,
        accounts_payable=2_500_000, payment_days=40,
        inventory_value=6_000_000, stock_days=200,
        monthly_sales=4_000_000, gross_margin_pct=15,
        monthly_fixed_expenses=200_000,
        short_term_loans=2_500_000, monthly_installment=320_000,
        other_current_liabilities=300_000,
    ),
    "Lahore Spice Kitchen (Crisis)": _case(
        "Crisis",
        "Restaurant losing cash every month with only days of cash left and overdue taxes.",
        symptoms={"delaying_suppliers": True, "personal_money": True, "overdue_tax": True},
        business_name="Lahore Spice Kitchen", business_type="restaurant", season="normal",
        cash_in_hand=80_000, bank_balance=70_000,
        accounts_receivable=50_000, collection_days=5,
        accounts_payable=900_000, payment_days=60,
        inventory_value=200_000, stock_days=12,
        monthly_sales=1_800_000, gross_margin_pct=55,
        monthly_fixed_expenses=1_000_000,
        short_term_loans=500_000, monthly_installment=120_000,
        other_current_liabilities=300_000,
    ),
    "Sialkot Sports Goods Mfg (Seasonal - Risky)": _case(
        "Risky",
        "Profitable manufacturer hit by the off-season: long production cycle, running finance maxed.",
        symptoms={"rf_maxed": True},
        business_name="Sialkot Sports Goods Mfg", business_type="manufacturing", season="off-season",
        cash_in_hand=200_000, bank_balance=1_000_000,
        accounts_receivable=4_500_000, collection_days=55,
        accounts_payable=2_000_000, payment_days=30,
        inventory_value=6_000_000, stock_days=100,
        monthly_sales=3_200_000, gross_margin_pct=28,
        monthly_fixed_expenses=600_000,
        short_term_loans=3_000_000, monthly_installment=150_000,
        other_current_liabilities=300_000,
    ),
}
