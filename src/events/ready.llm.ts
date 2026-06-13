import { Events, type Client } from 'discord.js'
import { getSettings, getAllChannels, queryTopChatterMsgCount } from '../db/llm.ts'
import { compilePrompt, chatCompletion, formatReply } from '../util/llm/chat.ts'
import type { Event } from './index.ts'
import { goOnline, goOffline, isOnline } from './messageCreate.llm.ts'

const STATS_DAYS = 7
const MIN_INTERVAL_MS = 30 * 60_000   // 下限: 30分
const MAX_INTERVAL_MS = 12 * 60 * 60_000  // 上限: 12時間

const lastSpontaneousFire = new Map<string, number>()

function calcIntervalMs(
  topCount: number,
  spontaneousRate: number,
  fallbackMinutes: number,
): number {
  if (topCount === 0 || spontaneousRate === 0) {
    return fallbackMinutes * 60_000
  }

  const topIntervalMs = (STATS_DAYS * 24 * 60 * 60_000) / topCount
  const scaled = topIntervalMs * (100 / spontaneousRate)
  return Math.min(MAX_INTERVAL_MS, Math.max(MIN_INTERVAL_MS, scaled))
}

async function fireSpontaneous(client: Client): Promise<void> {
  if (isOnline(client)) return

  const allChannels = getAllChannels()
  if (allChannels.length === 0) return

  const { guildId, channelId } =
    allChannels[Math.floor(Math.random() * allChannels.length)]!
  const settings = getSettings(guildId)

  const guildChannelIds = allChannels
    .filter((ch) => ch.guildId === guildId)
    .map((ch) => ch.channelId)

  const since = new Date(Date.now() - STATS_DAYS * 24 * 60 * 60_000)
  const topCount = queryTopChatterMsgCount(
    guildId,
    guildChannelIds,
    client.user!.id,
    since,
  )

  const intervalMs = calcIntervalMs(
    topCount,
    settings.spontaneousRate,
    settings.spontaneousInterval,
  )

  const lastFire = lastSpontaneousFire.get(guildId) ?? 0
  if (Date.now() - lastFire < intervalMs) return

  const guild = client.guilds.cache.get(guildId)
  if (!guild) return

  const channel = guild.channels.cache.get(channelId)
  if (!channel?.isTextBased()) return

  const durationMs = (Math.floor(Math.random() * 16) + 5) * 60_000
  goOnline(client, durationMs)
  lastSpontaneousFire.set(guildId, Date.now())

  try {
    const messages = await channel.messages.fetch({ limit: 10 })
    if (messages.size === 0) {
      goOffline(client)
      return
    }

    const recentMessages = [...messages.values()].reverse()
    const nonBotMessages = recentMessages.filter((msg) => !msg.author.bot)
    const mentionTarget =
      nonBotMessages.length > 0
        ? nonBotMessages[Math.floor(Math.random() * nonBotMessages.length)]!
            .author
        : null

    const prompt = compilePrompt(
      recentMessages.slice(-settings.contextScope),
      client.user!,
      guild,
    )
    const raw = await chatCompletion(prompt, settings)
    const reply = formatReply(raw, guild)

    if (!reply.trim()) {
      goOffline(client)
      return
    }

    const finalReply = mentionTarget ? `<@${mentionTarget.id}> ${reply}` : reply
    await channel.send(finalReply)
  } catch (error) {
    console.error('Spontaneous LLM error:', error)
    goOffline(client)
  }
}

export default {
  name: Events.ClientReady,
  once: true,
  execute(client) {
    client.user.setPresence({ status: 'invisible' })

    setInterval(() => void fireSpontaneous(client), 60_000)
  },
} satisfies Event<Events.ClientReady>
