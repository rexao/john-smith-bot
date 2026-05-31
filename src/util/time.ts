const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

export function calculateTimeElapsed(dt: Date, now: Date): string {
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
