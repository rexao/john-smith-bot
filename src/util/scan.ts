import type { Guild } from 'discord.js';
import { asGuildId } from '../domain/guild.ts';
import { asUserId } from '../domain/user.ts';
import { asChannelId } from '../domain/channel.ts';
import { asMessageId } from '../domain/message.ts';
import { Emoji, EMOJI_REGEX } from '../domain/emoji.ts';
import type { ScanEvent } from '../db/stats.ts';

export async function scanGuild(guild: Guild): Promise<{ events: ScanEvent[]; channelCount: number }> {
	const guildId = asGuildId(guild.id);
	const events: ScanEvent[] = [];

	const allChannels = await guild.channels.fetch();
	let channelCount = 0;

	for (const channel of allChannels.values()) {
		if (!channel || !channel.isTextBased()) continue;
		try {
			let before: string | undefined;
			while (true) {
				const messages = await channel.messages.fetch({ limit: 100, before });
				if (messages.size === 0) break;
				for (const message of messages.values()) {
					events.push({
						messageId: asMessageId(message.id),
						guildId,
						channelId: asChannelId(message.channel.id),
						userId: asUserId(message.author.id),
						sentAt: message.createdAt.toISOString(),
						emojis: [...message.content.matchAll(EMOJI_REGEX)].map(
							([, animatedFlag, name, id]) => Emoji.fromRegexMatch(animatedFlag, name, id),
						),
					});
				}
				before = messages.last()?.id;
			}
			channelCount++;
		} catch {
			// チャンネルにアクセス権がない場合はスキップ
		}
	}

	return { events, channelCount };
}
