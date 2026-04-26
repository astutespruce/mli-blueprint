<script lang="ts">
	import { uploadFile } from '$lib/api'
	import { captureException, logGAEvent } from '$lib/util/log'
	import { Footer, Header } from '$lib/components/layout'
	import { Done, Progress, Queued, ReportError, UploadForm } from '$lib/components/report'
	import type { ReportState, ReportJobResult } from '$lib/components/report/types'

	const initState: ReportState = {
		reportURL: null,
		status: null,
		progress: 0,
		queuePosition: 0,
		elapsedTime: null,
		message: null,
		errors: null, // non-fatal errors reported to user
		inProgress: false,
		error: null // if error is non-null, it indicates there was an error
	}

	let reportState: ReportState = $state(initState)

	const handleUpload = async (areaName: string, file: File) => {
		reportState = {
			...reportState,
			status: '',
			inProgress: true,
			progress: 0,
			queuePosition: 0,
			elapsedTime: null,
			message: null,
			errors: null,
			error: null,
			reportURL: null
		}

		logGAEvent('create-custom-report', {
			name: areaName,
			file: file.name,
			sizeKB: file.size / 1024
		})

		try {
			// upload file and update progress
			const {
				error: uploadError,
				result,
				errors: finalErrors
			}: ReportJobResult = await uploadFile(
				file,
				areaName,
				({
					status: nextStatus,
					progress: nextProgress,
					queuePosition: nextQueuePosition,
					elapsedTime: nextElapsedTime,
					message: nextMessage = null,
					errors: nextErrors = null
				}) => {
					reportState = {
						...reportState,
						status: nextStatus,
						inProgress:
							nextStatus === 'in_progress' ||
							(nextStatus === 'queued' && nextElapsedTime !== undefined && nextElapsedTime < 5),
						progress: nextProgress,
						queuePosition: nextQueuePosition,
						elapsedTime: nextElapsedTime,
						message: nextMessage || reportState.message,
						errors: nextErrors || reportState.errors
					}
				}
			)

			if (uploadError) {
				console.error(uploadError)

				reportState = {
					...reportState,
					inProgress: false,
					status: null,
					progress: 0,
					queuePosition: 0,
					elapsedTime: null,
					message: null,
					errors: null,
					error: uploadError,
					reportURL: null
				}

				logGAEvent('file-upload-error')

				return
			}

			// upload and processing completed successfully
			reportState = {
				...reportState,
				status: null,
				progress: 100,
				queuePosition: 0,
				elapsedTime: null,
				message: null,
				errors: finalErrors, // there may be non-fatal errors (e.g., errors rendering maps)
				inProgress: false,
				reportURL: result as string
			}

			window.location.href = result as string
		} catch (ex) {
			captureException('File upload failed', ex)
			console.error('Caught unhandled error from uploadFile', ex)

			reportState = {
				...reportState,
				inProgress: false,
				status: null,
				progress: 0,
				queuePosition: 0,
				elapsedTime: null,
				message: null,
				errors: null,
				error: '', // no meaningful error to show to user, but needs to be non-null}
				reportURL: null
			}
		}
	}

	const handleReset = () => {
		reportState = initState
	}
</script>

<svelte:head>
	<title>Create a custom Blueprint report</title>
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
				src="$images/26871026541_48a8096dd9_o.jpg"
				class="h-auto min-w-[720px] object-cover brightness-60"
				alt=""
			/>
		</div>
		<div class="container mt-14">
			<h1 class="text-7xl relative text-white z-2 text-shadow-sm text-shadow-black">
				Create a custom Blueprint report
			</h1>
		</div>
	</div>
	<div class="text-sm text-grey-8 text-right pr-1">
		Photo: Black Skimmers, <a
			href="https://www.flickr.com/photos/usfwssoutheast/26871026541/"
			target="_blank"
			tabindex="-1"
			class="text-grey-8">U.S. Fish and Wildlife Service Southeast Region</a
		>
	</div>

	{#if reportState.error !== null}
		<ReportError error={reportState.error} onReset={handleReset} class="mt-8" />
	{:else if reportState.reportURL !== null}
		<Done
			reportURL={reportState.reportURL}
			errors={reportState.errors}
			onReset={handleReset}
			class="mt-8"
		/>
	{:else if reportState.inProgress}
		<Progress message={reportState.message} progress={reportState.progress} class="mt-4" />
	{:else if reportState.status === 'queued'}
		<Queued
			message={reportState.message}
			queuePosition={reportState.queuePosition}
			elapsedTime={reportState.elapsedTime}
			class="mt-8"
		/>
	{:else}
		<UploadForm onSubmit={handleUpload} />
	{/if}
</main>

<Footer />
