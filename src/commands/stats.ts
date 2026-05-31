import {
	SlashCommandBuilder,
	type AutocompleteInteraction,
	type ChatInputCommandInteraction,
	type CommandInteraction,
} from 'discord.js';
import type { Command } from './index.ts';
import { asGuildId } from '../domain/guild.ts';
import { queryTopChatters, queryTopEmojis, queryTotalChatters, queryTotalEmojis, bulkInsert } from '../db/stats.ts';
import { buildChattersEmbed, buildEmotesEmbed, buildPaginationComponents, PAGE_SIZE } from '../components/stats.ts';
import { parsePeriod, DEFAULT_PERIOD_SUGGESTIONS } from '../util/period.ts';
import { scanGuild } from '../util/scan.ts';

const UNITS = ['h', 'd', 'w', 'm', 'y'];

function getPeriodSuggestions(current: string): string[] {
	if (!current) return DEFAULT_PERIOD_SUGGESTIONS;
	const numMatch = current.match(/^(\d+)$/);
	if (numMatch) return UNITS.map((u) => `${numMatch[1]}${u}`).concat(['all']);
	return DEFAULT_PERIOD_SUGGESTIONS.filter((s) => s.startsWith(current));
}

async function handlePeriodSubcommand(
	i: ChatInputCommandInteraction,
	type: 'chatters' | 'emotes',
): Promise<void> {
	const guildId = asGuildId(i.guild!.id);
	const periodInput = i.options.getString('period') ?? 'all';

	let since: string | null;
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
		const embed = buildEmotesEmbed(guild, rows, 1, periodInput);
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
			const events = await scanGuild(i.guild);
			const inserted = bulkInsert(events);
			await i.followUp(`Scan complete. ${inserted} new messages inserted (${events.length} total scanned).`);
		}
	},
} satisfies Command;
