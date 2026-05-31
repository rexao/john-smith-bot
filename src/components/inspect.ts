import {
	ActionRowBuilder,
	ButtonBuilder,
	ButtonStyle,
	ChannelType,
	EmbedBuilder,
	type Client,
	type Guild,
	type GuildMember,
} from 'discord.js';

const COLOR = 0x5873f2;

const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

function calculateTimeElapsed(dt: Date, now: Date): string {
	const diff = now.getTime() - dt.getTime();
	const seconds = diff / 1_000;
	const minutes = seconds / 60;
	const hours = minutes / 60;
	const days = hours / 24;

	if (seconds < 60) return rtf.format(-Math.floor(seconds), 'second');
	if (minutes < 60) return rtf.format(-Math.floor(minutes), 'minute');
	if (hours < 24) return rtf.format(-Math.floor(hours), 'hour');
	if (days < 30) return rtf.format(-Math.floor(days), 'day');
	if (days < 365) return rtf.format(-Math.floor(days / 30), 'month');
	return rtf.format(-Math.floor(days / 365), 'year');
}

export type ServerPage = 'main' | 'icon' | 'bannerBackground' | 'inviteBackground';
export type UserPage = 'main' | 'avatar' | 'profileBanner' | 'serverAvatar';

export function buildServerEmbeds(guild: Guild): Record<ServerPage, EmbedBuilder> {
	const now = new Date();
	const guildIconURL = guild.iconURL() ?? undefined;

	const main = new EmbedBuilder()
		.setColor(COLOR)
		.setTimestamp(now)
		.setAuthor({ name: guild.name, iconURL: guildIconURL })
		.setThumbnail(guild.iconURL())
		.addFields(
			{
				name: 'Overview',
				value: [
					`ID: \`${guild.id}\``,
					guild.description ? `Description: \`${guild.description}\`` : null,
					guild.vanityURLCode ? `Vanity URL: \`discord.gg/${guild.vanityURLCode}\`` : null,
				].filter(Boolean).join('\n'),
			},
			{
				name: 'Owner',
				value: [
					`Owner: <@${guild.ownerId}>`,
					`Created: \`${guild.createdAt.toLocaleDateString('en-US')} (${calculateTimeElapsed(guild.createdAt, now)})\``,
				].join('\n'),
			},
			{
				name: 'Members',
				value: [
					`Members: \`${guild.memberCount}\``,
					guild.maximumMembers ? `Max Members: \`${guild.maximumMembers}\`` : null,
				].filter(Boolean).join('\n'),
			},
			{
				name: 'Channels',
				value: [
					`Categories: \`${guild.channels.cache.filter((c) => c.type === ChannelType.GuildCategory).size}\``,
					`Text Channels: \`${guild.channels.cache.filter((c) => c.type === ChannelType.GuildText).size}\``,
					`Voice Channels: \`${guild.channels.cache.filter((c) => c.type === ChannelType.GuildVoice).size}\``,
				].join('\n'),
			},
			{
				name: 'Roles',
				value:
					guild.roles.cache
						.filter((r) => r.name !== '@everyone')
						.map((r) => r.toString())
						.join(' ') || 'None',
			},
			{
				name: 'Boosts',
				value: [
					`Boost Tier: \`${guild.premiumTier}\``,
					`Boosts: \`${guild.premiumSubscriptionCount}\``,
				].join('\n'),
			},
			{
				name: 'Security & Locale',
				value: [
					`Verification: \`${guild.verificationLevel}\``,
					`Locale: \`${guild.preferredLocale}\``,
				].join('\n'),
			},
			...(guild.features.length > 0 ? [{
				name: 'Features',
				value: guild.features.map((f) => `\`${f}\``).join(' '),
			}] : []),
		);

	const icon = new EmbedBuilder()
		.setColor(COLOR)
		.setTimestamp(now)
		.setAuthor({ name: guild.name, iconURL: guildIconURL })
		.setTitle('Server Icon');

	if (guild.icon) {
		icon.setImage(guild.iconURL({ size: 4_096 })).addFields({ name: 'Icon Hash', value: `\`${guild.icon}\`` });
	} else {
		icon.setDescription("There's no server icon.");
	}

	const bannerBackground = new EmbedBuilder()
		.setColor(COLOR)
		.setTimestamp(now)
		.setAuthor({ name: guild.name, iconURL: guildIconURL })
		.setTitle('Server Banner Background');

	if (guild.banner) {
		bannerBackground
			.setImage(guild.bannerURL({ size: 4_096 }))
			.addFields({ name: 'Banner Hash', value: `\`${guild.banner}\`` });
	} else {
		bannerBackground.setDescription("There's no server banner background.");
	}

	const inviteBackground = new EmbedBuilder()
		.setColor(COLOR)
		.setTimestamp(now)
		.setAuthor({ name: guild.name, iconURL: guildIconURL })
		.setTitle('Server Invite Background');

	if (guild.splash) {
		inviteBackground
			.setImage(guild.splashURL({ size: 4_096 }))
			.addFields({ name: 'Splash Hash', value: `\`${guild.splash}\`` });
	} else {
		inviteBackground.setDescription("There's no server invite background.");
	}

	return { main, icon, bannerBackground, inviteBackground };
}

export function buildServerComponents(page: ServerPage): ActionRowBuilder<ButtonBuilder> {
	const row = new ActionRowBuilder<ButtonBuilder>();

	if (page === 'main') {
		row.addComponents(
			new ButtonBuilder().setCustomId('inspect:server:icon').setLabel('Icon').setStyle(ButtonStyle.Primary),
			new ButtonBuilder()
				.setCustomId('inspect:server:bannerBackground')
				.setLabel('Banner Background')
				.setStyle(ButtonStyle.Primary),
			new ButtonBuilder()
				.setCustomId('inspect:server:inviteBackground')
				.setLabel('Invite Background')
				.setStyle(ButtonStyle.Primary),
		);
	} else {
		row.addComponents(
			new ButtonBuilder().setCustomId('inspect:server:main').setLabel('< Back').setStyle(ButtonStyle.Secondary),
		);
	}

	return row;
}

export async function buildUserEmbeds(member: GuildMember, client: Client): Promise<Record<UserPage, EmbedBuilder>> {
	const now = new Date();
	const { user } = member;
	const clientUser = await client.users.fetch(user.id, { force: true });
	const authorName = member.nickname ? `${member.nickname} (${user.username})` : user.username;
	const displayAvatarURL = member.displayAvatarURL({ size: 4_096 });

	const main = new EmbedBuilder()
		.setColor(COLOR)
		.setTimestamp(now)
		.setAuthor({ name: authorName, iconURL: displayAvatarURL })
		.setThumbnail(displayAvatarURL)
		.addFields(
			{ name: 'ID', value: `\`${user.id}\`` },
			{
				name: 'Roles',
				value:
					member.roles.cache
						.filter((r) => r.name !== '@everyone')
						.map((r) => r.toString())
						.join(' ') || 'None',
			},
			{
				name: 'Joined Server',
				value: member.joinedAt
					? `\`${member.joinedAt.toLocaleDateString('en-US')} (${calculateTimeElapsed(member.joinedAt, now)})\``
					: 'Unknown',
			},
			{
				name: 'Joined Discord',
				value: `\`${user.createdAt.toLocaleDateString('en-US')} (${calculateTimeElapsed(user.createdAt, now)})\``,
			},
		);

	const avatar = new EmbedBuilder()
		.setColor(COLOR)
		.setTimestamp(now)
		.setAuthor({ name: authorName, iconURL: displayAvatarURL })
		.setTitle('Avatar');

	if (user.avatar) {
		avatar.setImage(user.avatarURL({ size: 4_096 })).addFields({ name: 'Avatar Hash', value: `\`${user.avatar}\`` });
	} else {
		avatar.setDescription(`${user.toString()} has no avatar.`).setImage(displayAvatarURL);
	}

	const profileBanner = new EmbedBuilder()
		.setColor(COLOR)
		.setTimestamp(now)
		.setAuthor({ name: authorName, iconURL: displayAvatarURL })
		.setTitle('Profile Banner');

	if (clientUser.banner) {
		profileBanner
			.setImage(clientUser.bannerURL({ size: 4_096 })!)
			.addFields({ name: 'Banner Hash', value: `\`${clientUser.banner}\`` });
	} else {
		profileBanner.setDescription(`${user.toString()} has no profile banner.`);
	}

	const serverAvatar = new EmbedBuilder()
		.setColor(COLOR)
		.setTimestamp(now)
		.setAuthor({ name: authorName, iconURL: displayAvatarURL })
		.setTitle('Server Avatar');

	if (member.avatar) {
		serverAvatar
			.setImage(member.displayAvatarURL({ size: 4_096 }))
			.addFields({ name: 'Guild Avatar Hash', value: `\`${member.avatar}\`` });
	} else {
		serverAvatar.setDescription(`${user.toString()} has no server avatar.`).setImage(displayAvatarURL);
	}

	return { main, avatar, profileBanner, serverAvatar };
}

export function buildUserComponents(userId: string, page: UserPage, inGuild: boolean): ActionRowBuilder<ButtonBuilder> {
	const row = new ActionRowBuilder<ButtonBuilder>();

	if (page === 'main') {
		row.addComponents(
			new ButtonBuilder()
				.setCustomId(`inspect:user:${userId}:avatar`)
				.setLabel('Avatar')
				.setStyle(ButtonStyle.Primary),
			new ButtonBuilder()
				.setCustomId(`inspect:user:${userId}:profileBanner`)
				.setLabel('Profile Banner')
				.setStyle(ButtonStyle.Primary),
		);
		if (inGuild) {
			row.addComponents(
				new ButtonBuilder()
					.setCustomId(`inspect:user:${userId}:serverAvatar`)
					.setLabel('Server Avatar')
					.setStyle(ButtonStyle.Primary),
			);
		}
	} else {
		row.addComponents(
			new ButtonBuilder()
				.setCustomId(`inspect:user:${userId}:main`)
				.setLabel('< Back')
				.setStyle(ButtonStyle.Secondary),
		);
	}

	return row;
}
