import { type ChannelId } from './channel.ts'
import { Emoji } from './emoji.ts'
import { type GuildId } from './guild.ts'
import { type MessageId } from './message.ts'
import { type UserId } from './user.ts'

export type ChatterRow = { message_count: number, user_id: UserId; }
export type EmojiRow = {
  animated: number,
  emoji_id: string,
  emoji_name: string,
  usage_count: number
}

export const PAGE_SIZE = 10

export function rowToEmoji(row: EmojiRow): Emoji {
  return new Emoji(row.emoji_id, row.emoji_name, row.animated === 1)
}

export type MessageEventRow = {
  channelId: ChannelId,
  guildId: GuildId
  messageId: MessageId,
  sentAt: string,
  userId: UserId
}

export type ScanEvent = MessageEventRow & { emojis: Emoji[] }
