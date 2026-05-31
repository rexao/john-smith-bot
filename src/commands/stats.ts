import {
	SlashCommandBuilder,
	type AutocompleteInteraction,
	type ChatInputCommandInteraction,
	type CommandInteraction,
} from 'discord.js';
import type { Command } from './index.ts';
import { asGuildId } from '../domain/guild.ts';
import { queryTopChatters, queryTopEmojis, queryTotalChatters, queryTotalEmojis, bulkInsert, removeStaleMessages } from '../db/stats.ts';
import { buildChattersEmbed, buildEmotesEmbed, buildPaginationComponents } from '../components/stats.ts';
import { PAGE_SIZE } from '../domain/stats.ts';
import { parsePeriod, getPeriodSuggestions } from '../util/period.ts';
import { scanGuild } from '../util/scan.ts';

async function handlePeriodSubcommand(
	i: ChatInputCommandInteraction,
	type: 'chatters' | 'emotes',
): Promise<void> {
	const guildId = asGuildId(i.guild!.id);
	const periodInput = i.options.getString('period') ?? 'all';

	let since: Date | null;
	try {
		since = parsePeriod(periodInput);
	} catch (err) {
		await i.reply({ content: (err as Error).message, ephemeral: true });
		return;
	}

	const guild = { name: i.guild!.name, iconURL: i.guild!.iconURL() };

	if (type === 'chatters') {
		const total = queryTotalChatters(guildId, since);
		const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
		const rows = queryTopChatters(guildId, since, PAGE_SIZE, 0);
		const embed = buildChattersEmbed(guild, rows, 1, periodInput);
		const components = buildPaginationComponents('chatters', guildId, periodInput, 1, maxPage);
		await i.reply({ embeds: [embed], components: components ? [components] : [] });
	} else {
		const total = queryTotalEmojis(guildId, since);
		const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
		const rows = queryTopEmojis(guildId, since, PAGE_SIZE, 0);
		const embed = buildEmotesEmbed(i.guild!, rows, 1, periodInput);
		const components = buildPaginationComponents('emotes', guildId, periodInput, 1, maxPage);
		await i.reply({ embeds: [embed], components: components ? [components] : [] });
	}
}

export default {
	data: new SlashCommandBuilder()
		.setName('stats')
		.setDescription('Server statistics.')
		.addSubcommand((sub) =>
			sub
				.setName('chatters')
				.setDescription('Top chatters by message count.')
				.addStringOption((opt) =>
					opt
						.setName('period')
						.setDescription('Time period. e.g. 24h, 7d, 2w, 6m, 1y, all')
						.setAutocomplete(true),
				),
		)
		.addSubcommand((sub) =>
			sub
				.setName('emotes')
				.setDescription('Top emotes by usage count.')
				.addStringOption((opt) =>
					opt
						.setName('period')
						.setDescription('Time period. e.g. 24h, 7d, 2w, 6m, 1y, all')
						.setAutocomplete(true),
				),
		)
		.addSubcommand((sub) =>
			sub.setName('scan').setDescription('Scan server history to populate stats.'),
		)
		.toJSON(),

	async autocomplete(interaction: AutocompleteInteraction) {
		const current = interaction.options.getFocused();
		const suggestions = getPeriodSuggestions(current);
		await interaction.respond(suggestions.map((s) => ({ name: s, value: s })));
	},

	async execute(interaction: CommandInteraction) {
		const i = interaction as ChatInputCommandInteraction;
		if (!i.guild) {
			await i.reply({ content: 'This command can only be used in a server.', ephemeral: true });
			return;
		}

		const sub = i.options.getSubcommand();

		if (sub === 'chatters') await handlePeriodSubcommand(i, 'chatters');
		if (sub === 'emotes') await handlePeriodSubcommand(i, 'emotes');

		if (sub === 'scan') {
			await i.deferReply();
			const { events, channelCount, scannedIdsByChannel } = await scanGuild(i.guild);
			const inserted = bulkInsert(events);
			const deleted = removeStaleMessages(scannedIdsByChannel);
			await i.followUp(`Scan complete. ${channelCount} channels scanned, ${events.length} messages found, ${inserted} new messages inserted, ${deleted} stale messages removed.`);
		}
	},
} satisfies Command;
