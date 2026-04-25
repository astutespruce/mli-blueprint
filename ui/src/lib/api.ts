import { browser } from '$app/environment'
import { captureException } from '$lib/util/log'
import { API_TOKEN, API_HOST } from '$lib/env'
import type { ProgressCallback } from '$lib/components/report/types'

let apiHost = API_HOST

const pollInterval = 1000 // milliseconds; 1 second
const jobTimeout = 600000 // milliseconds; 10 minutes
const failedFetchLimit = 5

if (browser && !apiHost) {
	apiHost = `//${window.location.host}`
}

const API = `${apiHost}/api/reports`

export const uploadFile = async (file: File, name: string, onProgress: ProgressCallback) => {
	// NOTE: both file and name are required by API
	const formData = new FormData()
	formData.append('file', file)
	formData.append('name', name)

	const response = await fetch(`${API}/custom?token=${API_TOKEN}`, {
		method: 'POST',
		body: formData
	})

	const json = await response.json()
	const { job, detail } = json

	if (response.status === 400) {
		// indicates error with user request, show error to user

		// just for logging
		console.error('Bad upload request', json)
		captureException('Bad upload request', json)

		return { error: detail }
	}

	if (response.status !== 200) {
		console.error('Bad response', json)

		captureException('Bad upload response', json)

		throw new Error(response.statusText)
	}

	const result = await pollJob(job, onProgress)
	return result
}

export const createSummaryUnitReport = async (
	id: string,
	type: string,
	onProgress: ProgressCallback
) => {
	let unitType = null

	if (type === 'subwatershed') {
		unitType = 'huc12'
	} else if (type === 'marine hex') {
		unitType = 'marine_hex'
	}

	const response = await fetch(`${API}/${unitType}/${id}?token=${API_TOKEN}`, {
		method: 'POST'
	})

	const json = await response.json()
	const { job, detail } = json

	if (response.status === 400) {
		// indicates error with user request, show error to user

		// just for logging
		console.error('Bad create summary report request', json)
		captureException('Bad create summary report request', json)

		return { error: detail }
	}

	if (response.status !== 200) {
		console.error('Bad response', json)
		captureException('Bad upload response', json)

		throw new Error(response.statusText)
	}

	const result = await pollJob(job, onProgress)
	return result
}

const pollJob = async (jobId: string, onProgress: ProgressCallback) => {
	let time = 0
	let failedRequests = 0

	let response = null

	while (time < jobTimeout && failedRequests < failedFetchLimit) {
		try {
			response = await fetch(`${API}/status/${jobId}`, {
				cache: 'no-cache'
			})
		} catch (_) {
			failedRequests += 1

			// sleep and try again
			await new Promise((r) => {
				setTimeout(r, pollInterval)
			})
			time += pollInterval
			continue
		}

		const json = await response.json()
		const {
			status = null,
			progress = null,
			queue_position: queuePosition = null,
			elapsed_time: elapsedTime = null,
			message = null,
			errors = null,
			detail: error = null, // error message
			result = null
		} = json

		if (response.status !== 200 || status === 'failed') {
			captureException('Report job failed', json)
			if (error) {
				return { error }
			}

			throw Error(response.statusText)
		}

		if (status === 'success') {
			return { result: `${apiHost}${result}`, errors }
		}

		if (status === 'queued' || status === 'in_progress' || progress !== null) {
			onProgress({
				status,
				progress: progress || 0,
				queuePosition: queuePosition || 0,
				elapsedTime: elapsedTime || null,
				message,
				errors
			})
		}

		// sleep
		await new Promise((r) => {
			setTimeout(r, pollInterval)
		})
		time += pollInterval
	}

	// if we got here, it meant that we hit a timeout error or a fetch error
	if (failedRequests) {
		captureException(`Report job encountered ${failedRequests} fetch errors`)

		return {
			error:
				'network errors were encountered while creating report.  The server may be too busy or your network connection may be having problems.  Please try again in a few minutes.'
		}
	}

	if (time >= jobTimeout) {
		captureException('Report job timed out')
		return {
			error: 'timeout while creating report.  Your area of interest may be too big.'
		}
	}

	captureException('Report job had an unexpected error')
	return {
		error:
			'unexpected errors prevented your report from completing successfully.  Please try again.'
	}
}
