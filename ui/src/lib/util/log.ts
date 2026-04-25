import * as Sentry from '@sentry/browser'

import { browser } from '$app/environment'

export const captureException = (err: Error | string, data: object | null = null) => {
	if (browser && window.Sentry) {
		Sentry.withScope((scope) => {
			// capture location where error occurred
			scope.setFingerprint([window.location.pathname])
			if (data) {
				scope.setExtra('data', data)
			}
			Sentry.captureException(err)
		})
	}
}

export const logGAEvent = (event: string, data: object | null = null) => {
	// NOTE: window.gtag only available in build mode
	if (!(browser && window.gtag)) {
		return
	}

	try {
		window.gtag('event', event, data)
	} catch (ex) {
		console.error('Could not log event to google', ex)
	}
}
