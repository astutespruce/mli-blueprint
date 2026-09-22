import { captureException } from '$lib/util/log'
import { API_TOKEN, API_HOST } from '$lib/env'
import type {
	JobStatus,
	ProgressCallback,
	ReportType,
	ReportJobResult,
	SummaryUnitType
} from '$lib/components/report/types'

const pollInterval = 1000 // milliseconds; 1 second
const jobTimeout = 600000 // milliseconds; 10 minutes
const failedFetchLimit = 5

export const uploadFile = async (
	reportType: ReportType,
	file: File,
	name: string,
	onProgress: ProgressCallback
): Promise<ReportJobResult> => {
	// NOTE: both file and name are required by API
	const formData = new FormData()
	formData.append('file', file)
	formData.append('name', name)

	const response = await fetch(`${API_HOST}/api/custom_report/${reportType}?token=${API_TOKEN}`, {
		method: 'POST',
		body: formData
	})

	const json = await response.json()
	const { job, detail = null } = json

	if (response.status === 400) {
		// indicates error with user request, show error to user

		// just for logging
		console.error('Bad upload request', json)
		captureException('Bad upload request', json)

		return { status: 'failed', message: detail }
	}

	if (response.status !== 200) {
		console.error('Bad response', json)
		captureException('Bad upload response', json)

		throw new Error(response.statusText)
	}

	const result = await pollJob(job, onProgress)
	return result
}

export const finalizeXLSXReport = async (
	uuid: string,
	name: string | null,
	field: string | null,
	datasets: string,
	onProgress: ProgressCallback
): Promise<ReportJobResult> => {
	const formData = new FormData()
	if (name) {
		formData.append('name', name)
	}
	if (field) {
		formData.append('field', field)
	}
	formData.append('datasets', datasets)

	const response = await fetch(
		`${API_HOST}/api/custom_report/xlsx/${uuid}/finalize?token=${API_TOKEN}`,
		{
			method: 'POST',
			body: formData
		}
	)

	const json = await response.json()
	const { job, detail = null } = json

	if (response.status === 400) {
		// indicates error with user request, show error to user

		// just for logging
		console.error('Bad upload request', json)
		captureException('Bad upload request', json)

		return { status: 'failed', message: detail }
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
	type: SummaryUnitType,
	onProgress: ProgressCallback
): Promise<ReportJobResult> => {
	const unit_type = 'huc12' // other types not supported

	const response = await fetch(
		`${API_HOST}/api/summary_unit_report/${unit_type}/${id}/pdf?token=${API_TOKEN}`,
		{
			method: 'POST'
		}
	)

	const json = await response.json()
	const { job, detail = null } = json

	if (response.status === 400) {
		// indicates error with user request, show error to user

		// just for logging
		console.error('Bad create summary report request', json)
		captureException('Bad create summary report request', json)

		return { status: 'failed', message: detail }
	}

	if (response.status !== 200) {
		console.error('Bad response', json)
		captureException('Bad upload response', json)

		throw new Error(response.statusText)
	}

	const result = await pollJob(job, onProgress)
	return result
}

const pollJob = async (jobId: string, onProgress: ProgressCallback): Promise<ReportJobResult> => {
	let time = 0
	let failedRequests = 0

	let response = null

	while (time < jobTimeout && failedRequests < failedFetchLimit) {
		try {
			response = await fetch(`${API_HOST}/api/jobs/${jobId}`, {
				cache: 'no-cache'
			})
		} catch {
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
			detail = null,
			result = null
		} = json as {
			status?: JobStatus
			progress?: number
			queue_position?: number
			elapsed_time?: number | null
			message?: string | null // progress message
			result?: string | Record<string, unknown> | null
			detail?: string | null // fatal error message
			errors?: string[] | null // non-fatal errors
		}

		if (response.status !== 200 || status === 'failed') {
			captureException('Report job failed', json)
			if (detail) {
				return { status: 'failed', message: detail }
			}

			throw Error(response.statusText)
		}

		if (status === 'success') {
			return { status: 'success', result, errors }
		}

		if (status === 'queued' || status === 'in_progress' || progress !== null) {
			onProgress({
				// only show as queued if waiting for >= 5 seconds
				status:
					status === 'queued' && (elapsedTime === null || elapsedTime < 5) ? 'in_progress' : status,
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
			status: 'failed',
			message:
				'network errors were encountered while creating report.  The server may be too busy or your network connection may be having problems.  Please try again in a few minutes.'
		}
	}

	if (time >= jobTimeout) {
		captureException('Report job timed out')
		return {
			status: 'failed',
			message: 'timeout while creating report.  Your area of interest may be too big.'
		}
	}

	captureException('Report job had an unexpected error')
	return {
		status: 'failed',
		message:
			'unexpected errors prevented your report from completing successfully.  Please try again.'
	}
}
