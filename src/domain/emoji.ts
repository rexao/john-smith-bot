export const EMOJI_REGEX = /<(a?):(\w+):(\d+)>/g

export class Emoji {
  readonly id: string

  readonly name: string

  readonly animated: boolean

  constructor(id: string, name: string, animated: boolean) {
    this.id = id
    this.name = name
    this.animated = animated
  }

  format(): string {
    return this.animated
      ? `<a:${this.name}:${this.id}>`
      : `<:${this.name}:${this.id}>`
  }

  static fromRegexMatch(animatedFlag: string, name: string, id: string): Emoji {
    return new Emoji(id, name, animatedFlag === 'a')
  }
}
