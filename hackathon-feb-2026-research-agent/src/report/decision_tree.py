"""Decision tree visualization — generates Graphviz DOT from agent metadata."""

import json


def _escape(text: str) -> str:
    """Escape special chars for DOT labels."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _short_args(args: dict) -> str:
    """Format tool call args into a short single-line summary."""
    parts = []
    for k, v in args.items():
        if isinstance(v, list):
            v = ", ".join(str(i) for i in v)
        v = str(v)
        if len(v) > 40:
            v = v[:37] + "..."
        parts.append(f"{k}={v}")
    return ", ".join(parts)


def build_decision_tree_dot(metadata: dict) -> str:
    """Build a Graphviz DOT string from agent run metadata.

    Args:
        metadata: dict with keys companies, tickers,
                  financial_tool_calls, competitor_tool_calls.

    Returns:
        DOT-language string suitable for st.graphviz_chart().
    """
    companies = metadata.get("companies", [])
    tickers = metadata.get("tickers", [])
    fin_calls = metadata.get("financial_tool_calls", [])
    comp_calls = metadata.get("competitor_tool_calls", [])

    lines = [
        'digraph decision_tree {',
        '  rankdir=TB;',
        '  bgcolor="transparent";',
        '  node [fontname="Helvetica" fontsize=11 style=filled];',
        '  edge [fontname="Helvetica" fontsize=9 color="#888888"];',
        '',
        '  // Root',
        '  query [label="User Query" shape=diamond fillcolor="#FFD54F" fontcolor="#333333"];',
        '',
        '  // Parse stage',
        f'  parse [label="Parse\\n{_escape(", ".join(companies))}\\nTickers: {_escape(", ".join(tickers))}" '
        f'shape=box fillcolor="#E3F2FD" fontcolor="#1565C0"];',
        '  query -> parse [label="analyze"];',
        '',
    ]

    # Financial agent branch
    lines.append('  // Number Cruncher')
    lines.append(f'  financial [label="📊 Number Cruncher\\n{len(fin_calls)} tool calls" '
                 f'shape=box fillcolor="#E8F5E9" fontcolor="#2E7D32"];')
    lines.append('  parse -> financial [label="parallel"];')

    for i, tc in enumerate(fin_calls):
        node_id = f"fin_tc_{i}"
        tool_name = tc.get("tool", "?")
        args_str = _short_args(tc.get("args", {}))
        label = f"{tool_name}\\n{_escape(args_str)}"
        lines.append(f'  {node_id} [label="{label}" shape=ellipse fillcolor="#C8E6C9" fontcolor="#1B5E20"];')
        lines.append(f'  financial -> {node_id};')

    lines.append('')

    # Competitor agent branch
    lines.append('  // Street Scout')
    lines.append(f'  competitor [label="🔍 Street Scout\\n{len(comp_calls)} tool calls" '
                 f'shape=box fillcolor="#FFF3E0" fontcolor="#E65100"];')
    lines.append('  parse -> competitor [label="parallel"];')

    for i, tc in enumerate(comp_calls):
        node_id = f"comp_tc_{i}"
        tool_name = tc.get("tool", "?")
        args_str = _short_args(tc.get("args", {}))
        label = f"{tool_name}\\n{_escape(args_str)}"
        lines.append(f'  {node_id} [label="{label}" shape=ellipse fillcolor="#FFE0B2" fontcolor="#BF360C"];')
        lines.append(f'  competitor -> {node_id};')

    lines.append('')

    # Synthesis
    lines.append('  // Verdict')
    lines.append('  verdict [label="📝 Verdict\\nFinal Report" shape=box fillcolor="#F3E5F5" fontcolor="#6A1B9A"];')
    lines.append('  financial -> verdict [label="results"];')
    lines.append('  competitor -> verdict [label="results"];')

    lines.append('}')

    return '\n'.join(lines)
