import json
import os
import glob
import sys

# Pricing table in USD per Million tokens: (Input, Output, CacheRead)
MODEL_PRICING = {
    # google-antigravity specific pricing
    "google-antigravity/claude-opus-4-6": (5.0, 25.0, 0.5),
    "google-antigravity/claude-sonnet-4-6": (3.0, 15.0, 0.3),
    "google-antigravity/gemini-3.1-pro": (2.0, 12.0, 0.2),
    "google-antigravity/gemini-3.5-flash": (1.5, 9.0, 0.15),
    "google-antigravity/gpt-oss-120b": (0.25, 0.69, 0.025),
    
    # general model default fallback rates
    "opus": (5.0, 25.0, 0.5),
    "sonnet": (3.0, 15.0, 0.3),
    "haiku": (0.80, 4.0, 0.08),
    "gemini-3.5-flash": (1.5, 9.0, 0.15),
    "gemini-2.5-flash": (1.5, 9.0, 0.15),
    "gemini-3.1-pro": (2.0, 12.0, 0.2),
    "gpt-5.4-mini": (0.75, 4.5, 0.075),
    "gpt-5.5": (5.0, 30.0, 0.5),
    "gpt-5-mini": (0.25, 2.0, 0.025),
    "gpt-oss-120b": (0.25, 0.69, 0.025)
}

def get_pricing(model_name, provider=None):
    if not model_name:
        return (0.0, 0.0, 0.0)
    
    # Match with provider prefix if available
    if provider:
        full_key = f"{provider.lower()}/{model_name.lower()}"
        for key, pricing in MODEL_PRICING.items():
            if key.lower() == full_key or key.lower() in full_key:
                return pricing

    model_lower = model_name.lower()
    for key, pricing in MODEL_PRICING.items():
        if key in model_lower:
            return pricing
    # Default fallback (similar to flash/gpt-5-mini pricing)
    return (1.0, 5.0, 0.1)

def parse_usage(usage, model_name, provider=None):
    if not usage:
        return {
            "input": 0, "output": 0, "cacheRead": 0,
            "cost_in": 0.0, "cost_out": 0.0, "cost_cache": 0.0, "cost_total": 0.0
        }
    
    input_tokens = usage.get("input", 0) or 0
    output_tokens = usage.get("output", 0) or 0
    cache_read = usage.get("cacheRead", 0) or 0
    
    # Check if the harness already calculated a non-zero cost
    logged_cost = usage.get("cost", {})
    if isinstance(logged_cost, dict) and logged_cost.get("total", 0.0) > 0.0:
        return {
            "input": input_tokens, "output": output_tokens, "cacheRead": cache_read,
            "cost_in": logged_cost.get("input", 0.0),
            "cost_out": logged_cost.get("output", 0.0),
            "cost_cache": logged_cost.get("cacheRead", 0.0),
            "cost_total": logged_cost.get("total", 0.0)
        }
    
    # Calculate using local pricing tables
    p_in, p_out, p_cache = get_pricing(model_name, provider)
    cost_in = (input_tokens / 1000000.0) * p_in
    cost_out = (output_tokens / 1000000.0) * p_out
    cost_cache = (cache_read / 1000000.0) * p_cache
    cost_total = cost_in + cost_out + cost_cache
    
    return {
        "input": input_tokens, "output": output_tokens, "cacheRead": cache_read,
        "cost_in": cost_in, "cost_out": cost_out, "cost_cache": cost_cache, "cost_total": cost_total
    }

def main():
    # Find active session file
    session_dirs = glob.glob(os.path.expanduser('~/.pi/agent/sessions/*/*.jsonl'))
    if not session_dirs:
        print("No active Pi session log files found.")
        sys.exit(0)
        
    latest_session = max(session_dirs, key=os.path.getmtime)
    print("=" * 60)
    print(f"ACTIVE PI SESSION: {os.path.basename(latest_session)}")
    print(f"Path: {latest_session}")
    print("=" * 60)
    
    main_turns = 0
    main_input = 0
    main_output = 0
    main_cache = 0
    main_cost = 0.0
    main_models = set()
    main_efforts = set()
    
    subagents = []
    
    with open(latest_session, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                
                # Check for thinking level change
                if data.get('type') == 'thinking_level_change':
                    level = data.get('thinkingLevel')
                    if level:
                        main_efforts.add(level)
                
                msg = data.get('message', {})
                role = msg.get('role')
                
                # Check for main assistant message
                if role == 'assistant':
                    content = msg.get('content', [])
                    # Ignore if the assistant message is only tool calls
                    is_only_calls = all(c.get('type') == 'toolCall' for c in content) if content else False
                    
                    usage_data = msg.get('usage')
                    model_name = msg.get('model') or data.get('model')
                    provider = msg.get('provider') or data.get('provider')
                    
                    if model_name:
                        full_model = f"{provider}/{model_name}" if provider else model_name
                        main_models.add(full_model)
                    
                    if usage_data:
                        stats = parse_usage(usage_data, model_name, provider)
                        main_input += stats["input"]
                        main_output += stats["output"]
                        main_cache += stats["cacheRead"]
                        main_cost += stats["cost_total"]
                        if not is_only_calls:
                            main_turns += 1
                            
                # Check for subagent tool execution results
                elif role == 'toolResult' and msg.get('toolName') == 'subagent':
                    tool_call_id = msg.get('toolCallId')
                    details = msg.get('details', {})
                    agent_name = details.get('agent') or "subagent"
                    results = details.get('results', [])
                    
                    if results:
                        last_result = results[-1]
                        usage_data = last_result.get('usage', {})
                        model_name = last_result.get('model')
                        provider = last_result.get('provider') or details.get('provider')
                        turns = usage_data.get('turns', 1)
                        stats = parse_usage(usage_data, model_name, provider)
                        
                        subagents.append({
                            "line": line_num,
                            "id": tool_call_id,
                            "agent": agent_name,
                            "model": model_name,
                            "turns": turns,
                            "stats": stats
                        })
            except Exception as e:
                pass
                
    print("\n--- MAIN SESSION STATS ---")
    print(f"Model(s):     {', '.join(main_models) if main_models else 'Unknown'}")
    print(f"Effort(s):    {', '.join(main_efforts) if main_efforts else 'Unknown'}")
    print(f"Turns:        {main_turns}")
    print(f"Tokens:       ↑{main_input:,} input | ↓{main_output:,} output | R {main_cache:,} cache read")
    print(f"Est. Cost:    ${main_cost:.4f}")
    
    if subagents:
        print("\n--- SUBAGENT RUNS BREAKDOWN ---")
        sub_cost_total = 0.0
        for s in subagents:
            stats = s["stats"]
            sub_cost_total += stats["cost_total"]
            print(f"Line {s['line']} | {s['agent']} ({s['model']}) [ID: {s['id']}]:")
            print(f"  Turns:      {s['turns']}")
            print(f"  Tokens:     ↑{stats['input']:,} input | ↓{stats['output']:,} output | R {stats['cacheRead']:,} cache read")
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

if __name__ == '__main__':
    main()
