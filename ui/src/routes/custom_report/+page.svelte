<script lang="ts">
	import { uploadFile } from '$lib/api'
	import { API_URL } from '$lib/env'
	import { captureException, logGAEvent } from '$lib/util/log'
	import { Footer, Header } from '$lib/components/layout'
	import { Done, Progress, Queued, Error, UploadForm } from '$lib/components/report'
	import type { ReportState, ReportJobResult, ReportType } from '$lib/components/report/types'

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

	let reportState: ReportState = $state(initState)

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

			// upload and processing completed successfully
			reportState = {
				...initState,
				view: 'done',
				status: 'success',
				progress: 100,
				result: uploadJobResult,
				errors: uploadJobErrors // there may be non-fatal errors (e.g., errors rendering maps)
			}
			window.location.href = `${API_URL}${uploadJobResult}` as string
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
</script>

<svelte:head>
	<title>Create a custom blueprint report</title>
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
		<div class="z-1 absolute top-[-40%]">
			<enhanced:img
				src="$images/IndianaDNR_Fountain_County_Wetland.jpg"
				class="h-auto min-w-[720px] object-cover"
				fetchpriority="high"
				alt=""
			/>
		</div>
		<div class="container mt-14">
			<h1 class="text-7xl relative text-white z-2 text-shadow-sm text-shadow-black">
				Create a custom blueprint report
			</h1>
		</div>
	</div>
	<div class="text-sm text-grey-8 text-right pr-1">
		Photo: Wetland in Fountain County, IN. Iowa Department of Natural Resources.
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
	{:else if reportState.view === 'done'}
		<Done
			reportURL={`${API_URL}${reportState.result}`}
			errors={reportState.errors}
			onReset={handleReset}
			class="mt-8"
		/>
	{:else}
		<UploadForm reportFormat="pdf" onSubmit={handleUpload} />
	{/if}
</main>

<Footer />
