import { browser } from '$app/environment'

export const hasGeolocation = browser && navigator && 'geolocation' in navigator

export const saveToStorage = (key: string, data: object) => {
	if (!browser) return

	window.localStorage.setItem(key, JSON.stringify(data))
}

export const getFromStorage = (key: string) => {
	if (!browser) return null

	const value = window.localStorage.getItem(key)

	return value !== undefined && value !== null ? JSON.parse(value) : null
}
