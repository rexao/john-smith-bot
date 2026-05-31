import { Events, type Message } from 'discord.js';
import type { Event } from './index.ts';
import { asGuildId } from '../domain/guild.ts';
import { asUserId } from '../domain/user.ts';
import { asChannelId } from '../domain/channel.ts';
import { asMessageId } from '../domain/message.ts';
import { insertMessageEvent, insertEmojiEvent } from '../db/stats.ts';
import { Emoji, EMOJI_REGEX } from '../domain/emoji.ts';

export default {
	name: Events.MessageCreate,
	execute(message: Message) {
		if (!message.guild) return;

		const messageId = asMessageId(message.id);
		const guildId   = asGuildId(message.guild.id);
		const channelId = asChannelId(message.channel.id);
		const userId    = asUserId(message.author.id);

		const sentAt = message.createdAt.toISOString();
		insertMessageEvent(messageId, guildId, channelId, userId, sentAt);

		for (const [, animatedFlag, name, id] of message.content.matchAll(EMOJI_REGEX)) {
			const emoji = Emoji.fromRegexMatch(animatedFlag, name, id);
			insertEmojiEvent(messageId, guildId, channelId, emoji.id, emoji.name, emoji.animated, userId, sentAt);
		}
	},
} satisfies Event<Events.MessageCreate>;
