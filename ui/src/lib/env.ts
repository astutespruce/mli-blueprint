import { browser } from '$app/env'
import { DEPLOY_PATH } from '$app/env/public'

export * from '$app/env/public'

export const BLUEPRINT_VERSION = '2026'

const deploy_path = DEPLOY_PATH || ''
const root_url = browser
	? `${window.location.protocol}//${window.location.host}${deploy_path}`
	: deploy_path
export const API_URL = `${root_url}/api`
export const TILES_URL = `${root_url}/tiles`
