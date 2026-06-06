import process from 'node:process'
import type { Message, User, Guild } from 'discord.js'
import type { LlmSettings } from '../domain/llm.ts'
import { buildSystemPrompt } from './scenario.ts'

const ollamaBase = (
  process.env.OLLAMA_BASE_URL ?? 'http://localhost:11434'
).replace(/\/api\/?$/, '').replace(/\/v1\/?$/, '')

const MAX_CONTENT_LENGTH = 200
const MAX_REPLY_LENGTH = 2_000
const THINK_TAG_RE = /<think>[\S\s]*?<\/think>/gi

type OllamaMessage = { content: string; role: 'assistant' | 'system' | 'user' }

type OllamaChatResponse = {
  message: { content: string; role: string }
}

export function formatContent(message: Message): string {
  let content = message.content

  for (const [, user] of message.mentions.users) {
    content = content.replaceAll(`<@${user.id}>`, `@${user.displayName}`)
  }

  for (const embed of message.embeds) {
    if (embed.description) content += ` [embed: ${embed.description}]`
  }

  return content.slice(0, MAX_CONTENT_LENGTH)
}

export async function traceThread(message: Message): Promise<Message[]> {
  const chain: Message[] = [message]
  let current = message

  while (current.reference?.messageId) {
    try {
      const parent = await current.channel.messages.fetch(
        current.reference.messageId,
      )
      if (chain.some((msg) => msg.id === parent.id)) break
      chain.unshift(parent)
      current = parent
    } catch {
      break
    }
  }

  return chain
}

export function compilePrompt(
  messages: Message[],
  botUser: User,
  guild: Guild,
): OllamaMessage[] {
  const system: OllamaMessage = {
    role: 'system',
    content: buildSystemPrompt(guild),
  }

  const history: OllamaMessage[] = messages.map((msg) => ({
    role: msg.author.id === botUser.id ? 'assistant' : 'user',
    content: `${msg.author.displayName ?? msg.author.username}: ${formatContent(msg)}`,
  }))

  return [system, ...history]
}

export async function chatCompletion(
  messages: OllamaMessage[],
  settings: LlmSettings,
): Promise<string> {
  const res = await fetch(`${ollamaBase}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: settings.model,
      messages,
      stream: false,
      options: { temperature: settings.temperature / 100 },
    }),
  })

  if (!res.ok) {
    throw new Error(`Ollama API error: ${res.status} ${await res.text()}`)
  }

  const data = (await res.json()) as OllamaChatResponse
  return data.message.content
}

export function formatReply(content: string, guild: Guild): string {
  let result = content.replaceAll(THINK_TAG_RE, '').trim()

  result = result.replace(/^john smith\s*:\s*/i, '').trim()

  for (const member of guild.members.cache.values()) {
    const name = member.displayName
    result = result.replaceAll(`@${name}`, `<@${member.id}>`)
  }

  if (result.length > MAX_REPLY_LENGTH) {
    result = result.slice(0, MAX_REPLY_LENGTH - 3) + '...'
  }

  return result
}

export async function fetchOllamaModels(): Promise<string[]> {
  try {
    const res = await fetch(`${ollamaBase}/api/tags`)
    if (!res.ok) return []
    const data = (await res.json()) as { models?: { name: string }[] }
    return data.models?.map((model) => model.name) ?? []
  } catch {
    return []
  }
}
