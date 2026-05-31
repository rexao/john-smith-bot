import type { ButtonInteraction } from 'discord.js';
import { asGuildId } from '../../domain/guild.ts';
import { queryTopChatters, queryTopEmojis, queryTotalChatters, queryTotalEmojis } from '../../db/stats.ts';
import { buildChattersEmbed, buildEmotesEmbed, buildPaginationComponents, PAGE_SIZE } from '../../components/stats.ts';
import { parsePeriod } from '../../util/period.ts';

export async function handleStatsButton(interaction: ButtonInteraction): Promise<void> {
	// customId format: stats:<type>:<guildId>:<period>:<page>
	const [, type, rawGuildId, periodInput, rawPage] = interaction.customId.split(':');
	const guildId = asGuildId(rawGuildId);
	const since = parsePeriod(periodInput);
	const page = parseInt(rawPage, 10);
	const offset = (page - 1) * PAGE_SIZE;
	const guild = { name: interaction.guild!.name, iconURL: interaction.guild!.iconURL() };

	if (type === 'chatters') {
		const total = queryTotalChatters(guildId, since);
		const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
		const rows = queryTopChatters(guildId, since, PAGE_SIZE, offset);
		const embed = buildChattersEmbed(guild, rows, page, periodInput);
		const components = buildPaginationComponents('chatters', guildId, periodInput, page, maxPage);
		await interaction.update({ embeds: [embed], components: components ? [components] : [] });
	}

	if (type === 'emotes') {
		const total = queryTotalEmojis(guildId, since);
		const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
		const rows = queryTopEmojis(guildId, since, PAGE_SIZE, offset);
		const embed = buildEmotesEmbed(guild, rows, page, periodInput);
		const components = buildPaginationComponents('emotes', guildId, periodInput, page, maxPage);
		await interaction.update({ embeds: [embed], components: components ? [components] : [] });
	}
}
