def calc_cost_usd(
    input_tokens: int,
    output_tokens: int,
    cost_per_1k_input: float,
    cost_per_1k_output: float,
) -> float:
    return (input_tokens / 1000) * cost_per_1k_input + (output_tokens / 1000) * cost_per_1k_output
