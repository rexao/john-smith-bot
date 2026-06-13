import type { Guild } from 'discord.js'
import { asChannelId, type ChannelId } from '../../domain/channel.ts'
import { Emoji, EMOJI_REGEX } from '../../domain/emoji.ts'
import { asGuildId } from '../../domain/guild.ts'
import { asMessageId, type MessageId } from '../../domain/message.ts'
import type { ScanEvent } from '../../domain/stats.ts'
import { asUserId } from '../../domain/user.ts'

export async function scanGuild(guild: Guild): Promise<{
  channelCount: number,
  events: ScanEvent[],
  scannedIdsByChannel: Map<ChannelId, Set<MessageId>>
}> {
  const guildId = asGuildId(guild.id)
  const events: ScanEvent[] = []
  const scannedIdsByChannel = new Map<ChannelId, Set<MessageId>>()

  const allChannels = await guild.channels.fetch()
  let channelCount = 0

  for (const channel of allChannels.values()) {
    if (!channel?.isTextBased()) continue
    try {
      const channelId = asChannelId(channel.id)
      const scannedIds = new Set<MessageId>()
      let before: string | undefined
      while (true) {
        const messages = await channel.messages.fetch({ limit: 100, before })
        if (messages.size === 0) break
        for (const message of messages.values()) {
          const messageId = asMessageId(message.id)
          scannedIds.add(messageId)
          events.push({
            messageId,
            guildId,
            channelId,
            userId: asUserId(message.author.id),
            sentAt: message.createdAt.toISOString(),
            emojis: [...message.content.matchAll(EMOJI_REGEX)].map(
              ([, animatedFlag, name, id]) =>
                Emoji.fromRegexMatch(animatedFlag, name, id),
            ),
          })
        }

        before = messages.last()?.id
      }

      scannedIdsByChannel.set(channelId, scannedIds)
      channelCount++
    } catch {
      // チャンネルにアクセス権がない場合はスキップ
    }
  }

  return { events, channelCount, scannedIdsByChannel }
}
