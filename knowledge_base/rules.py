"""
rules.py - THE KNOWLEDGE BASE of CashFlow IQ.

Every rule is data:  Rule(id, group, description, conditions, actions, cf, priority)

  * Numbers are NEVER hard-coded: thresholds are referenced with T("name") and
    read from thresholds.json at match time (so the Admin page can change them).
  * Problems are referenced by catalog key (see problems.py).
  * COMPUTE rules derive new facts using named formulas (see formulas.py).

PRIORITY SCHEME (higher fires first - used in conflict resolution)
  220  DATA CHECK (missing)   -> is every essential fact present?
  210  DATA CHECK (sanity)    -> do the inputs look consistent?
  200  DATA VERDICT           -> "Insufficient data" + HALT, or data_sufficient = True
  100  COMPUTE rules          -> derived facts must exist before they are tested
   90  BAND rules             -> classify ratios into bands (critical/short/...)
   70  DIAGNOSIS rules        -> raise problems directly from facts
   60  SYMPTOM rules          -> raise problems from Yes/No answers
   40  CHAINED rules          -> use conclusions of other rules (forward chaining)
    6  STATUS OVERRIDE        -> imminent crisis forces "Crisis"
    5  SCORING                -> health score & problem counts (after ALL diagnosis)
    4  STATUS                 -> Healthy / Watch / Risky / Crisis
    3  STATUS DECISIONS       -> final advice based on the status
"""
from knowledge_base.rule_model import (
    Rule, Condition as C, T, Compute, Assert, RaiseProblem, AddStrength,
    Recommend, FlagMissing, Warn, Halt, known, yes, has_problem,
)

P_MISSING, P_SANITY, P_VERDICT = 220, 210, 200
P_COMPUTE, P_BAND, P_DIAG, P_SYMPTOM, P_CHAIN = 100, 90, 70, 60, 40
P_OVERRIDE, P_SCORE, P_STATUS, P_STATUS_DECISION = 6, 5, 4, 3

G0 = "0. Data Sufficiency"
G1 = "1. Ratio Analysis"
G2 = "2. Cash Runway"
G3 = "3. Receivables"
G4 = "4. Inventory"
G5 = "5. Payables"
G6 = "6. Debt Burden"
G7 = "7. Seasonal & Business Type"
G8 = "8. Symptoms"
G9 = "9. Final Status"

RULE_GROUPS = [G0, G1, G2, G3, G4, G5, G6, G7, G8, G9]

# Essential input facts checked by the data-sufficiency rules (used by the UI
# to mark required fields; tests check this list matches the G0 rules).
ESSENTIAL_FACTS = ["cash_in_hand", "bank_balance", "monthly_sales", "gross_margin_pct",
                   "monthly_fixed_expenses"]
LIABILITY_FACTS = ["accounts_payable", "short_term_loans", "other_current_liabilities"]

# Facts needed for the balance-sheet ratios (used by several COMPUTE rules)
_CURRENT_ITEMS = (known("liquid_cash"), known("accounts_receivable"), known("inventory_value"),
                  known("accounts_payable"), known("short_term_loans"),
                  known("other_current_liabilities"))

RULES = [
    # =====================================================================
    # GROUP 1 - RATIO ANALYSIS
    # =====================================================================
    Rule("R01", G1, "Liquid cash is cash in hand plus bank balance.",
         (known("cash_in_hand"), known("bank_balance")),
         (Compute("liquid_cash", "liquid_cash"),), 1.0, P_COMPUTE),
    Rule("R02", G1, "Current ratio = current assets / current liabilities.",
         _CURRENT_ITEMS, (Compute("current_ratio", "current_ratio"),), 1.0, P_COMPUTE),
    Rule("R03", G1, "Quick ratio excludes inventory from current assets.",
         _CURRENT_ITEMS, (Compute("quick_ratio", "quick_ratio"),), 1.0, P_COMPUTE),
    Rule("R04", G1, "Cash ratio = liquid cash / current liabilities.",
         _CURRENT_ITEMS, (Compute("cash_ratio", "cash_ratio"),), 1.0, P_COMPUTE),
    Rule("R05", G1, "Working capital = current assets - current liabilities.",
         _CURRENT_ITEMS, (Compute("working_capital", "working_capital"),), 1.0, P_COMPUTE),
    Rule("R06", G1, "A current ratio below 1.0 means short-term debts exceed short-term assets.",
         (C("current_ratio", "<", T("current_ratio_weak")),),
         (Assert("cr_band", "weak"), RaiseProblem("weak_current_ratio")), 0.90, P_BAND),
    Rule("R07", G1, "A current ratio between 1.0 and 1.5 leaves little safety margin.",
         (C("current_ratio", ">=", T("current_ratio_weak")),
          C("current_ratio", "<", T("current_ratio_safe"))),
         (Assert("cr_band", "borderline"), RaiseProblem("borderline_current_ratio")), 0.70, P_BAND),
    Rule("R08", G1, "A current ratio of 1.5 or more is strong.",
         (C("current_ratio", ">=", T("current_ratio_safe")),),
         (Assert("cr_band", "strong"), AddStrength("Healthy current ratio")), 1.0, P_BAND),
    Rule("R09", G1, "A quick ratio below 0.5 means a severe shortage of liquid assets.",
         (C("quick_ratio", "<", T("quick_ratio_critical")),),
         (RaiseProblem("quick_liquidity_shortfall"),), 0.85, P_DIAG),
    Rule("R10", G1, "Strong current ratio but weak quick ratio means liquidity is locked in stock (chains on R08).",
         (C("cr_band", "==", "strong"), C("quick_ratio", "<", T("quick_ratio_safe"))),
         (RaiseProblem("liquidity_locked_in_inventory"),), 0.75, P_DIAG),
    Rule("R11", G1, "A cash ratio below 0.2 means very little cash cover.",
         (C("cash_ratio", "<", T("cash_ratio_low")),),
         (Assert("cash_band", "low"), RaiseProblem("low_cash_cover")), 0.70, P_BAND),
    Rule("R12", G1, "Very high current and cash ratios mean surplus cash is sitting idle.",
         (C("current_ratio", ">", T("current_ratio_excess")),
          C("cash_ratio", ">", T("cash_ratio_idle"))),
         (RaiseProblem("idle_surplus_cash"),), 0.60, P_DIAG),
    Rule("R13", G1, "Negative working capital means the business depends on new credit.",
         (C("working_capital", "<", 0),),
         (RaiseProblem("negative_working_capital"),), 0.90, P_DIAG),

    # =====================================================================
    # GROUP 2 - CASH RUNWAY & CASH FLOW
    # =====================================================================
    Rule("R14", G2, "Monthly gross profit = sales x gross margin %.",
         (known("monthly_sales"), known("gross_margin_pct")),
         (Compute("monthly_gross_profit", "monthly_gross_profit"),), 1.0, P_COMPUTE),
    Rule("R15", G2, "Cash runway = days the business can pay fixed costs + installment from cash.",
         (known("liquid_cash"), known("monthly_fixed_expenses"), known("monthly_installment")),
         (Compute("runway_days", "runway_days"),), 1.0, P_COMPUTE),
    Rule("R16", G2, "Net monthly cash flow = gross profit - fixed costs - installment.",
         (known("monthly_gross_profit"), known("monthly_fixed_expenses"), known("monthly_installment")),
         (Compute("net_monthly_cash_flow", "net_monthly_cash_flow"),), 1.0, P_COMPUTE),
    Rule("R17", G2, "Runway under 30 days: cash runs out within a month.",
         (C("runway_days", "<", T("crisis_runway_days")),),
         (Assert("runway_band", "critical"), RaiseProblem("cash_runs_out_within_month")), 0.95, P_BAND),
    Rule("R18", G2, "Runway of 30-60 days is short.",
         (C("runway_days", ">=", T("crisis_runway_days")), C("runway_days", "<", T("short_runway_days"))),
         (Assert("runway_band", "short"), RaiseProblem("short_cash_runway")), 0.85, P_BAND),
    Rule("R19", G2, "Runway of 60-90 days is a thin buffer.",
         (C("runway_days", ">=", T("short_runway_days")), C("runway_days", "<", T("safe_runway_days"))),
         (Assert("runway_band", "moderate"), RaiseProblem("thin_cash_buffer")), 0.60, P_BAND),
    Rule("R20", G2, "Runway of 90+ days is comfortable.",
         (C("runway_days", ">=", T("safe_runway_days")),),
         (Assert("runway_band", "comfortable"), AddStrength("Comfortable cash runway (3+ months)")), 1.0, P_BAND),
    Rule("R21", G2, "Negative net cash flow means the business burns cash every month.",
         (C("net_monthly_cash_flow", "<", 0),),
         (Assert("cf_band", "negative"), RaiseProblem("monthly_cash_burn")), 0.90, P_BAND),
    Rule("R22", G2, "Burning cash AND under 30 days of runway = imminent crisis (chains R17 + R21).",
         (C("cf_band", "==", "negative"), C("runway_band", "==", "critical")),
         (RaiseProblem("imminent_cash_crisis"),), 0.95, P_CHAIN),

    # =====================================================================
    # GROUP 3 - RECEIVABLES / CREDIT CONTROL
    # =====================================================================
    Rule("R23", G3, "Receivables-to-sales = months of sales owed by customers.",
         (known("accounts_receivable"), known("monthly_sales")),
         (Compute("receivables_to_sales", "receivables_to_sales"),), 1.0, P_COMPUTE),
    Rule("R24", G3, "Credit gap = customer collection days - supplier payment days.",
         (known("collection_days"), known("payment_days")),
         (Compute("credit_gap_days", "credit_gap_days"),), 1.0, P_COMPUTE),
    Rule("R25", G3, "Collection within 60 days is normal.",
         (C("collection_days", "<=", T("slow_collection_days")),),
         (Assert("collection_band", "normal"),), 1.0, P_BAND),
    Rule("R26", G3, "Collection of 60-90 days is slow.",
         (C("collection_days", ">", T("slow_collection_days")),
          C("collection_days", "<=", T("very_slow_collection_days"))),
         (Assert("collection_band", "slow"),), 1.0, P_BAND),
    Rule("R27", G3, "Collection over 90 days is a severe delay.",
         (C("collection_days", ">", T("very_slow_collection_days")),),
         (Assert("collection_band", "very_slow"), RaiseProblem("severe_collection_delay")), 0.90, P_BAND),
    Rule("R28", G3, "Slow or very slow collections indicate weak credit control (chains R26/R27).",
         (C("collection_band", "in", ("slow", "very_slow")),),
         (RaiseProblem("weak_credit_control"),), 0.60, P_CHAIN),
    Rule("R29", G3, "Receivables above 1.5 months of sales are too high.",
         (C("receivables_to_sales", ">", T("max_receivables_to_sales")),),
         (RaiseProblem("receivables_too_high"),), 0.75, P_DIAG),
    Rule("R30", G3, "Customers taking 30+ days longer than suppliers means you finance customers.",
         (C("credit_gap_days", ">", T("max_credit_gap_days")),),
         (RaiseProblem("financing_customers"),), 0.70, P_DIAG),
    Rule("R31", G3, "Slow collections during a cash shortage trap cash (chains collection + runway bands).",
         (C("collection_band", "in", ("slow", "very_slow")),
          C("runway_band", "in", ("critical", "short"))),
         (RaiseProblem("receivables_trapping_cash"),), 0.85, P_CHAIN),
    Rule("R32", G3, "Fast collection and low receivables show disciplined credit control.",
         (C("collection_days", "<=", T("good_collection_days")),
          C("receivables_to_sales", "<=", T("healthy_receivables_to_sales"))),
         (AddStrength("Disciplined collections"),), 1.0, P_DIAG),

    # =====================================================================
    # GROUP 4 - INVENTORY
    # =====================================================================
    Rule("R33", G4, "Inventory-to-sales = months of sales held as stock.",
         (known("inventory_value"), known("monthly_sales")),
         (Compute("inventory_to_sales", "inventory_to_sales"),), 1.0, P_COMPUTE),
    Rule("R34", G4, "Stock taking 90-180 days to sell is slow-moving.",
         (C("stock_days", ">", T("slow_stock_days")), C("stock_days", "<=", T("dead_stock_days"))),
         (Assert("inventory_band", "slow"), RaiseProblem("slow_moving_stock")), 0.75, P_BAND),
    Rule("R35", G4, "Stock taking over 180 days to sell risks becoming dead stock.",
         (C("stock_days", ">", T("dead_stock_days")),),
         (Assert("inventory_band", "dead"), RaiseProblem("dead_stock_risk")), 0.85, P_BAND),
    Rule("R36", G4, "Inventory above 2 months of sales is overstocking.",
         (C("inventory_to_sales", ">", T("max_inventory_to_sales")),),
         (RaiseProblem("overstocking"),), 0.70, P_DIAG),
    Rule("R37", G4, "Liquidity locked in stock that is also slow-moving = cash trapped (chains R10 + R34/R35).",
         (has_problem("liquidity_locked_in_inventory"), C("inventory_band", "in", ("slow", "dead"))),
         (RaiseProblem("cash_trapped_in_stock"),), 0.80, P_CHAIN),
    Rule("R38", G4, "Restaurants holding stock over 7 days risk spoilage.",
         (C("business_type", "==", "restaurant"), C("stock_days", ">", T("perishable_stock_days"))),
         (RaiseProblem("perishable_stock"),), 0.80, P_DIAG),
    Rule("R39", G4, "Low stock days and low inventory-to-sales indicate lean inventory.",
         (C("stock_days", "<=", T("lean_stock_days")),
          C("inventory_to_sales", "<=", T("lean_inventory_to_sales"))),
         (AddStrength("Lean inventory"),), 1.0, P_DIAG),

    # =====================================================================
    # GROUP 5 - PAYABLES / SUPPLIER TERMS
    # =====================================================================
    Rule("R40", G5, "Cash conversion cycle = stock days + collection days - payment days.",
         (known("stock_days"), known("collection_days"), known("payment_days")),
         (Compute("cash_conversion_cycle", "cash_conversion_cycle"),), 1.0, P_COMPUTE),
    Rule("R41", G5, "A cash conversion cycle above 90 days is long.",
         (C("cash_conversion_cycle", ">", T("long_ccc_days")),),
         (Assert("ccc_band", "long"), RaiseProblem("long_ccc")), 0.75, P_BAND),
    Rule("R42", G5, "A cash conversion cycle of zero or less means suppliers finance operations.",
         (C("cash_conversion_cycle", "<=", 0),),
         (Assert("ccc_band", "favourable"), AddStrength("Suppliers finance your operations (CCC <= 0)")), 1.0, P_BAND),
    Rule("R43", G5, "Paying suppliers in under 15 days wastes free supplier credit.",
         (C("accounts_payable", ">", 0), C("payment_days", "<", T("fast_payment_days"))),
         (RaiseProblem("paying_suppliers_too_fast"),), 0.65, P_DIAG),
    Rule("R44", G5, "Paying suppliers after 90+ days is dangerously stretched.",
         (C("payment_days", ">", T("stretched_payment_days")),),
         (RaiseProblem("stretched_payables"),), 0.80, P_DIAG),
    Rule("R45", G5, "Delaying suppliers while cash is short strains supplier relationships.",
         (yes("delaying_suppliers"), C("runway_band", "in", ("critical", "short"))),
         (RaiseProblem("supplier_strain"),), 0.80, P_CHAIN),
    Rule("R46", G5, "Long cash cycle plus negative cash flow = working-capital gap (chains R41 + R21).",
         (C("ccc_band", "==", "long"), C("cf_band", "==", "negative")),
         (RaiseProblem("working_capital_gap"),), 0.85, P_CHAIN),

    # =====================================================================
    # GROUP 6 - DEBT BURDEN
    # =====================================================================
    Rule("R47", G6, "Debt service ratio = installment / gross profit.",
         (known("monthly_installment"), known("monthly_gross_profit")),
         (Compute("debt_service_ratio", "debt_service_ratio"),), 1.0, P_COMPUTE),
    Rule("R48", G6, "Installments of 30% of gross profit or less are affordable.",
         (C("debt_service_ratio", "<=", T("dsr_moderate")),),
         (Assert("debt_band", "normal"), AddStrength("Affordable debt repayments")), 1.0, P_BAND),
    Rule("R49", G6, "Installments of 30-50% of gross profit are a high load.",
         (C("debt_service_ratio", ">", T("dsr_moderate")), C("debt_service_ratio", "<=", T("dsr_heavy"))),
         (Assert("debt_band", "moderate"), RaiseProblem("high_debt_servicing")), 0.70, P_BAND),
    Rule("R50", G6, "Installments above 50% of gross profit are unsustainable.",
         (C("debt_service_ratio", ">", T("dsr_heavy")),),
         (Assert("debt_band", "heavy"), RaiseProblem("unsustainable_debt")), 0.90, P_BAND),
    Rule("R51", G6, "Planning expansion while debt is heavy is dangerous (chains R50).",
         (C("debt_band", "==", "heavy"), yes("planning_expansion")),
         (RaiseProblem("expansion_with_heavy_debt"),), 0.90, P_CHAIN),
    Rule("R52", G6, "Running finance fully used while cash is short = no borrowing headroom.",
         (yes("rf_maxed"), C("runway_band", "in", ("critical", "short"))),
         (RaiseProblem("no_borrowing_headroom"),), 0.85, P_CHAIN),

    # =====================================================================
    # GROUP 7 - SEASONAL & BUSINESS-TYPE SPECIFIC
    # =====================================================================
    Rule("R53", G7, "Off-season with less than 3 months of runway = off-season squeeze.",
         (C("season", "==", "off-season"), C("runway_band", "in", ("critical", "short", "moderate"))),
         (RaiseProblem("off_season_squeeze"),), 0.80, P_CHAIN),
    Rule("R54", G7, "Slow or dead stock during peak season signals wrong product mix or pricing.",
         (C("season", "==", "peak"), C("inventory_band", "in", ("slow", "dead"))),
         (RaiseProblem("peak_season_stock_not_selling"),), 0.85, P_CHAIN),
    Rule("R55", G7, "Manufacturers with a CCC above 120 days have a long production-to-cash cycle.",
         (C("business_type", "==", "manufacturing"),
          C("cash_conversion_cycle", ">", T("manufacturing_long_ccc_days"))),
         (RaiseProblem("long_production_cycle"),), 0.75, P_DIAG),
    Rule("R56", G7, "Wholesale/trading with a gross margin below 8% is thin-margin trading.",
         (C("business_type", "in", ("wholesale", "trading")),
          C("gross_margin_pct", "<", T("thin_margin_pct"))),
         (RaiseProblem("thin_margin_trading"),), 0.70, P_DIAG),
    Rule("R57", G7, "Retail/restaurant collecting slower than 15 days gives unnecessary credit.",
         (C("business_type", "in", ("retail", "restaurant")),
          C("collection_days", ">", T("cash_business_credit_days"))),
         (RaiseProblem("credit_in_cash_business"),), 0.70, P_DIAG),
    Rule("R58", G7, "Service firms collecting slower than 45 days have slow billing.",
         (C("business_type", "==", "services"), C("collection_days", ">", T("services_billing_days"))),
         (RaiseProblem("slow_service_billing"),), 0.70, P_DIAG),

    # =====================================================================
    # GROUP 8 - SYMPTOM-BASED (Yes/No answers)
    # =====================================================================
    Rule("R59", G8, "Customers often paying late indicates weak credit control (combines with R28).",
         (yes("late_customers"),), (RaiseProblem("weak_credit_control"),), 0.50, P_SYMPTOM),
    Rule("R60", G8, "Delaying supplier payments strains supplier relationships (combines with R45).",
         (yes("delaying_suppliers"),), (RaiseProblem("supplier_strain"),), 0.60, P_SYMPTOM),
    Rule("R61", G8, "Stock piling up indicates overstocking (combines with R36).",
         (yes("stock_piling"),), (RaiseProblem("overstocking"),), 0.50, P_SYMPTOM),
    Rule("R62", G8, "Sales growing but cash shrinking with a long cash cycle = overtrading.",
         (yes("sales_up_cash_down"), C("ccc_band", "==", "long")),
         (RaiseProblem("overtrading"),), 0.85, P_CHAIN),
    Rule("R63", G8, "Sales growing but cash shrinking suggests overtrading (combines with R62).",
         (yes("sales_up_cash_down"),), (RaiseProblem("overtrading"),), 0.50, P_SYMPTOM),
    Rule("R64", G8, "Using personal money for the business means the owner is subsidising it.",
         (yes("personal_money"),), (RaiseProblem("owner_subsidising"),), 0.70, P_SYMPTOM),
    Rule("R65", G8, "Personal money covering a cash-burning business hides a structural loss.",
         (yes("personal_money"), C("cf_band", "==", "negative")),
         (RaiseProblem("hidden_structural_loss"),), 0.85, P_CHAIN),
    Rule("R66", G8, "Planning expansion with less than 90 days of runway is not affordable.",
         (yes("planning_expansion"), C("runway_band", "!=", "comfortable")),
         (RaiseProblem("expansion_not_affordable"),), 0.85, P_CHAIN),
    Rule("R67", G8, "One customer above 40% of sales is a concentration risk.",
         (yes("big_customer"),), (RaiseProblem("customer_concentration"),), 0.60, P_SYMPTOM),
    Rule("R68", G8, "A dominant customer plus high receivables strengthens concentration risk (combines with R67).",
         (yes("big_customer"), C("receivables_to_sales", ">", T("healthy_receivables_to_sales"))),
         (RaiseProblem("customer_concentration"),), 0.80, P_SYMPTOM),
    Rule("R69", G8, "Overdue taxes create penalty and account-attachment risk.",
         (yes("overdue_tax"),), (RaiseProblem("tax_arrears"),), 0.90, P_SYMPTOM),

    # =====================================================================
    # GROUP 9 - FINAL STATUS  (fires last because of its low priority)
    # =====================================================================
    Rule("R70", G9, "After all diagnosis, compute the health score (0-100) - only if data is sufficient.",
         (C("data_sufficient", "==", True),), (Compute("health_score", "health_score"),), 1.0, P_SCORE),
    Rule("R71", G9, "Count the Critical problems diagnosed.",
         (C("data_sufficient", "==", True),),
         (Compute("critical_problem_count", "critical_problem_count"),), 1.0, P_SCORE),
    Rule("R72", G9, "Count the High problems diagnosed.",
         (C("data_sufficient", "==", True),),
         (Compute("high_problem_count", "high_problem_count"),), 1.0, P_SCORE),
    Rule("R73", G9, "An imminent cash crisis forces status Crisis, whatever the score (override).",
         (has_problem("imminent_cash_crisis"), C("status", "unknown")),
         (Assert("status", "Crisis"),), 1.0, P_OVERRIDE),
    Rule("R74", G9, "Health score below 35 = Crisis.",
         (C("health_score", "<", T("crisis_score")), C("status", "unknown")),
         (Assert("status", "Crisis"),), 1.0, P_STATUS),
    Rule("R75", G9, "Health score 35-55 = Risky.",
         (C("health_score", ">=", T("crisis_score")), C("health_score", "<", T("watch_score")),
          C("status", "unknown")),
         (Assert("status", "Risky"),), 1.0, P_STATUS),
    Rule("R76", G9, "SAFETY CAP: any Critical problem limits the status to Risky (never Watch/Healthy).",
         (C("health_score", ">=", T("watch_score")), C("critical_problem_count", ">", 0),
          C("status", "unknown")),
         (Assert("status", "Risky"),), 1.0, P_STATUS),
    Rule("R77", G9, "Health score 55-75 with no Critical problem = Watch.",
         (C("health_score", ">=", T("watch_score")), C("health_score", "<", T("healthy_score")),
          C("critical_problem_count", "==", 0), C("status", "unknown")),
         (Assert("status", "Watch"),), 1.0, P_STATUS),
    Rule("R78", G9, "SAFETY CAP: score 75+ but a High problem exists = Watch (Healthy needs zero High).",
         (C("health_score", ">=", T("healthy_score")), C("critical_problem_count", "==", 0),
          C("high_problem_count", ">", 0), C("status", "unknown")),
         (Assert("status", "Watch"),), 1.0, P_STATUS),
    Rule("R79", G9, "Score 75+ with zero Critical and zero High problems = Healthy.",
         (C("health_score", ">=", T("healthy_score")), C("critical_problem_count", "==", 0),
          C("high_problem_count", "==", 0), C("status", "unknown")),
         (Assert("status", "Healthy"),), 1.0, P_STATUS),
    Rule("R80", G9, "A Crisis status calls for a 30-day cash survival plan.",
         (C("status", "==", "Crisis"),),
         (Recommend("Start a 30-day cash survival plan: daily cash log, stop all capital spending",
                    "In a crisis, daily control of every rupee is the only way to avoid default.",
                    "Critical"),), 1.0, P_STATUS_DECISION),
    Rule("R81", G9, "A Healthy status calls for maintaining reserves and quarterly review.",
         (C("status", "==", "Healthy"),),
         (Recommend("Maintain a 3-month cash reserve and review this diagnosis quarterly",
                    "Healthy businesses stay healthy by monitoring before problems appear.",
                    "Low"),), 1.0, P_STATUS_DECISION),

    # =====================================================================
    # GROUP 0 - DATA SUFFICIENCY  (highest priority: checked before anything else)
    #   An expert must not conclude without data. Missing essentials -> the
    #   status becomes "Insufficient data" and the engine HALTS (no score).
    #   (Numbered R82+ so that the original rule IDs R01-R81 stay unchanged.)
    # =====================================================================
    Rule("R82", G0, "Cash in hand is essential for any liquidity diagnosis.",
         (C("cash_in_hand", "missing"),),
         (FlagMissing("cash_in_hand", "Cash in hand"),), 1.0, P_MISSING),
    Rule("R83", G0, "Bank balance is essential for any liquidity diagnosis.",
         (C("bank_balance", "missing"),),
         (FlagMissing("bank_balance", "Bank balance"),), 1.0, P_MISSING),
    Rule("R84", G0, "Monthly sales must be known and above zero (all sales ratios depend on it).",
         (C("monthly_sales", "empty"),),
         (FlagMissing("monthly_sales", "Monthly sales (must be greater than 0)"),), 1.0, P_MISSING),
    Rule("R85", G0, "Gross margin is needed to estimate gross profit and cash flow.",
         (C("gross_margin_pct", "missing"),),
         (FlagMissing("gross_margin_pct", "Gross profit margin (%)"),), 1.0, P_MISSING),
    Rule("R86", G0, "Monthly fixed expenses are needed to compute the cash runway.",
         (C("monthly_fixed_expenses", "missing"),),
         (FlagMissing("monthly_fixed_expenses", "Monthly fixed expenses"),), 1.0, P_MISSING),
    Rule("R87", G0, "At least one current liability is needed - unless the owner confirms the "
         "business owes nothing (see R95).",
         (C("owes_nothing", "not_yes"), C("accounts_payable", "empty"),
          C("short_term_loans", "empty"), C("other_current_liabilities", "empty")),
         (FlagMissing("current_liabilities",
                      "At least one current liability (payables, short-term loans or other dues)"),),
         1.0, P_MISSING),
    Rule("R88", G0, "SANITY: receivables exist but monthly sales is zero.",
         (C("monthly_sales", "empty"), C("accounts_receivable", ">", 0)),
         (Warn("Receivables are entered but monthly sales is 0 - check your inputs."),), 1.0, P_SANITY),
    Rule("R89", G0, "SANITY: positive sales with a 0% gross margin is unusual.",
         (C("gross_margin_pct", "==", 0), C("monthly_sales", ">", 0)),
         (Warn("Gross margin is 0% while sales are positive - check your inputs."),), 1.0, P_SANITY),
    Rule("R90", G0, "SANITY: stock has value but 'days to sell stock' is zero.",
         (C("inventory_value", ">", 0), C("stock_days", "empty")),
         (Warn("Inventory has a value but 'days to sell stock' is 0 - check your inputs."),), 1.0, P_SANITY),
    Rule("R91", G0, "SANITY: receivables exist but collection days is zero.",
         (C("accounts_receivable", ">", 0), C("collection_days", "empty")),
         (Warn("Receivables are entered but 'collection days' is 0 - check your inputs."),), 1.0, P_SANITY),
    Rule("R92", G0, "SANITY: payables exist but payment days is zero.",
         (C("accounts_payable", ">", 0), C("payment_days", "empty")),
         (Warn("Payables are entered but 'payment days' is 0 - check your inputs."),), 1.0, P_SANITY),
    Rule("R93", G0, "If any essential fact is missing: status = Insufficient data and STOP (no conclusions).",
         (C("missing_facts_count", ">", 0),),
         (Assert("status", "Insufficient data"), Halt()), 1.0, P_VERDICT),
    Rule("R94", G0, "If no essential fact is missing, the data is sufficient for a diagnosis.",
         (C("missing_facts_count", "unknown"),),
         (Assert("data_sufficient", True),), 1.0, P_VERDICT),

    # A debt-free business: liquidity ratios cannot be computed (nothing to divide by),
    # but that is GOOD news, not missing data. (Numbered R95 to keep earlier IDs stable.)
    Rule("R95", G1, "Owner confirms the business owes nothing: there is no short-term debt, so "
         "liquidity ratios do not apply - a strength, not missing data.",
         (yes("owes_nothing"), C("accounts_payable", "empty"), C("short_term_loans", "empty"),
          C("other_current_liabilities", "empty")),
         (Assert("cr_band", "no_debt"), AddStrength("No short-term debt")), 1.0, P_BAND),
]
