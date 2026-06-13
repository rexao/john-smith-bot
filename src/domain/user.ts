declare const _userId: unique symbol
export type UserId = string & { readonly [_userId]: never }
export const asUserId = (id: string): UserId => id as UserId
