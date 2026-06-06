import type { GuildId } from './guild.ts'

export type LlmSettings = {
  contextScope: number
  guildId: GuildId
  model: string
  randomRate: number
  spontaneousInterval: number
  spontaneousRate: number
  temperature: number
}

export const DEFAULT_LLM_SETTINGS: Omit<LlmSettings, 'guildId'> = {
  model: 'llama3.2:latest',
  temperature: 100,
  contextScope: 12,
  randomRate: 10,
  spontaneousRate: 20,
  spontaneousInterval: 30,
}
