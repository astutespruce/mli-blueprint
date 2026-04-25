export type ReportState = {
	reportURL: string | null
	status: string | null
	progress: number
	queuePosition?: number
	elapsedTime?: number | null
	message?: string | null
	errors?: string[] | null // non-fatal errors
	inProgress: boolean | null
	error?: string | null // if error is non-null, it indicates there was an error
}

export type ReportJobResult = {
	error?: string
	result?: string
	errors?: string[]
}

export type ProgressCallbackParams = {
	status: string
	progress: number
	queuePosition?: number
	elapsedTime?: number
	message: string | null
	errors: string[] | null
}

export type ProgressCallback = (ProgressCallbackParams) => void
