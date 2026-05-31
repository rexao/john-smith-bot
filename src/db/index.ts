import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import process from 'node:process';
import Database from 'better-sqlite3';

const dbPath = process.env.DB_PATH ?? 'data/data.sqlite';
mkdirSync(dirname(dbPath), { recursive: true });

const db = new Database(dbPath);
db.pragma('journal_mode = WAL');

db.exec(`
	CREATE TABLE IF NOT EXISTS message_events (
		message_id  TEXT PRIMARY KEY,
		guild_id    TEXT NOT NULL,
		channel_id  TEXT NOT NULL,
		user_id     TEXT NOT NULL,
		sent_at     TEXT NOT NULL
	);
	CREATE INDEX IF NOT EXISTS idx_message_events ON message_events (guild_id, sent_at);

	CREATE TABLE IF NOT EXISTS emoji_events (
		message_id  TEXT NOT NULL,
		guild_id    TEXT NOT NULL,
		channel_id  TEXT NOT NULL,
		emoji_id    TEXT NOT NULL,
		emoji_name  TEXT NOT NULL,
		animated    INTEGER NOT NULL DEFAULT 0,
		user_id     TEXT NOT NULL,
		used_at     TEXT NOT NULL
	);
	CREATE INDEX IF NOT EXISTS idx_emoji_events ON emoji_events (guild_id, used_at);
`);

export default db;
