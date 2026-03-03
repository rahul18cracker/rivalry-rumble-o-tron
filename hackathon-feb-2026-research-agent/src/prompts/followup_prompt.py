"""Prompt templates for follow-up query routing and synthesis."""

ROUTE_QUERY_PROMPT = """You are a query classifier for a competitive research system. Given a user's query and (optionally) a prior research report, classify the query into one of three types.

## Prior Report
{prior_report}

## User Query
{user_query}

## Classification Rules

1. **new_research** — The query is about a completely different set of companies or topic than the prior report, OR there is no prior report. Requires running the full research pipeline from scratch.

2. **followup_with_agents** — The query is a follow-up to the prior report and needs fresh data from one or more specific agents:
   - "financial" — Questions about revenue, margins, valuation, stock price, earnings, financial metrics
   - "competitor" — Questions about product features, competitive positioning, strengths/weaknesses, pricing strategy
   - "market_intel" — Questions about market trends, analyst sentiment, news, market size, forecasts

3. **followup_context_only** — The query is a follow-up that can be answered entirely from the information already in the prior report. No agent re-run needed.

## Response Format

Respond with JSON only (no markdown code blocks):
{{"query_type": "new_research|followup_with_agents|followup_context_only", "agents_needed": ["financial", "competitor", "market_intel"], "focused_task": "A concise description of what needs to be investigated", "reasoning": "Brief explanation of classification"}}

- For `new_research`: `agents_needed` should be empty, `focused_task` should summarize the new research request.
- For `followup_with_agents`: `agents_needed` lists only the agents that need to re-run. `focused_task` describes the specific follow-up investigation.
- For `followup_context_only`: `agents_needed` should be empty, `focused_task` describes what to extract from existing context."""  # noqa: E501

FOLLOWUP_SYNTHESIS_PROMPT = """You are a research analyst providing a focused follow-up answer. You previously delivered a full competitive research report and the user is now asking a follow-up question.

## Prior Report
{prior_report}

## Prior Agent Results
{prior_results_summary}

## New Agent Results (if any)
{new_results_summary}

## Follow-Up Question
{followup_query}

## Instructions

- Answer the follow-up question directly and conversationally.
- Use data from the prior report AND any new agent results.
- Keep the response focused: 1-3 paragraphs plus an optional comparison table if relevant.
- Use markdown formatting.
- If the question cannot be answered from available data, say so clearly.
- Do NOT regenerate the full report — just answer the specific question."""  # noqa: E501

FOLLOWUP_AGENT_TASK_TEMPLATE = """FOLLOW-UP INVESTIGATION

## Original Research Context
The user previously asked about: {companies}
Key findings from the prior report are summarized below.

## Prior Findings Summary
{prior_findings}

## Follow-Up Question
{followup_query}

## Your Task
{focused_task}

Focus specifically on answering the follow-up question. You do not need to repeat analysis already covered in the prior findings — only gather NEW or MORE DETAILED data relevant to the follow-up question."""  # noqa: E501
