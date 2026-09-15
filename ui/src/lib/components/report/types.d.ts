export type ReportType = 'pdf' | 'xlsx'

export type SummaryUnitType = 'subwatershed'

export type View = 'upload' | 'config' | 'done'

export type JobStatus = 'not_started' | 'queued' | 'in_progress' | 'success' | 'failed'

export type InspectResult = {
	uuid: string
	count: number
	fields: Record<string, number>
	datasets: string[]
}

export type Result = null | string | InspectResult

type ReportStateCore = {
	status: JobStatus
	progress: number
	queuePosition?: number
	elapsedTime?: number | null
	message?: string | null
	result?: Result
	errors?: string[] | null // non-fatal errors
}

export type ReportState = {
	view: View
} & ReportStateCore

export type SummaryUnitReportState = ReportStateCore

export type ReportJobResult = {
	status: JobStatus
	result?: Result
	message?: string
	errors?: string[] | null // non-fatal errors
}

export type ProgressCallbackParams = {
	status: JobStatus
	progress: number
	queuePosition?: number
	elapsedTime?: number
	message: string | null
	errors: string[] | null // non-fatal errors
}

export type ProgressCallback = (ProgressCallbackParams) => void
