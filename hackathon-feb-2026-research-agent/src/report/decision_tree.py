"""Decision tree visualization — generates a readable text tree from agent metadata."""


def _short_args(args: dict) -> str:
    """Format tool call args into a compact summary."""
    parts = []
    for k, v in args.items():
        if isinstance(v, list):
            v = ", ".join(str(i) for i in v)
        v = str(v)
        if len(v) > 50:
            v = v[:47] + "..."
        parts.append(f"{k}={v}")
    return "  ".join(parts)


def _friendly_tool_name(tool: str) -> str:
    """Convert snake_case tool name to a readable label."""
    mapping = {
        "get_company_financials": "Company Financials",
        "get_historical_revenue": "Historical Revenue",
        "get_company_comparison": "Company Comparison",
        "search_company_info": "Company Info Search",
        "search_competitive_analysis": "Competitive Analysis",
        "search_product_info": "Product Info Search",
        "search_market_trends": "Market Trends Search",
    }
    return mapping.get(tool, tool.replace("_", " ").title())


def build_decision_tree_markdown(metadata: dict) -> str:
    """Build a readable plain-text tree from agent run metadata.

    Args:
        metadata: dict with keys companies, tickers,
                  financial_tool_calls, competitor_tool_calls.

    Returns:
        Plain-text string for rendering inside st.code().
    """
    companies = metadata.get("companies", [])
    tickers = metadata.get("tickers", [])
    fin_calls = metadata.get("financial_tool_calls", [])
    comp_calls = metadata.get("competitor_tool_calls", [])

    lines = []

    # Root
    lines.append("🔷 User Query")
    lines.append("│")

    # Parse
    lines.append(f"├── 📋 Parse → {', '.join(companies)}  ·  Tickers: {', '.join(tickers)}")
    lines.append("│")

    # Parallel split
    lines.append("├── ⚡ parallel execution")
    lines.append("│")

    # Number Cruncher
    lines.append(f"├── 📊 Number Cruncher — {len(fin_calls)} tool call{'s' if len(fin_calls) != 1 else ''}")
    for i, tc in enumerate(fin_calls):
        is_last = i == len(fin_calls) - 1
        prefix = "│   └── " if is_last else "│   ├── "
        name = _friendly_tool_name(tc.get("tool", "?"))
        args_str = _short_args(tc.get("args", {}))
        lines.append(f"{prefix}🔧 {name}  ({args_str})")
    lines.append("│")

    # Street Scout
    lines.append(f"├── 🔍 Street Scout — {len(comp_calls)} tool call{'s' if len(comp_calls) != 1 else ''}")
    for i, tc in enumerate(comp_calls):
        is_last = i == len(comp_calls) - 1
        prefix = "│   └── " if is_last else "│   ├── "
        name = _friendly_tool_name(tc.get("tool", "?"))
        args_str = _short_args(tc.get("args", {}))
        lines.append(f"{prefix}🔧 {name}  ({args_str})")
    lines.append("│")

    # Verdict
    lines.append("└── 📝 Verdict → Final Report")

    return "\n".join(lines)
