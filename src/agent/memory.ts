export type MemoryEntry = { role: 'user' | 'assistant'; content: string }

const store = new Map<string, MemoryEntry[]>()

export function getMemory(sessionId: string): MemoryEntry[] {
  return store.get(sessionId) ?? []
}

export function appendMemory(sessionId: string, entry: MemoryEntry): void {
  const existing = store.get(sessionId) ?? []
  store.set(sessionId, [...existing, entry])
}

export function clearMemory(sessionId: string): void {
  store.delete(sessionId)
}
