import {
	ActionRowBuilder,
	ButtonBuilder,
	ButtonStyle,
	EmbedBuilder,
} from 'discord.js';
import { type GuildId } from '../domain/guild.ts';
import { type ChatterRow, type EmojiRow, rowToEmoji } from '../db/stats.ts';

type GuildInfo = { name: string; iconURL: string | null };

const COLOR = 0xed4245;

function periodLabel(period: string): string {
	if (period === 'all') return 'All Time';
	const match = period.match(/^(\d+)(h|d|w|m|y)$/);
	if (!match) return period;
	const [, num, unit] = match;
	const unitLabel: Record<string, string> = { h: 'Hour', d: 'Day', w: 'Week', m: 'Month', y: 'Year' };
	const n = parseInt(num, 10);
	return `Last ${n} ${unitLabel[unit]}${n > 1 ? 's' : ''}`;
}

export const PAGE_SIZE = 10;

export function buildChattersEmbed(
	guild: GuildInfo,
	rows: ChatterRow[],
	page: number,
	period: string,
): EmbedBuilder {
	const description = rows.length === 0
		? 'No data yet.'
		: rows.map((row, i) =>
			`\`${(page - 1) * PAGE_SIZE + i + 1}\` <@${row.user_id}> — **${row.message_count}**`,
		).join('\n');

	return new EmbedBuilder()
		.setColor(COLOR)
		.setTitle(`Top Chatters — \`${periodLabel(period)}\``)
		.setDescription(description)
		.setAuthor({ name: guild.name, iconURL: guild.iconURL ?? undefined })
		.setTimestamp();
}

export function buildEmotesEmbed(
	guild: GuildInfo,
	rows: EmojiRow[],
	page: number,
	period: string,
): EmbedBuilder {
	const description = rows.length === 0
		? 'No data yet.'
		: rows.map((row, i) => {
			const emoji = rowToEmoji(row);
			return `\`${(page - 1) * PAGE_SIZE + i + 1}\` ${emoji.format()} — **${row.usage_count}**`;
		}).join('\n');

	return new EmbedBuilder()
		.setColor(COLOR)
		.setTitle(`Top Emotes — \`${periodLabel(period)}\``)
		.setDescription(description)
		.setAuthor({ name: guild.name, iconURL: guild.iconURL ?? undefined })
		.setTimestamp();
}

export function buildPaginationComponents(
	type: 'chatters' | 'emotes',
	guildId: GuildId,
	period: string,
	page: number,
	maxPage: number,
): ActionRowBuilder<ButtonBuilder> | null {
	if (maxPage <= 1) return null;
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
	);
}
