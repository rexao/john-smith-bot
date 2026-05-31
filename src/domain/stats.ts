import { type GuildId } from './guild.ts';
import { type UserId } from './user.ts';
import { type ChannelId } from './channel.ts';
import { type MessageId } from './message.ts';
import { Emoji } from './emoji.ts';

export type ChatterRow = { user_id: UserId; message_count: number };
export type EmojiRow = { emoji_id: string; emoji_name: string; animated: number; usage_count: number };

export const PAGE_SIZE = 10;

export function rowToEmoji(row: EmojiRow): Emoji {
	return new Emoji(row.emoji_id, row.emoji_name, row.animated === 1);
}

export type MessageEventRow = {
	messageId: MessageId;
	guildId: GuildId;
	channelId: ChannelId;
	userId: UserId;
	sentAt: string;
};

export type ScanEvent = MessageEventRow & { emojis: Emoji[] };
