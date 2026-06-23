export function calcCostUsd(
  inputTokens: number,
  outputTokens: number,
  costPer1kInput: number,
  costPer1kOutput: number
): number {
  return (inputTokens / 1000) * costPer1kInput + (outputTokens / 1000) * costPer1kOutput
}
