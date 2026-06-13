import { type ChannelId, asChannelId } from '../domain/channel.ts'
import { type GuildId, asGuildId } from '../domain/guild.ts'
import { type LlmSettings, DEFAULT_LLM_SETTINGS } from '../domain/llm.ts'
import db from './index.ts'

type LlmSettingsRow = {
  context_scope: number,
  guild_id: string,
  model: string,
  random_rate: number,
  spontaneous_interval: number,
  spontaneous_rate: number
  temperature: number
}

function rowToSettings(row: LlmSettingsRow): LlmSettings {
  return {
    guildId: asGuildId(row.guild_id),
    model: row.model,
    temperature: row.temperature,
    contextScope: row.context_scope,
    randomRate: row.random_rate,
    spontaneousRate: row.spontaneous_rate,
    spontaneousInterval: row.spontaneous_interval,
  }
}

export function getSettings(guildId: GuildId): LlmSettings {
  const row = db
    .prepare(`SELECT * FROM llm_settings WHERE guild_id = ?`)
    .get(guildId) as LlmSettingsRow | undefined
  if (!row) {
    return { guildId, ...DEFAULT_LLM_SETTINGS }
  }

  return rowToSettings(row)
}

export function upsertSettings(settings: LlmSettings): void {
  db.prepare(
    `
		INSERT OR REPLACE INTO llm_settings
			(guild_id, model, temperature, context_scope, random_rate, spontaneous_rate, spontaneous_interval)
		VALUES (?, ?, ?, ?, ?, ?, ?)
	`,
  ).run(
    settings.guildId,
    settings.model,
    settings.temperature,
    settings.contextScope,
    settings.randomRate,
    settings.spontaneousRate,
    settings.spontaneousInterval,
  )
}

export function addChannel(guildId: GuildId, channelId: ChannelId): void {
  db.prepare(
    `INSERT OR IGNORE INTO llm_channels (guild_id, channel_id) VALUES (?, ?)`,
  ).run(guildId, channelId)
}

export function removeChannel(guildId: GuildId, channelId: ChannelId): void {
  db.prepare(
    `DELETE FROM llm_channels WHERE guild_id = ? AND channel_id = ?`,
  ).run(guildId, channelId)
}

export function getChannels(guildId: GuildId): ChannelId[] {
  const rows = db
    .prepare(`SELECT channel_id FROM llm_channels WHERE guild_id = ?`)
    .all(guildId) as { channel_id: string }[]
  return rows.map((row) => asChannelId(row.channel_id))
}

export function getAllChannels(): { channelId: ChannelId; guildId: GuildId }[] {
  const rows = db
    .prepare(`SELECT guild_id, channel_id FROM llm_channels`)
    .all() as { channel_id: string; guild_id: string }[]
  return rows.map((row) => ({
    guildId: asGuildId(row.guild_id),
    channelId: asChannelId(row.channel_id),
  }))
}

export function queryTopChatterMsgCount(
  guildId: GuildId,
  channelIds: ChannelId[],
  excludeUserId: string,
  since: Date,
): number {
  if (channelIds.length === 0) return 0
  const placeholders = channelIds.map(() => '?').join(',')
  const row = db
    .prepare(
      `SELECT COUNT(*) as msg_count
       FROM message_events
       WHERE guild_id = ?
         AND channel_id IN (${placeholders})
         AND sent_at >= ?
         AND user_id != ?
       GROUP BY user_id
       ORDER BY msg_count DESC
       LIMIT 1`,
    )
    .get(guildId, ...channelIds, since.toISOString(), excludeUserId) as
    | { msg_count: number }
    | undefined
  return row?.msg_count ?? 0
}
