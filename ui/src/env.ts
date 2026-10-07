import { defineEnvVars } from '@sveltejs/kit/env'

export const variables = defineEnvVars({
	SENTRY_DSN: { public: true, static: true },
	GOOGLE_ANALYTICS_ID: { public: true, static: true },
	MAPBOX_TOKEN: { public: true, static: true },
	API_TOKEN: { public: true, static: true },
	DEPLOY_ENV: { public: true, static: true },
	DEPLOY_PATH: { public: true, static: true },
	CONTACT_URL: { public: true, static: true },
	BLUEPRINT_URL: { public: true, static: true }
})
