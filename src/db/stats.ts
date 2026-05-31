import db from './index.ts';
import { type GuildId } from '../domain/guild.ts';
import { type UserId } from '../domain/user.ts';
import { type ChannelId } from '../domain/channel.ts';
import { type MessageId } from '../domain/message.ts';
import { Emoji } from '../domain/emoji.ts';

export type ChatterRow = { user_id: UserId; message_count: number };
export type EmojiRow   = { emoji_id: string; emoji_name: string; animated: number; usage_count: number };

export function rowToEmoji(row: EmojiRow): Emoji {
	return new Emoji(row.emoji_id, row.emoji_name, row.animated === 1);
}

export function insertMessageEvent(
	messageId: MessageId,
	guildId: GuildId,
	channelId: ChannelId,
	userId: UserId,
): void {
	db.prepare(`
		INSERT OR IGNORE INTO message_events (message_id, guild_id, channel_id, user_id, sent_at)
		VALUES (?, ?, ?, ?, datetime('now'))
	`).run(messageId, guildId, channelId, userId);
}

export function insertEmojiEvent(
	messageId: MessageId,
	guildId: GuildId,
	channelId: ChannelId,
	emojiId: string,
	emojiName: string,
	animated: boolean,
	userId: UserId,
): void {
	db.prepare(`
		INSERT INTO emoji_events (message_id, guild_id, channel_id, emoji_id, emoji_name, animated, user_id, used_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
	`).run(messageId, guildId, channelId, emojiId, emojiName, animated ? 1 : 0, userId);
}

export function queryTopChatters(guildId: GuildId, since: string | null, limit: number, offset: number): ChatterRow[] {
	return db.prepare(`
		SELECT user_id, COUNT(*) as message_count
		FROM message_events
		WHERE guild_id = ? ${since ? `AND sent_at >= ${since}` : ''}
		GROUP BY user_id
		ORDER BY message_count DESC
		LIMIT ? OFFSET ?
	`).all(guildId, limit, offset) as ChatterRow[];
}

export function queryTopEmojis(guildId: GuildId, since: string | null, limit: number, offset: number): EmojiRow[] {
	return db.prepare(`
		SELECT emoji_id, emoji_name, animated, COUNT(*) as usage_count
		FROM emoji_events
		WHERE guild_id = ? ${since ? `AND used_at >= ${since}` : ''}
		GROUP BY emoji_id
		ORDER BY usage_count DESC
		LIMIT ? OFFSET ?
	`).all(guildId, limit, offset) as EmojiRow[];
}

export function queryTotalChatters(guildId: GuildId, since: string | null): number {
	const row = db.prepare(`
		SELECT COUNT(DISTINCT user_id) as total
		FROM message_events
		WHERE guild_id = ? ${since ? `AND sent_at >= ${since}` : ''}
	`).get(guildId) as { total: number };
	return row.total;
}

export function queryTotalEmojis(guildId: GuildId, since: string | null): number {
	const row = db.prepare(`
		SELECT COUNT(DISTINCT emoji_name) as total
		FROM emoji_events
		WHERE guild_id = ? ${since ? `AND used_at >= ${since}` : ''}
	`).get(guildId) as { total: number };
	return row.total;
}

export type MessageEventRow = {
	messageId: MessageId;
	guildId: GuildId;
	channelId: ChannelId;
	userId: UserId;
	sentAt: string;
};

export type EmojiEventRow = {
	messageId: MessageId;
	guildId: GuildId;
	channelId: ChannelId;
	emojiId: string;
	emojiName: string;
	animated: boolean;
	userId: UserId;
	usedAt: string;
};

export type ScanEvent = MessageEventRow & { emojis: Emoji[] };

export function bulkInsert(events: ScanEvent[]): number {
	const insertMessage = db.prepare(`
		INSERT OR IGNORE INTO message_events (message_id, guild_id, channel_id, user_id, sent_at)
		VALUES (?, ?, ?, ?, ?)
	`);
	const insertEmoji = db.prepare(`
		INSERT INTO emoji_events (message_id, guild_id, channel_id, emoji_id, emoji_name, animated, user_id, used_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`);

	let inserted = 0;

	db.transaction(() => {
		for (const event of events) {
			const result = insertMessage.run(event.messageId, event.guildId, event.channelId, event.userId, event.sentAt);
			if (result.changes === 0) continue; // 既存メッセージはスキップ
			inserted++;
			for (const emoji of event.emojis) {
				insertEmoji.run(event.messageId, event.guildId, event.channelId, emoji.id, emoji.name, emoji.animated ? 1 : 0, event.userId, event.sentAt);
			}
		}
	})();

	return inserted;
}
