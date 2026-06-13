import { type ChannelId } from '../domain/channel.ts'
import { type GuildId } from '../domain/guild.ts'
import { type MessageId } from '../domain/message.ts'
import {
  type ChatterRow,
  type EmojiRow,
  type ScanEvent,
} from '../domain/stats.ts'
import { type UserId } from '../domain/user.ts'
import db from './index.ts'

export function insertMessageEvent(
  messageId: MessageId,
  guildId: GuildId,
  channelId: ChannelId,
  userId: UserId,
  sentAt: string,
): void {
  db.prepare(
    `
		INSERT OR IGNORE INTO message_events (message_id, guild_id, channel_id, user_id, sent_at)
		VALUES (?, ?, ?, ?, ?)
	`,
  ).run(messageId, guildId, channelId, userId, sentAt)
}

export function insertEmojiEvent(
  messageId: MessageId,
  guildId: GuildId,
  channelId: ChannelId,
  emojiId: string,
  emojiName: string,
  animated: boolean,
  userId: UserId,
  sentAt: string,
): void {
  db.prepare(
    `
		INSERT INTO emoji_events (message_id, guild_id, channel_id, emoji_id, emoji_name, animated, user_id, used_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`,
  ).run(
    messageId,
    guildId,
    channelId,
    emojiId,
    emojiName,
    animated ? 1 : 0,
    userId,
    sentAt,
  )
}

export function queryTopChatters(
  guildId: GuildId,
  since: Date | null,
  limit: number,
  offset: number,
): ChatterRow[] {
  const sinceStr = since?.toISOString() ?? null
  const params = sinceStr
    ? [guildId, sinceStr, limit, offset]
    : [guildId, limit, offset]
  return db
    .prepare(
      `
		SELECT user_id, COUNT(*) as message_count
		FROM message_events
		WHERE guild_id = ?${sinceStr ? ' AND sent_at >= ?' : ''}
		GROUP BY user_id
		ORDER BY message_count DESC
		LIMIT ? OFFSET ?
	`,
    )
    .all(...params) as ChatterRow[]
}

export function queryTopEmojis(
  guildId: GuildId,
  since: Date | null,
  limit: number,
  offset: number,
): EmojiRow[] {
  const sinceStr = since?.toISOString() ?? null
  const params = sinceStr
    ? [guildId, sinceStr, limit, offset]
    : [guildId, limit, offset]
  return db
    .prepare(
      `
		SELECT emoji_id, emoji_name, animated, COUNT(*) as usage_count
		FROM emoji_events
		WHERE guild_id = ?${sinceStr ? ' AND used_at >= ?' : ''}
		GROUP BY emoji_id
		ORDER BY usage_count DESC
		LIMIT ? OFFSET ?
	`,
    )
    .all(...params) as EmojiRow[]
}

export function queryTotalChatters(
  guildId: GuildId,
  since: Date | null,
): number {
  const sinceStr = since?.toISOString() ?? null
  const params = sinceStr ? [guildId, sinceStr] : [guildId]
  const row = db
    .prepare(
      `
		SELECT COUNT(DISTINCT user_id) as total
		FROM message_events
		WHERE guild_id = ?${sinceStr ? ' AND sent_at >= ?' : ''}
	`,
    )
    .get(...params) as { total: number }
  return row.total
}

export function queryTotalEmojis(guildId: GuildId, since: Date | null): number {
  const sinceStr = since?.toISOString() ?? null
  const params = sinceStr ? [guildId, sinceStr] : [guildId]
  const row = db
    .prepare(
      `
		SELECT COUNT(DISTINCT emoji_name) as total
		FROM emoji_events
		WHERE guild_id = ?${sinceStr ? ' AND used_at >= ?' : ''}
	`,
    )
    .get(...params) as { total: number }
  return row.total
}

export function removeStaleMessages(
  scannedIdsByChannel: Map<ChannelId, Set<MessageId>>,
): number {
  let deleted = 0
  db.transaction(() => {
    for (const [channelId, scannedIds] of scannedIdsByChannel) {
      const dbRows = db
        .prepare(`SELECT message_id FROM message_events WHERE channel_id = ?`)
        .all(channelId) as { message_id: MessageId }[]
      const staleIds = dbRows
        .map((r) => r.message_id)
        .filter((id) => !scannedIds.has(id))
      if (staleIds.length === 0) continue
      const placeholders = staleIds.map(() => '?').join(',')
      db.prepare(
        `DELETE FROM emoji_events WHERE message_id IN (${placeholders})`,
      ).run(...staleIds)
      const result = db
        .prepare(
          `DELETE FROM message_events WHERE message_id IN (${placeholders})`,
        )
        .run(...staleIds)
      deleted += result.changes
    }
  })()
  return deleted
}

export function bulkInsert(events: ScanEvent[]): number {
  const insertMessage = db.prepare(`
		INSERT OR IGNORE INTO message_events (message_id, guild_id, channel_id, user_id, sent_at)
		VALUES (?, ?, ?, ?, ?)
	`)
  const insertEmoji = db.prepare(`
		INSERT INTO emoji_events (message_id, guild_id, channel_id, emoji_id, emoji_name, animated, user_id, used_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`)

  let inserted = 0

  db.transaction(() => {
    for (const event of events) {
      const result = insertMessage.run(
        event.messageId,
        event.guildId,
        event.channelId,
        event.userId,
        event.sentAt,
      )
      if (result.changes === 0) continue // 既存メッセージはスキップ
      inserted++
      for (const emoji of event.emojis) {
        insertEmoji.run(
          event.messageId,
          event.guildId,
          event.channelId,
          emoji.id,
          emoji.name,
          emoji.animated ? 1 : 0,
          event.userId,
          event.sentAt,
        )
      }
    }
  })()

  return inserted
}
