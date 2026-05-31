const PERIOD_REGEX = /^(\d+)(h|d|w|m|y)$/;

const UNITS = ['h', 'd', 'w', 'm', 'y'];

export const DEFAULT_PERIOD_SUGGESTIONS = ['1h', '24h', '7d', '30d', '90d', '1y', 'all'];

export function getPeriodSuggestions(current: string): string[] {
	if (!current) return DEFAULT_PERIOD_SUGGESTIONS;
	const numMatch = current.match(/^(\d+)$/);
	if (numMatch) return UNITS.map((u) => `${numMatch[1]}${u}`).concat(['all']);
	return DEFAULT_PERIOD_SUGGESTIONS.filter((s) => s.startsWith(current));
}

const UNIT_LABEL: Record<string, string> = { h: 'Hour', d: 'Day', w: 'Week', m: 'Month', y: 'Year' };

export function periodLabel(period: string): string {
	if (period === 'all') return 'All Time';
	const match = period.match(PERIOD_REGEX);
	if (!match) return period;
	const [, num, unit] = match;
	const n = parseInt(num, 10);
	return `Last ${n} ${UNIT_LABEL[unit]}${n > 1 ? 's' : ''}`;
}

export function parsePeriod(period: string): Date | null {
	if (period === 'all') return null;
	const match = period.match(PERIOD_REGEX);
	if (!match) throw new Error(`Invalid period: "${period}". Use formats like 24h, 7d, 2w, 6m, 1y, or all.`);
	const [, num, unit] = match;
	const n = parseInt(num, 10);
	const since = new Date();
	if (unit === 'h') since.setHours(since.getHours() - n);
	else if (unit === 'd') since.setDate(since.getDate() - n);
	else if (unit === 'w') since.setDate(since.getDate() - n * 7);
	else if (unit === 'm') since.setMonth(since.getMonth() - n);
	else since.setFullYear(since.getFullYear() - n);
	return since;
}
