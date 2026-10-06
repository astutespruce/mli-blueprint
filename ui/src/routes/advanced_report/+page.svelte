<script lang="ts">
	import { uploadFile, finalizeXLSXReport } from '$lib/api'
	import { API_URL } from '$lib/env'
	import { captureException, logGAEvent } from '$lib/util/log'
	import { Footer, Header } from '$lib/components/layout'
	import {
		ConfigXLSXReport,
		Done,
		Progress,
		Queued,
		Error,
		UploadForm
	} from '$lib/components/report'
	import type {
		ReportState,
		ReportJobResult,
		ReportType,
		InspectResult
	} from '$lib/components/report/types'

	const initState: ReportState = {
		view: 'upload',
		status: 'not_started',
		progress: 0,
		queuePosition: 0,
		elapsedTime: null,
		message: null,
		result: null,
		errors: null // non-fatal errors reported to user
	}

	type ConfigData = {
		name: string | null
	} & InspectResult

	let reportState: ReportState = $state(initState)
	let configData: ConfigData | null = $state(null)

	const handleUpload = async (reportType: ReportType, areaName: string, file: File) => {
		reportState = {
			...initState,
			status: 'in_progress'
		}

		logGAEvent(`create-custom-${reportType}-report`, {
			name: areaName,
			file: file.name,
			sizeKB: file.size / 1024
		})

		try {
			// upload file and update progress
			const {
				status: uploadJobStatus,
				result: uploadJobResult,
				message: uploadJobErrorMessage,
				errors: uploadJobErrors
			}: ReportJobResult = await uploadFile(
				reportType,
				file,
				areaName,
				({
					status: nextStatus,
					progress: nextProgress,
					queuePosition: nextQueuePosition,
					elapsedTime: nextElapsedTime,
					message: nextMessage = reportState.message,
					errors: nextErrors = reportState.errors
				}) => {
					reportState = {
						...reportState,
						status: nextStatus,
						progress: nextProgress,
						queuePosition: nextQueuePosition,
						elapsedTime: nextElapsedTime,
						message: nextMessage,
						errors: nextErrors
					}
				}
			)

			if (uploadJobStatus === 'failed') {
				console.error(uploadJobErrorMessage)

				reportState = {
					...initState,
					status: 'failed',
					message: uploadJobErrorMessage
				}

				logGAEvent('file-upload-error')

				return
			}

			configData = {
				name: areaName,
				...(uploadJobResult as InspectResult)
			}

			reportState = {
				...initState,
				view: 'config'
			}
		} catch (ex) {
			captureException('File upload failed', ex)
			console.error('Caught unhandled error from uploadFile', ex)

			reportState = {
				...initState,
				status: 'failed'
				// NOTE: no meaningful error to show to user
			}
		}
	}

	const handleReset = () => {
		reportState = initState
	}

	const handleSubmitXLSXReport = async (field: string, datasets: string[]) => {
		reportState = {
			...reportState,
			status: 'in_progress'
		}

		logGAEvent('finalize-custom-xlsx-report', {
			name: configData!.name,
			field,
			datasets: datasets.join(',')
		})

		try {
			const {
				status: finalizeJobStatus,
				result: finalizeJobResult,
				message: finalizeJobErrorMessage
			}: ReportJobResult = await finalizeXLSXReport(
				configData!.uuid,
				configData!.name,
				field,
				datasets.join(','),
				({
					status: nextStatus,
					progress: nextProgress,
					queuePosition: nextQueuePosition,
					elapsedTime: nextElapsedTime,
					message: nextMessage = reportState.message,
					errors: nextErrors = reportState.errors
				}) => {
					reportState = {
						...reportState,
						status: nextStatus,
						progress: nextProgress,
						queuePosition: nextQueuePosition,
						elapsedTime: nextElapsedTime,
						message: nextMessage,
						errors: nextErrors
					}
				}
			)

			if (finalizeJobStatus === 'failed') {
				console.error(finalizeJobErrorMessage)

				reportState = {
					...initState,
					status: 'failed',
					message: finalizeJobErrorMessage
				}

				logGAEvent('file-upload-error')

				return
			}

			reportState = {
				...initState,
				view: 'done',
				result: finalizeJobResult
			}

			window.location.href = `${API_URL}${finalizeJobResult}` as string
		} catch (ex) {
			captureException('finalize XLSX report failed', ex)
			console.error('Caught unhandled error from finalize XLSX report', ex)

			reportState = {
				...initState,
				status: 'failed'
				// NOTE: no meaningful error to show to user
			}
		}
	}
</script>

<svelte:head>
	<title>Create an advanced Blueprint report</title>
</svelte:head>

<svelte:document
	ondragover={(e) => {
		e.preventDefault()
	}}
	ondrop={(e) => {
		e.preventDefault()
	}}
/>

<Header />

<main class="h-full w-full flex-auto overflow-auto">
	<div class="relative z-0 w-full overflow-hidden h-56">
		<div class="z-1 absolute top-[-20%]">
			<enhanced:img
				src="$images/usfws-candy-darter.jpg"
				class="h-auto min-w-[720px] object-cover"
				alt=""
				fetchpriority="high"
			/>
		</div>
		<div class="container mt-14">
			<h1 class="text-7xl relative text-white z-2 text-shadow-sm text-shadow-black">
				Create an advanced Blueprint report
			</h1>
		</div>
	</div>
	<div class="text-sm text-grey-8 text-right pr-1">
		Photo: Candy darter, <a
			href="https://www.fws.gov/media/candy-darter-30"
			target="_blank"
			tabindex="-1"
			class="text-grey-8">Ryan Hagerty/USFWS</a
		>
	</div>

	{#if reportState.status === 'failed'}
		<Error message={reportState.message} onReset={handleReset} class="mt-8" />
	{:else if reportState.status === 'queued'}
		<Queued
			message={reportState.message}
			queuePosition={reportState.queuePosition}
			elapsedTime={reportState.elapsedTime}
			class="mt-8"
		/>
	{:else if reportState.status === 'in_progress'}
		<Progress message={reportState.message} progress={reportState.progress} class="mt-4" />
	{:else if reportState.view === 'config' && configData !== null}
		<ConfigXLSXReport {...configData} onStartOver={handleReset} onSubmit={handleSubmitXLSXReport} />
	{:else if reportState.view === 'done'}
		<Done
			reportURL={`${API_URL}${reportState.result}`}
			errors={reportState.errors}
			onReset={handleReset}
			class="mt-8"
		/>
	{:else}
		<UploadForm reportFormat="xlsx" onSubmit={handleUpload} />
	{/if}
</main>

<Footer />
