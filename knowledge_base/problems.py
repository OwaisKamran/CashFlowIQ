"""
problems.py - The PROBLEM CATALOG (single source of truth for every diagnosis).

Rules only say  RaiseProblem("weak_credit_control").
Everything else about that problem - its title, severity, description and the
recommended decisions (with reasons) - lives here, exactly once.

Why a catalog?
  * Several rules can raise the same problem (e.g. R28 from collection days AND
    R59 from the "customers pay late" symptom). Each works on its own, and when
    both fire their certainty factors are COMBINED (MYCIN).
  * Decisions are written once, so they never go out of sync between rules.

Severity levels (used for ranking and for the health score):
  Critical > High > Medium > Low
"""

SEVERITY_RANK = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


def _p(title, severity, description, decisions):
    """Build one catalog entry. decisions = list of (decision, reason)."""
    assert severity in SEVERITY_RANK, f"bad severity {severity}"
    return {
        "title": title,
        "severity": severity,
        "description": description,
        "decisions": [{"text": d, "reason": r} for d, r in decisions],
    }


PROBLEMS = {
    # ---------------- Ratio analysis ----------------
    "weak_current_ratio": _p(
        "Weak current ratio", "High",
        "Short-term liabilities are larger than short-term assets.",
        [("Convert part of short-term debt into a longer-term loan",
          "Moving repayments further out immediately improves the current ratio."),
         ("Inject owner equity or bring in a partner",
          "Fresh equity adds current assets without adding liabilities.")]),
    "borderline_current_ratio": _p(
        "Borderline current ratio", "Low",
        "Current assets only just cover current liabilities; there is little margin for shocks.",
        [("Avoid new short-term commitments until the ratio is above the safe level",
          "Every new short-term liability pushes the ratio closer to 1.0.")]),
    "quick_liquidity_shortfall": _p(
        "Severe quick-liquidity shortfall", "High",
        "Without selling stock, the business cannot cover even half of its short-term liabilities.",
        [("Speed up collections from customers",
          "Receivables are the fastest non-stock asset that can be turned into cash."),
         ("Keep a minimum cash reserve in the bank",
          "A reserve protects the business when stock cannot be sold quickly.")]),
    "liquidity_locked_in_inventory": _p(
        "Liquidity locked in inventory", "Medium",
        "The current ratio looks healthy only because of stock; quick liquidity is weak.",
        [("Reduce stock levels and buy in smaller lots",
          "Stock is the least liquid current asset; less stock means more usable cash.")]),
    "low_cash_cover": _p(
        "Very low cash cover", "Medium",
        "Cash and bank balances cover only a small fraction of short-term liabilities.",
        [("Build a minimum cash balance equal to at least one month of fixed costs",
          "A cash buffer prevents missed payments when collections are delayed.")]),
    "idle_surplus_cash": _p(
        "Idle surplus cash", "Low",
        "Far more cash is held than the business needs; it earns nothing while idle.",
        [("Place surplus cash in short-term bank deposits or savings certificates",
          "Earns a return while keeping money accessible."),
         ("Pay off expensive debt early",
          "Saves interest cost, which is often higher than deposit returns.")]),
    "negative_working_capital": _p(
        "Negative working capital", "High",
        "Current liabilities exceed current assets; the business depends on new credit to survive.",
        [("Restructure liabilities: move short-term debt to long-term",
          "Reduces the amount that must be paid within the year."),
         ("Inject owner equity",
          "Directly closes the working-capital gap.")]),

    # ---------------- Cash runway ----------------
    "cash_runs_out_within_month": _p(
        "Cash runs out within a month", "Critical",
        "At the current spending level, cash will be exhausted in less than 30 days.",
        [("Freeze all non-essential spending immediately",
          "Every rupee saved extends the runway."),
         ("Launch an urgent collection drive on all overdue invoices",
          "Collecting receivables is the fastest way to raise cash without borrowing.")]),
    "short_cash_runway": _p(
        "Short cash runway", "High",
        "Cash covers only one to two months of fixed costs and loan installments.",
        [("Prepare a 13-week cash flow forecast and review it weekly",
          "A short-term forecast shows exactly which week cash becomes tight."),
         ("Cut discretionary costs (marketing, travel, non-urgent repairs)",
          "Reduces monthly burn and lengthens the runway.")]),
    "thin_cash_buffer": _p(
        "Thin cash buffer", "Low",
        "Cash covers two to three months of costs - acceptable but below the 3-month comfort level.",
        [("Build the cash reserve up to 3 months of fixed costs",
          "Three months of cover protects against seasonal dips and late payers.")]),
    "monthly_cash_burn": _p(
        "Monthly cash burn", "High",
        "Gross profit does not cover fixed expenses plus loan installments; cash falls every month.",
        [("Cut fixed costs (rent, staff, utilities) by 10-15%",
          "Fixed costs must be lower than gross profit for the business to sustain itself."),
         ("Review pricing and remove loss-making products",
          "Higher margins increase gross profit per rupee of sales.")]),
    "imminent_cash_crisis": _p(
        "Imminent cash crisis", "Critical",
        "The business is losing cash every month AND has less than a month of cash left.",
        [("Talk to your bank NOW about bridging finance or a temporary limit",
          "Banks respond better before a default than after one."),
         ("Negotiate deferral of rent/installments for 1-2 months",
          "Buys time to fix operations without defaulting.")]),

    # ---------------- Receivables ----------------
    "severe_collection_delay": _p(
        "Severe collection delay", "High",
        "Customers take more than three months on average to pay.",
        [("Hand over accounts older than 90 days to a recovery process",
          "Old debts become harder to recover every month they are left."),
         ("Stop all new credit sales until overdue amounts are cleared",
          "Prevents the receivable balance growing further.")]),
    "weak_credit_control": _p(
        "Weak credit control", "Medium",
        "Customers are paying late; credit is not being managed tightly.",
        [("Stop new credit to customers who pay late",
          "Late payers are the biggest drain on cash."),
         ("Send weekly payment reminders and call before due dates",
          "Regular follow-up shortens the average collection period.")]),
    "receivables_too_high": _p(
        "Receivables too high relative to sales", "Medium",
        "Money owed by customers equals more than one and a half months of sales.",
        [("Offer a 2% discount for payment within 10 days",
          "A small discount is usually cheaper than borrowing to fund receivables.")]),
    "financing_customers": _p(
        "Financing customers with your own cash", "Medium",
        "Customers get much longer credit than your suppliers give you.",
        [("Align credit terms: give customers no more days than suppliers give you",
          "Closes the gap that your own cash is currently funding.")]),
    "receivables_trapping_cash": _p(
        "Receivables trapping cash during a shortage", "High",
        "Cash is short while a large amount is stuck with slow-paying customers.",
        [("Use invoice discounting / bill discounting with your bank",
          "Turns receivables into cash now instead of waiting."),
         ("Personally contact the top 5 debtors this week",
          "The largest balances give the biggest cash impact for the effort.")]),

    # ---------------- Inventory ----------------
    "slow_moving_stock": _p(
        "Slow-moving stock", "Medium",
        "Stock takes three to six months to sell.",
        [("Run a clearance sale on slow stock",
          "Converts dead weight into cash, even at a lower margin.")]),
    "dead_stock_risk": _p(
        "Dead / obsolete stock risk", "High",
        "Stock takes more than six months to sell and may never sell at full price.",
        [("Return slow items to suppliers or sell in bulk to other traders",
          "Recovers part of the cost before the stock loses all value."),
         ("Write off or donate stock that cannot be sold",
          "Stops wasting storage space and gives a true picture of assets.")]),
    "overstocking": _p(
        "Overstocking", "Medium",
        "Inventory is more than two months of sales; too much cash is sitting on shelves.",
        [("Stop reordering slow items and set reorder levels per product",
          "Buys only what sells, freeing cash for other needs.")]),
    "cash_trapped_in_stock": _p(
        "Cash trapped in slow stock", "High",
        "The healthy-looking current ratio is built on stock that is not selling.",
        [("Convert stock to cash through bundle offers and discounts",
          "The ratio is misleading until this stock turns into cash.")]),
    "perishable_stock": _p(
        "Perishable stock held too long", "Medium",
        "A restaurant holding stock for more than a week risks spoilage and waste.",
        [("Purchase daily/twice-weekly and follow FIFO (first in, first out)",
          "Reduces spoilage and the cash tied up in ingredients.")]),

    # ---------------- Payables ----------------
    "long_ccc": _p(
        "Long cash conversion cycle", "Medium",
        "It takes more than three months for a rupee spent on stock to come back as cash.",
        [("Negotiate 15 extra days of credit with suppliers",
          "Longer payment days shorten the cash conversion cycle directly.")]),
    "paying_suppliers_too_fast": _p(
        "Paying suppliers too quickly", "Low",
        "Suppliers are paid in under two weeks; free supplier credit is not being used.",
        [("Negotiate 30-day payment terms with regular suppliers",
          "Supplier credit is interest-free financing.")]),
    "stretched_payables": _p(
        "Severely stretched payables", "High",
        "Suppliers wait more than three months for payment; supply may be cut off.",
        [("Prioritise payments to critical suppliers and agree a written payment plan",
          "Protects the supply of goods the business cannot operate without.")]),
    "supplier_strain": _p(
        "Supplier relationship strain", "High",
        "Supplier payments are being delayed, which risks losing credit terms or supply.",
        [("Proactively share a realistic payment plan with key suppliers",
          "Suppliers tolerate delays far better when they are informed in advance.")]),
    "working_capital_gap": _p(
        "Working-capital funding gap", "High",
        "A long cash cycle combined with negative monthly cash flow cannot be self-funded.",
        [("Arrange a running finance (working-capital) line with your bank",
          "Bridges the gap between paying suppliers and collecting from customers.")]),

    # ---------------- Debt ----------------
    "high_debt_servicing": _p(
        "High debt-servicing load", "Medium",
        "Loan installments take 30-50% of gross profit.",
        [("Avoid any new borrowing until existing loans are reduced",
          "More debt would push installments to an unsustainable level.")]),
    "unsustainable_debt": _p(
        "Unsustainable debt burden", "Critical",
        "Loan installments consume more than half of gross profit.",
        [("Request the bank to reschedule the loan over a longer period",
          "Lower installments free cash for operations."),
         ("Sell non-essential assets to repay part of the loan",
          "Reduces both principal and future installments.")]),
    "expansion_with_heavy_debt": _p(
        "Expansion on top of heavy debt", "High",
        "Planning an expansion while debt repayments are already unsustainable.",
        [("Delay expansion until the debt-service ratio is below the safe level",
          "Expansion adds cash needs before it adds cash inflows.")]),
    "no_borrowing_headroom": _p(
        "No borrowing headroom", "High",
        "The running finance limit is fully used and cash is running short.",
        [("Request a limit enhancement early, with updated accounts",
          "Banks need time to approve; asking during a crisis is harder."),
         ("Reduce dependence on running finance by collecting receivables",
          "Lowers utilisation and restores emergency headroom.")]),

    # ---------------- Seasonal & business type ----------------
    "off_season_squeeze": _p(
        "Off-season cash squeeze", "High",
        "It is the off-season and the cash runway is below three months.",
        [("Arrange running finance BEFORE the off-season deepens",
          "Banks lend more easily when sales figures still look strong."),
         ("Cut variable costs and temporary staff during the off-season",
          "Matches spending to the lower seasonal sales.")]),
    "peak_season_stock_not_selling": _p(
        "Stock not selling even in peak season", "High",
        "Stock is slow-moving during the peak season - a strong sign of wrong product mix or pricing.",
        [("Review product mix and pricing against competitors",
          "If stock doesn't sell in peak season, it will not sell later.")]),
    "long_production_cycle": _p(
        "Long production-to-cash cycle", "Medium",
        "Manufacturing cash cycle exceeds four months.",
        [("Take customer advances or use milestone billing on large orders",
          "Customer money finances production instead of your own cash.")]),
    "thin_margin_trading": _p(
        "Thin-margin trading", "Medium",
        "Gross margin is too thin to absorb late payments or price changes.",
        [("Avoid giving credit on thin-margin goods",
          "Financing cost of credit can wipe out the whole margin."),
         ("Negotiate volume discounts with suppliers",
          "Improves margin without raising selling prices.")]),
    "credit_in_cash_business": _p(
        "Unnecessary credit in a cash business", "Medium",
        "Retail/restaurant businesses should collect almost immediately, but collections are slow.",
        [("Move to cash, card and digital payments (Raast, JazzCash, Easypaisa)",
          "Instant digital payments remove the need for customer credit.")]),
    "slow_service_billing": _p(
        "Slow billing in service business", "Medium",
        "A service business is waiting too long to be paid for work already done.",
        [("Bill in advance or use monthly retainers",
          "Services cannot be repossessed - get paid before or during the work.")]),

    # ---------------- Symptom-based ----------------
    "overtrading": _p(
        "Overtrading (growth outpacing cash)", "High",
        "Sales are growing but cash is shrinking - growth is consuming working capital.",
        [("Slow down credit-based growth until collections catch up",
          "Growth on credit uses cash before it brings cash."),
         ("Fund growth with long-term finance, not daily cash",
          "Matches long-term needs with long-term money.")]),
    "owner_subsidising": _p(
        "Owner subsidising the business", "Medium",
        "Personal money is being used to keep the business running.",
        [("Separate personal and business bank accounts; pay yourself a fixed salary",
          "Shows the true performance of the business and protects household money.")]),
    "hidden_structural_loss": _p(
        "Hidden structural loss", "High",
        "Personal money is covering a business that loses cash every month.",
        [("Do a break-even review of every product/service line",
          "Identifies which activities lose money so they can be fixed or stopped.")]),
    "expansion_not_affordable": _p(
        "Expansion not affordable now", "High",
        "A big purchase/expansion is planned while the cash runway is below three months.",
        [("Delay expansion until the cash runway is at least 90 days",
          "Expansion needs a cash cushion to survive the start-up period.")]),
    "customer_concentration": _p(
        "Customer concentration risk", "Medium",
        "One customer provides over 40% of sales; losing or delays from them would hurt badly.",
        [("Diversify the customer base - target 3-5 new mid-size customers",
          "Reduces dependence on a single buyer."),
         ("Ask the key customer for post-dated cheques or partial advance",
          "Secures the largest single source of cash.")]),
    "tax_arrears": _p(
        "Tax arrears & FBR penalty risk", "High",
        "Overdue taxes attract penalties, default surcharge and possible account attachment.",
        [("Clear overdue taxes first or apply to FBR for an installment plan",
          "Penalties grow quickly and bank accounts can be attached for recovery.")]),
}


# Plain-language "concern" phrases used in the report summary:
#   "The main concern is that <concern>."
# {placeholders} are filled from working-memory facts (see explanation.plain_summary).
CONCERNS = {
    "weak_current_ratio": "you owe more in the short term than you have in short-term assets",
    "borderline_current_ratio": "your short-term assets only just cover what you owe soon",
    "quick_liquidity_shortfall": "without selling stock you could pay less than half of what you owe soon",
    "liquidity_locked_in_inventory": "much of your money is tied up in stock",
    "low_cash_cover": "your cash covers only {cash_ratio_pct} of what you owe soon",
    "idle_surplus_cash": "a lot of cash is sitting idle instead of earning a return",
    "negative_working_capital": "your short-term debts are larger than your short-term assets",
    "cash_runs_out_within_month": "your cash will last only about {runway_days} days",
    "short_cash_runway": "your cash will last only about {runway_days} days",
    "thin_cash_buffer": "your cash buffer is below the safe level of three months",
    "monthly_cash_burn": "you are losing about {net_cf_abs} every month",
    "imminent_cash_crisis": "you are losing money every month and your cash will last only about "
                            "{runway_days} days",
    "severe_collection_delay": "customers take {collection_days} days to pay",
    "weak_credit_control": "customers take {collection_days} days to pay",
    "receivables_too_high": "customers owe you about {rec_months} months of sales",
    "financing_customers": "customers take {collection_days} days to pay you, while you pay "
                           "suppliers in {payment_days} days",
    "receivables_trapping_cash": "money is stuck with slow-paying customers while cash is short",
    "slow_moving_stock": "stock takes about {stock_days} days to sell",
    "dead_stock_risk": "stock takes about {stock_days} days to sell and may not sell at full price",
    "overstocking": "you hold about {inv_months} months of sales as stock",
    "cash_trapped_in_stock": "your money is trapped in stock that is not selling",
    "perishable_stock": "ingredients are kept for {stock_days} days, which risks waste",
    "long_ccc": "money spent on stock takes about {ccc} days to come back as cash",
    "paying_suppliers_too_fast": "you pay suppliers in only {payment_days} days",
    "stretched_payables": "suppliers wait {payment_days} days for payment and may stop supplying",
    "supplier_strain": "you are paying suppliers late",
    "working_capital_gap": "your cash cycle is long and you are losing money each month",
    "high_debt_servicing": "loan installments take {dsr_pct} of your gross profit",
    "unsustainable_debt": "loan installments take {dsr_pct} of your gross profit",
    "expansion_with_heavy_debt": "you plan to expand while loan payments are already too heavy",
    "no_borrowing_headroom": "your running finance limit is used up while cash is short",
    "off_season_squeeze": "it is the slow season and your cash would last less than three months",
    "peak_season_stock_not_selling": "stock is not selling even in the busy season",
    "long_production_cycle": "it takes about {ccc} days from buying materials to collecting cash",
    "thin_margin_trading": "your profit margin of {margin} is too thin to absorb late payments",
    "credit_in_cash_business": "customers take {collection_days} days to pay in a business that "
                               "should be paid at once",
    "slow_service_billing": "clients take {collection_days} days to pay for work already done",
    "overtrading": "sales are growing faster than your cash",
    "owner_subsidising": "personal money is being used to keep the business going",
    "hidden_structural_loss": "personal money is covering a business that loses money every month",
    "expansion_not_affordable": "you plan to expand with less than three months of cash",
    "customer_concentration": "one customer brings in more than 40% of your sales",
    "tax_arrears": "you have overdue taxes that attract penalties",
}
