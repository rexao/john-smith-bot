import {
  SlashCommandBuilder,
  EmbedBuilder,
  MessageFlags,
  type AutocompleteInteraction,
  type ChatInputCommandInteraction,
  type CommandInteraction,
} from 'discord.js'
import {
  getSettings,
  upsertSettings,
  addChannel,
  removeChannel,
  getChannels,
} from '../db/llm.ts'
import { asChannelId } from '../domain/channel.ts'
import { asGuildId } from '../domain/guild.ts'
import { fetchOllamaModels } from '../util/llm/chat.ts'
import type { Command } from './index.ts'

async function handleSettings(
  intr: ChatInputCommandInteraction,
): Promise<void> {
  const guildId = asGuildId(intr.guild!.id)
  const current = getSettings(guildId)

  const model = intr.options.getString('model')
  const temperature = intr.options.getInteger('temperature')
  const contextScope = intr.options.getInteger('context_scope')
  const randomRate = intr.options.getInteger('random_rate')
  const spontaneousRate = intr.options.getInteger('spontaneous_rate')
  const spontaneousInterval = intr.options.getInteger('spontaneous_interval')

  const hasChanges =
    model !== null ||
    temperature !== null ||
    contextScope !== null ||
    randomRate !== null ||
    spontaneousRate !== null ||
    spontaneousInterval !== null

  if (hasChanges) {
    upsertSettings({
      guildId,
      model: model ?? current.model,
      temperature: temperature ?? current.temperature,
      contextScope: contextScope ?? current.contextScope,
      randomRate: randomRate ?? current.randomRate,
      spontaneousRate: spontaneousRate ?? current.spontaneousRate,
      spontaneousInterval: spontaneousInterval ?? current.spontaneousInterval,
    })
    await intr.reply({ content: 'Settings updated.', flags: MessageFlags.Ephemeral })
    return
  }

  const settings = getSettings(guildId)
  const embed = new EmbedBuilder()
    .setTitle('LLM Settings')
    .setColor(0x5865f2)
    .addFields(
      { name: 'Model', value: settings.model, inline: true },
      {
        name: 'Temperature',
        value: String(settings.temperature / 100),
        inline: true,
      },
      {
        name: 'Context Scope',
        value: String(settings.contextScope),
        inline: true,
      },
      { name: 'Random Rate', value: `${settings.randomRate}%`, inline: true },
      {
        name: 'Spontaneous Rate',
        value: `${settings.spontaneousRate}%`,
        inline: true,
      },
      {
        name: 'Spontaneous Interval',
        value: `${settings.spontaneousInterval} min`,
        inline: true,
      },
    )

  await intr.reply({ embeds: [embed], flags: MessageFlags.Ephemeral })
}

async function handleChannelAdd(
  intr: ChatInputCommandInteraction,
): Promise<void> {
  const guildId = asGuildId(intr.guild!.id)
  const channel = intr.options.getChannel('channel', true)
  const channelId = asChannelId(channel.id)
  addChannel(guildId, channelId)
  await intr.reply({
    content: `Added <#${channel.id}> to LLM channels.`,
    flags: MessageFlags.Ephemeral,
  })
}

async function handleChannelRemove(
  intr: ChatInputCommandInteraction,
): Promise<void> {
  const guildId = asGuildId(intr.guild!.id)
  const channel = intr.options.getChannel('channel', true)
  const channelId = asChannelId(channel.id)
  removeChannel(guildId, channelId)
  await intr.reply({
    content: `Removed <#${channel.id}> from LLM channels.`,
    flags: MessageFlags.Ephemeral,
  })
}

async function handleChannelList(
  intr: ChatInputCommandInteraction,
): Promise<void> {
  const guildId = asGuildId(intr.guild!.id)
  const channels = getChannels(guildId)
  if (channels.length === 0) {
    await intr.reply({
      content: 'No LLM channels configured.',
      flags: MessageFlags.Ephemeral,
    })
    return
  }

  const list = channels.map((id) => `<#${id}>`).join('\n')
  await intr.reply({
    content: `**LLM Channels:**\n${list}`,
    flags: MessageFlags.Ephemeral,
  })
}

export default {
  data: new SlashCommandBuilder()
    .setName('llm')
    .setDescription('Manage John Smith LLM settings.')
    .addSubcommand((sub) =>
      sub
        .setName('settings')
        .setDescription('View or update LLM settings.')
        .addStringOption((opt) =>
          opt
            .setName('model')
            .setDescription('Ollama model name')
            .setAutocomplete(true),
        )
        .addIntegerOption((opt) =>
          opt
            .setName('temperature')
            .setDescription('Temperature ×100 (0-200)')
            .setMinValue(0)
            .setMaxValue(200),
        )
        .addIntegerOption((opt) =>
          opt
            .setName('context_scope')
            .setDescription('Number of recent messages for context')
            .setMinValue(1)
            .setMaxValue(50),
        )
        .addIntegerOption((opt) =>
          opt
            .setName('random_rate')
            .setDescription('Random reply rate (0-100%)')
            .setMinValue(0)
            .setMaxValue(100),
        )
        .addIntegerOption((opt) =>
          opt
            .setName('spontaneous_rate')
            .setDescription('Spontaneous message rate (0-100%)')
            .setMinValue(0)
            .setMaxValue(100),
        )
        .addIntegerOption((opt) =>
          opt
            .setName('spontaneous_interval')
            .setDescription('Spontaneous interval in minutes')
            .setMinValue(1)
            .setMaxValue(1_440),
        ),
    )
    .addSubcommandGroup((group) =>
      group
        .setName('channel')
        .setDescription('Manage LLM channel whitelist.')
        .addSubcommand((sub) =>
          sub
            .setName('add')
            .setDescription('Add a channel to the LLM whitelist.')
            .addChannelOption((opt) =>
              opt
                .setName('channel')
                .setDescription('Channel to add')
                .setRequired(true),
            ),
        )
        .addSubcommand((sub) =>
          sub
            .setName('remove')
            .setDescription('Remove a channel from the LLM whitelist.')
            .addChannelOption((opt) =>
              opt
                .setName('channel')
                .setDescription('Channel to remove')
                .setRequired(true),
            ),
        )
        .addSubcommand((sub) =>
          sub.setName('list').setDescription('List all LLM channels.'),
        ),
    )
    .toJSON(),

  async autocomplete(interaction: AutocompleteInteraction) {
    const focused = interaction.options.getFocused(true)
    if (focused.name !== 'model') {
      await interaction.respond([])
      return
    }

    const models = await fetchOllamaModels()
    const filtered = models.filter((model) =>
      model.toLowerCase().includes(focused.value.toLowerCase()),
    )
    await interaction.respond(
      filtered.slice(0, 25).map((model) => ({ name: model, value: model })),
    )
  },

  async execute(interaction: CommandInteraction) {
    const intr = interaction as ChatInputCommandInteraction
    if (!intr.guild) {
      await intr.reply({
        content: 'This command can only be used in a server.',
        flags: MessageFlags.Ephemeral,
      })
      return
    }

    const sub = intr.options.getSubcommand(false)
    const group = intr.options.getSubcommandGroup(false)

    if (!group && sub === 'settings') {
      await handleSettings(intr)
      return
    }

    if (group === 'channel') {
      if (sub === 'add') await handleChannelAdd(intr)
      if (sub === 'remove') await handleChannelRemove(intr)
      if (sub === 'list') await handleChannelList(intr)
    }
  },
} satisfies Command
