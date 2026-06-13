declare const _guildId: unique symbol
export type GuildId = string & { readonly [_guildId]: never }
export const asGuildId = (id: string): GuildId => id as GuildId
