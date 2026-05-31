const PERIOD_REGEX = /^(\d+)(h|d|w|m|y)$/;

export const DEFAULT_PERIOD_SUGGESTIONS = ['1h', '24h', '7d', '30d', '90d', '1y', 'all'];

export function parsePeriod(period: string): string | null {
	if (period === 'all') return null;
	const match = period.match(PERIOD_REGEX);
	if (!match) throw new Error(`Invalid period: "${period}". Use formats like 24h, 7d, 2w, 6m, 1y, or all.`);
	const [, num, unit] = match;
	const n = unit === 'w' ? parseInt(num, 10) * 7 : parseInt(num, 10);
	const sqlUnit = unit === 'h' ? 'hours' : unit === 'm' ? 'months' : unit === 'y' ? 'years' : 'days';
	return `datetime('now', '-${n} ${sqlUnit}')`;
}
