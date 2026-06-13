import {
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  EmbedBuilder,
  type Guild,
  type GuildEmoji,
} from 'discord.js'
import { type GuildId } from '../domain/guild.ts'
import {
  type ChatterRow,
  type EmojiRow,
  rowToEmoji,
  PAGE_SIZE,
} from '../domain/stats.ts'
import { periodLabel } from '../util/stats/period.ts'

type GuildInfo = { iconURL: string | null, name: string; }

const COLOR = 0xed4245

export function buildChattersEmbed(
  guild: GuildInfo,
  rows: ChatterRow[],
  page: number,
  period: string,
): EmbedBuilder {
  const description =
    rows.length === 0
      ? 'No data yet.'
      : rows
          .map(
            (row, i) =>
              `\`${(page - 1) * PAGE_SIZE + i + 1}\`　-　<@${row.user_id}>　-　**${row.message_count}**`,
          )
          .join('\n')

  return new EmbedBuilder()
    .setColor(COLOR)
    .setTitle(`Top Chatters — \`${periodLabel(period)}\``)
    .setDescription(description)
    .setAuthor({ name: guild.name, iconURL: guild.iconURL ?? undefined })
    .setTimestamp()
}

export function buildEmotesEmbed(
  guild: Guild,
  rows: EmojiRow[],
  page: number,
  period: string,
): EmbedBuilder {
  const description =
    rows.length === 0
      ? 'No data yet.'
      : rows
          .map((row, i) => {
            let guildEmoji: GuildEmoji | undefined
            for (const g of guild.client.guilds.cache.values()) {
              guildEmoji = g.emojis.cache.find((e) => e.name === row.emoji_name)
              if (guildEmoji) break
            }

            const display = guildEmoji
              ? guildEmoji.toString()
              : rowToEmoji(row).format()
            return `\`${(page - 1) * PAGE_SIZE + i + 1}\`　-　${display} ${row.emoji_name}　-　**${row.usage_count}**`
          })
          .join('\n')

  return new EmbedBuilder()
    .setColor(COLOR)
    .setTitle(`Top Emotes — \`${periodLabel(period)}\``)
    .setDescription(description)
    .setAuthor({ name: guild.name, iconURL: guild.iconURL() ?? undefined })
    .setTimestamp()
}

export function buildPaginationComponents(
  type: 'chatters' | 'emotes',
  guildId: GuildId,
  period: string,
  page: number,
  maxPage: number,
): ActionRowBuilder<ButtonBuilder> | null {
  if (maxPage <= 1) return null
  return new ActionRowBuilder<ButtonBuilder>().addComponents(
    new ButtonBuilder()
      .setCustomId(`stats:${type}:${guildId}:${period}:${page - 1}`)
      .setLabel('< Previous')
      .setStyle(ButtonStyle.Primary)
      .setDisabled(page <= 1),
    new ButtonBuilder()
      .setCustomId(`stats:${type}:${guildId}:${period}:${page + 1}`)
      .setLabel('Next >')
      .setStyle(ButtonStyle.Primary)
      .setDisabled(page >= maxPage),
  )
}
