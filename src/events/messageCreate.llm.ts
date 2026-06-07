import { Events, type Client, type Message, type TextChannel } from 'discord.js'
import { getSettings, getChannels } from '../db/llm.ts'
import { type ChannelId, asChannelId } from '../domain/channel.ts'
import { asGuildId } from '../domain/guild.ts'
import {
  traceThread,
  compilePrompt,
  chatCompletion,
  formatReply,
} from '../util/llm/chat.ts'
import type { Event } from './index.ts'

type OnlineState = { online: boolean; until: number }
type DebounceState = { resetCount: number, timer: NodeJS.Timeout; }

let onlineState: OnlineState = { online: false, until: 0 }
const channelActivity = new Map<ChannelId, number[]>()
const debounceMap = new Map<ChannelId, DebounceState>()

export function goOnline(client: Client, durationMs: number): void {
  onlineState = { online: true, until: Date.now() + durationMs }
  client.user?.setPresence({ status: 'online' })
}

export function goOffline(client: Client): void {
  onlineState = { online: false, until: 0 }
  client.user?.setPresence({ status: 'invisible' })
}

export function isOnline(client: Client): boolean {
  if (!onlineState.online) return false
  if (Date.now() > onlineState.until) {
    goOffline(client)
    return false
  }

  return true
}

function getHeat(channelId: ChannelId): number {
  const now = Date.now()
  const cutoff = now - 30_000
  const timestamps = (channelActivity.get(channelId) ?? []).filter(
    (ts) => ts > cutoff,
  )
  channelActivity.set(channelId, timestamps)
  return timestamps.length
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function onlineChance(heat: number): number {
  return clamp(heat * 0.15, 0.05, 0.95)
}

function roll(chance: number): boolean {
  return Math.random() < chance
}

async function sendReply(message: Message, client: Client): Promise<void> {
  if (!message.guild) return
  const guildId = asGuildId(message.guild.id)
  const settings = getSettings(guildId)

  try {
    const channel = message.channel as TextChannel
    await channel.sendTyping()

    const context = await traceThread(message)
    const recent = context.slice(-settings.contextScope)
    const prompt = compilePrompt(recent, client.user!, message.guild)
    const raw = await chatCompletion(prompt, settings)
    const reply = formatReply(raw, message.guild)

    if (reply) await message.reply(reply)
  } catch (error) {
    console.error('LLM reply error:', error)
  }
}

async function fireDebounce(
  channelId: ChannelId,
  message: Message,
  client: Client,
): Promise<void> {
  const state = debounceMap.get(channelId)
  if (!state) return
  clearTimeout(state.timer)
  debounceMap.delete(channelId)
  await sendReply(message, client)
}

function scheduleDebounce(
  channelId: ChannelId,
  message: Message,
  client: Client,
): void {
  const existing = debounceMap.get(channelId)

  if (!existing) {
    const timer = setTimeout(
      () => void fireDebounce(channelId, message, client),
      10_000,
    )
    debounceMap.set(channelId, { timer, resetCount: 0 })
    return
  }

  if (existing.resetCount >= 5) {
    void fireDebounce(channelId, message, client)
    const timer = setTimeout(
      () => void fireDebounce(channelId, message, client),
      10_000,
    )
    debounceMap.set(channelId, { timer, resetCount: 0 })
    return
  }

  clearTimeout(existing.timer)
  const timer = setTimeout(
    () => void fireDebounce(channelId, message, client),
    10_000,
  )
  debounceMap.set(channelId, { timer, resetCount: existing.resetCount + 1 })
}

function isMentionOrReply(message: Message, client: Client): boolean {
  if (message.mentions.has(client.user!)) return true
  if (message.reference?.messageId) {
    const referenced = message.channel.messages.cache.get(
      message.reference.messageId,
    )
    if (referenced?.author.id === client.user!.id) return true
  }

  return false
}

export default {
  name: Events.MessageCreate,
  async execute(message: Message) {
    if (message.author.bot) return
    if (!message.guild) return

    const client = message.client
    const guildId = asGuildId(message.guild.id)
    const channelId = asChannelId(message.channel.id)

    if (isMentionOrReply(message, client)) {
      await sendReply(message, client)
      return
    }

    const allowedChannels = getChannels(guildId)
    if (!allowedChannels.includes(channelId)) return

    const now = Date.now()
    const timestamps = channelActivity.get(channelId) ?? []
    timestamps.push(now)
    channelActivity.set(channelId, timestamps)

    const heat = getHeat(channelId)

    if (!isOnline(client)) {
      if (!roll(onlineChance(heat))) return
      const durationMs = (Math.floor(Math.random() * 51) + 10) * 60_000
      goOnline(client, durationMs)
    }

    const settings = getSettings(guildId)
    if (!roll(settings.randomRate / 100)) return

    scheduleDebounce(channelId, message, client)
  },
} satisfies Event<Events.MessageCreate>
