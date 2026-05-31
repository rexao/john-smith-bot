import type { ButtonInteraction } from 'discord.js';
import {
	buildServerComponents,
	buildServerEmbeds,
	buildUserComponents,
	buildUserEmbeds,
	type ServerPage,
	type UserPage,
} from '../../components/inspect.ts';

export async function handleInspectButton(interaction: ButtonInteraction): Promise<void> {
	// customId format:
	//   inspect:server:<page>
	//   inspect:user:<userId>:<page>
	const [, target, ...rest] = interaction.customId.split(':');

	if (target === 'server') {
		if (!interaction.guild) return;
		const [page] = rest as [ServerPage];
		const embed = buildServerEmbeds(interaction.guild)[page];
		const components = buildServerComponents(page);
		await interaction.update({ embeds: [embed], components: [components] });
	}

	if (target === 'user') {
		if (!interaction.guild) return;
		const [userId, page] = rest as [string, UserPage];
		const member = await interaction.guild.members.fetch(userId);
		const embed = (await buildUserEmbeds(member, interaction.client))[page];
		const components = buildUserComponents(userId, page, true);
		await interaction.update({ embeds: [embed], components: [components] });
	}
}
