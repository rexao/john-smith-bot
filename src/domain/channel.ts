declare const _channelId: unique symbol;
export type ChannelId = string & { readonly [_channelId]: never };
export const asChannelId = (id: string): ChannelId => id as ChannelId;
