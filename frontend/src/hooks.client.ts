import type { HandleClientError } from '@sveltejs/kit';

function isChunkLoadError(error: unknown): boolean {
	if (!error) return false;
	const message = (error as Error)?.message || String(error);
	return (
		message.includes('Failed to fetch dynamically imported module') ||
		message.includes('Importing a module script failed') ||
		message.includes('error loading dynamically imported module') ||
		message.includes('Failed to load module script') ||
		message.includes('error loading module')
	);
}

export const handleError: HandleClientError = async ({ error, event, status, message }) => {
	if (typeof window !== 'undefined' && isChunkLoadError(error)) {
		const key = 'last_chunk_reload_timestamp';
		const lastReload = Number(sessionStorage.getItem(key) || 0);
		// Prevent infinite refresh loops by rate-limiting to once every 10 seconds
		if (Date.now() - lastReload > 10000) {
			sessionStorage.setItem(key, String(Date.now()));
			window.location.reload();
			return;
		}
	}

	return {
		message: message || 'An unexpected error occurred.'
	};
};
