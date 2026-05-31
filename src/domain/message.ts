declare const _messageId: unique symbol;
export type MessageId = string & { readonly [_messageId]: never };
export const asMessageId = (id: string): MessageId => id as MessageId;
