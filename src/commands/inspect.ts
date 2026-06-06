import {
  SlashCommandBuilder,
  type ChatInputCommandInteraction,
  type CommandInteraction,
  type GuildMember,
} from 'discord.js'
import {
  buildServerComponents,
  buildServerEmbeds,
  buildUserComponents,
  buildUserEmbeds,
} from '../components/inspect.ts'
import { asUserId } from '../domain/user.ts'
import type { Command } from './index.ts'

export default {
  data: new SlashCommandBuilder()
    .setName('inspect')
    .setDescription('Access top secret information.')
    .addSubcommand((sub) =>
      sub.setName('server').setDescription('Get server info.'),
    )
    .addSubcommand((sub) =>
      sub
        .setName('user')
        .setDescription('Get user info.')
        .addUserOption((opt) =>
          opt.setName('user').setDescription('Specify a user.'),
        ),
    )
    .toJSON(),

  async execute(interaction: CommandInteraction) {
    const i = interaction as ChatInputCommandInteraction
    const sub = i.options.getSubcommand()

    if (sub === 'server') {
      if (!i.guild) {
        await i.reply({
          content: 'Hey bro this is not a server.',
          ephemeral: true,
        })
        return
      }

      const embeds = buildServerEmbeds(i.guild)
      await i.reply({
        embeds: [embeds.main],
        components: [buildServerComponents('main')],
      })
    }

    if (sub === 'user') {
      const member = (i.options.getMember('user') ??
        i.member) as GuildMember | null

      if (!member) {
        await i.reply({
          content: 'Please use this command in a server.',
          ephemeral: true,
        })
        return
      }

      const embeds = await buildUserEmbeds(member, i.client)
      await i.reply({
        embeds: [embeds.main],
        components: [
          buildUserComponents(asUserId(member.id), 'main', Boolean(i.guild)),
        ],
      })
    }
  },
} satisfies Command
