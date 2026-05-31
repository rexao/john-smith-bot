import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { Events } from 'discord.js';
import { loadCommands } from '../util/loaders.ts';
import type { Event } from './index.ts';
import { handleInspectButton } from './buttons/inspect.ts';

const commands = await loadCommands(pathToFileURL(join(import.meta.dirname, '../commands')));

export default {
	name: Events.InteractionCreate,
	async execute(interaction) {
		if (interaction.isCommand()) {
			const command = commands.get(interaction.commandName);
			if (!command) throw new Error(`Command '${interaction.commandName}' not found.`);
			await command.execute(interaction);
		}

		if (interaction.isButton()) {
			if (interaction.customId.startsWith('inspect:')) await handleInspectButton(interaction);
		}
	},
} satisfies Event<Events.InteractionCreate>;
