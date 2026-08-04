import glob
import json
import os
import sys

# Pricing table in USD per million tokens.
# Shape: input, output, cacheRead, cacheWrite, cacheWrite1h.
# Refreshed against official provider pricing on 2026-07-31.
DEFAULT_PRICING = {
    "input": 1.0,
    "output": 5.0,
    "cacheRead": 0.1,
    "cacheWrite": 0.0,
    "cacheWrite1h": 0.0,
}


def price(input_, output, cache_read, cache_write=0.0, cache_write_1h=None):
    return {
        "input": float(input_),
        "output": float(output),
        "cacheRead": float(cache_read),
        "cacheWrite": float(cache_write),
        "cacheWrite1h": float(cache_write if cache_write_1h is None else cache_write_1h),
    }


MODEL_PRICING = {
    # Current local Pi/Hermes aliases in ~/.pi/agent/models.json.
    "hai-proxy/anthropic--claude-4.8-opus": price(5.0, 25.0, 0.5, 6.25, 10.0),
    "hai-proxy/anthropic--claude-4.6-sonnet": price(3.0, 15.0, 0.3, 3.75, 6.0),
    "hai-proxy/anthropic--claude-4.5-haiku": price(1.0, 5.0, 0.1, 1.25, 2.0),
    "hai-litellm/gpt-5.5": price(5.0, 30.0, 0.5),
    "hai-litellm/gpt-5.4": price(2.5, 15.0, 0.25),
    "hai-mini/gpt-5-mini": price(0.25, 2.0, 0.025),
    "hai-gemini/gemini-3.5-flash": price(1.5, 9.0, 0.15),
    "hai-gemini/gemini-3.1-flash-lite": price(0.25, 1.5, 0.025),

    # OpenAI direct / compatible model names.
    "gpt-5.5": price(5.0, 30.0, 0.5),
    "gpt-5.4": price(2.5, 15.0, 0.25),
    "gpt-5.4-mini": price(0.75, 4.5, 0.075),
    "gpt-5-mini": price(0.25, 2.0, 0.025),
    "gpt-oss-120b": price(0.25, 0.69, 0.025),

    # Anthropic direct / generic aliases.
    "claude-opus-4.8": price(5.0, 25.0, 0.5, 6.25, 10.0),
    "claude-sonnet-4.6": price(3.0, 15.0, 0.3, 3.75, 6.0),
    "claude-haiku-4.5": price(1.0, 5.0, 0.1, 1.25, 2.0),
    "opus": price(5.0, 25.0, 0.5, 6.25, 10.0),
    "sonnet": price(3.0, 15.0, 0.3, 3.75, 6.0),
    "haiku": price(1.0, 5.0, 0.1, 1.25, 2.0),

    # Gemini direct / compatible model names.
    "gemini-3.5-flash": price(1.5, 9.0, 0.15),
    "gemini-3.1-flash-lite": price(0.25, 1.5, 0.025),
    "gemini-3.1-pro": price(2.0, 12.0, 0.2),
    "gemini-2.5-flash": price(1.5, 9.0, 0.15),

    # Historical google-antigravity aliases kept for old logs.
    "google-antigravity/claude-opus-4-6": price(5.0, 25.0, 0.5, 6.25, 10.0),
    "google-antigravity/claude-sonnet-4-6": price(3.0, 15.0, 0.3, 3.75, 6.0),
    "google-antigravity/gemini-3.1-pro": price(2.0, 12.0, 0.2),
    "google-antigravity/gemini-3.5-flash": price(1.5, 9.0, 0.15),
    "google-antigravity/gpt-oss-120b": price(0.25, 0.69, 0.025),
}


def get_pricing(model_name, provider=None):
    if not model_name:
        return price(0.0, 0.0, 0.0)

    lower_table = {key.lower(): value for key, value in MODEL_PRICING.items()}
    model_lower = model_name.lower()
    full_key = f"{provider.lower()}/{model_lower}" if provider else model_lower

    # Prefer exact provider/model and exact model matches before substring aliases.
    if full_key in lower_table:
        return lower_table[full_key]
    if model_lower in lower_table:
        return lower_table[model_lower]

    # Then match aliases, longest first so gpt-5.4-mini beats gpt-5.4, etc.
    for key in sorted(lower_table, key=len, reverse=True):
        if key in full_key or key in model_lower:
            return lower_table[key]

    return DEFAULT_PRICING.copy()


def parse_usage(usage, model_name, provider=None):
    if not usage:
        return {
            "input": 0,
            "output": 0,
            "cacheRead": 0,
            "cacheWrite": 0,
            "cost_in": 0.0,
            "cost_out": 0.0,
            "cost_cache": 0.0,
            "cost_cache_write": 0.0,
            "cost_total": 0.0,
        }

    input_tokens = usage.get("input", 0) or 0
    output_tokens = usage.get("output", 0) or 0
    cache_read = usage.get("cacheRead", 0) or 0
    cache_write = usage.get("cacheWrite", 0) or 0
    cache_write_1h = usage.get("cacheWrite1h", 0) or 0
    cache_write_5m = max(cache_write - cache_write_1h, 0)

    # Prefer harness/provider cost when present. This catches provider-specific
    # tiers, proxy markup/discounts, and other billing rules local estimates miss.
    logged_cost = usage.get("cost", {})
    if isinstance(logged_cost, dict) and logged_cost.get("total", 0.0) > 0.0:
        return {
            "input": input_tokens,
            "output": output_tokens,
            "cacheRead": cache_read,
            "cacheWrite": cache_write,
            "cost_in": logged_cost.get("input", 0.0),
            "cost_out": logged_cost.get("output", 0.0),
            "cost_cache": logged_cost.get("cacheRead", 0.0),
            "cost_cache_write": logged_cost.get("cacheWrite", 0.0),
            "cost_total": logged_cost.get("total", 0.0),
        }

    pricing = get_pricing(model_name, provider)
    cost_in = (input_tokens / 1_000_000.0) * pricing["input"]
    cost_out = (output_tokens / 1_000_000.0) * pricing["output"]
    cost_cache = (cache_read / 1_000_000.0) * pricing["cacheRead"]
    cost_cache_write = (
        (cache_write_5m / 1_000_000.0) * pricing["cacheWrite"]
        + (cache_write_1h / 1_000_000.0) * pricing["cacheWrite1h"]
    )
    cost_total = cost_in + cost_out + cost_cache + cost_cache_write

    return {
        "input": input_tokens,
        "output": output_tokens,
        "cacheRead": cache_read,
        "cacheWrite": cache_write,
        "cost_in": cost_in,
        "cost_out": cost_out,
        "cost_cache": cost_cache,
        "cost_cache_write": cost_cache_write,
        "cost_total": cost_total,
    }


def find_session_file():
    env_session = os.environ.get("PI_SESSION_FILE")
    if env_session and os.path.exists(env_session):
        return env_session

    session_files = glob.glob(os.path.expanduser("~/.pi/agent/sessions/*/*.jsonl"))
    if not session_files:
        return None
    return max(session_files, key=os.path.getmtime)


def main():
    latest_session = find_session_file()
    if not latest_session:
        print("No active Pi session log files found.")
        sys.exit(0)

    print("=" * 60)
    print(f"ACTIVE PI SESSION: {os.path.basename(latest_session)}")
    print(f"Path: {latest_session}")
    print("=" * 60)

    main_turns = 0
    main_input = 0
    main_output = 0
    main_cache = 0
    main_cache_write = 0
    main_cost = 0.0
    main_models = set()
    main_efforts = set()

    subagents = []

    with open(latest_session, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line)

                if data.get("type") == "thinking_level_change":
                    level = data.get("thinkingLevel")
                    if level:
                        main_efforts.add(level)

                msg = data.get("message", {})
                role = msg.get("role")

                if role == "assistant":
                    content = msg.get("content", [])
                    is_only_calls = all(c.get("type") == "toolCall" for c in content) if content else False

                    usage_data = msg.get("usage")
                    model_name = msg.get("model") or data.get("model")
                    provider = msg.get("provider") or data.get("provider")

                    if model_name:
                        full_model = f"{provider}/{model_name}" if provider else model_name
                        main_models.add(full_model)

                    if usage_data:
                        stats = parse_usage(usage_data, model_name, provider)
                        main_input += stats["input"]
                        main_output += stats["output"]
                        main_cache += stats["cacheRead"]
                        main_cache_write += stats["cacheWrite"]
                        main_cost += stats["cost_total"]
                        if not is_only_calls:
                            main_turns += 1

                elif role == "toolResult" and msg.get("toolName") == "subagent":
                    tool_call_id = msg.get("toolCallId")
                    details = msg.get("details", {})
                    agent_name = details.get("agent") or "subagent"
                    results = details.get("results", [])

                    if results:
                        last_result = results[-1]
                        usage_data = last_result.get("usage", {})
                        model_name = last_result.get("model")
                        provider = last_result.get("provider") or details.get("provider")
                        turns = usage_data.get("turns", 1)
                        stats = parse_usage(usage_data, model_name, provider)

                        subagents.append({
                            "line": line_num,
                            "id": tool_call_id,
                            "agent": agent_name,
                            "model": model_name,
                            "turns": turns,
                            "stats": stats,
                        })
            except Exception:
                pass

    print("\n--- MAIN SESSION STATS ---")
    print(f"Model(s):     {', '.join(sorted(main_models)) if main_models else 'Unknown'}")
    print(f"Effort(s):    {', '.join(sorted(main_efforts)) if main_efforts else 'Unknown'}")
    print(f"Turns:        {main_turns}")
    print(
        f"Tokens:       {main_input:,} input | {main_output:,} output | "
        f"{main_cache:,} cache read | {main_cache_write:,} cache write"
    )
    print(f"Est. Cost:    ${main_cost:.4f}")

    if subagents:
        print("\n--- SUBAGENT RUNS BREAKDOWN ---")
        sub_cost_total = 0.0
        for s in subagents:
            stats = s["stats"]
            sub_cost_total += stats["cost_total"]
            print(f"Line {s['line']} | {s['agent']} ({s['model']}) [ID: {s['id']}]:")
            print(f"  Turns:      {s['turns']}")
            print(
                f"  Tokens:     {stats['input']:,} input | {stats['output']:,} output | "
                f"{stats['cacheRead']:,} cache read | {stats['cacheWrite']:,} cache write"
            )
            print(f"  Est. Cost:  ${stats['cost_total']:.4f}")
            print("-" * 40)

        print("\n--- SESSION TOTAL SUMMARY ---")
        print(f"Main Session Cost:  ${main_cost:.4f}")
        print(f"Subagent Cost:      ${sub_cost_total:.4f}")
        print(f"Total Session Cost: ${main_cost + sub_cost_total:.4f}")
    else:
        print("\nNo subagent runs logged in this session yet.")
        print(f"Total Session Cost: ${main_cost:.4f}")

    print("=" * 60)


if __name__ == "__main__":
    main()
