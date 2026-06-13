import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import process from 'node:process'
import type { Guild } from 'discord.js'

const scenarioPath = process.env.SCENARIO_PATH ?? 'data/scenario.txt'
const examplePath = 'data/scenario.example.txt'

if (!existsSync(scenarioPath)) {
  const example = readFileSync(examplePath, 'utf8')
  mkdirSync(dirname(scenarioPath), { recursive: true })
  writeFileSync(scenarioPath, example, 'utf8')
  console.log(`Created ${scenarioPath} from example. Edit it to customize John Smith's personality.`)
}

const template = readFileSync(scenarioPath, 'utf8')

export function buildSystemPrompt(guild: Guild): string {
  const now = new Date().toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' })
  return template
    .replaceAll('{guild_name}', guild.name)
    .replaceAll('{time}', now)
}
