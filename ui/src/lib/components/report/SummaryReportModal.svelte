<script lang="ts">
	import DownloadIcon from '~icons/fa-solid/download'
	import { createSummaryUnitReport } from '$lib/api'
	import { CONTACT_URL } from '$lib/env'
	import { Root, Trigger, Content, Header, Title } from '$lib/components/ui/dialog'
	import { Button } from '$lib/components/ui/button'
	import { captureException, logGAEvent } from '$lib/util/log'
	import Done from './Done.svelte'
	import Progress from './Progress.svelte'
	import Queued from './Queued.svelte'
	import ReportError from './ReportError.svelte'
	import type { ReportState, ReportJobResult, ProgressCallbackParams } from './types'

	let open: boolean = $state(false)

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

	const { id, type } = $props()

	let reportState: ReportState = $state(initState)

	const handleModelOpenChange = () => {
		if (!open) {
			reportState = initState
		}
	}

	const handleClose = () => {
		// TODO: cancel report on server
		open = false
		reportState = initState
	}

	const handleCreateReport = async () => {
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

		logGAEvent('create-summary-report', { type, id: `${type}:${id}` })

		try {
			const {
				error: uploadError,
				result,
				errors: finalErrors
			}: ReportJobResult = await createSummaryUnitReport(
				id,
				type,
				({
					status: nextStatus,
					progress: nextProgress,
					queuePosition: nextQueuePosition,
					elapsedTime: nextElapsedTime,
					message: nextMessage = null,
					errors: nextErrors = null
				}: ProgressCallbackParams) => {
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

				logGAEvent('summary-unit-report-error')

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
			captureException(`Create summary report for ${id} (${type}) failed`, ex)
			console.error('Caught unhandled error from createSummaryUnitReport', ex)

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
</script>

<Root bind:open onOpenChange={handleModelOpenChange}>
	<Trigger>
		<div class="flex items-center gap-2 text-link text-md cursor-pointer hover:underline">
			<DownloadIcon class="size-4" />
			Export detailed maps and analysis
		</div>
	</Trigger>
	<Content class="pt-4 pb-6 pr-6">
		<Header class="border-b pb-4 border-b-grey-2">
			<Title class="text-3xl">Blueprint Summary Report</Title>
		</Header>

		<div class="pt-2 pb-4">
			{#if reportState.error !== null}
				<ReportError error={reportState.error} />
			{:else if reportState.reportURL !== null}
				<Done errors={reportState.errors} />
				<p class="text-lg">You can also click the button below to download your report.</p>
			{:else if reportState.inProgress}
				<Progress message={reportState.message} progress={reportState.progress} />
			{:else if reportState.status === 'queued'}
				<Queued
					message={reportState.message}
					queuePosition={reportState.queuePosition}
					elapsedTime={reportState.elapsedTime}
				/>
			{:else}
				<p class="text-xl">
					Create and download a blueprint summary report for this area. This detailed report
					includes maps and analysis of the blueprint priorities and each indicator present in this
					area, as well as potential threats and protected areas.
				</p>
				<p class="text-md mt-4">
					Note: we have made every possible effort to ensure that the information provided in this
					viewer is accessible to people with disabilities. If you cannot fully access the
					information, please reach out to
					<a href={CONTACT_URL} target="_blank"> Midwest Landscape Initiative staff </a>
					so that we can provide the information in an alternate format.
				</p>
			{/if}
		</div>
		<hr class="mt-0 mb-4" />
		<div class="flex justify-between items-center gap-4">
			<Button onclick={handleClose} variant="outline" class="text-lg">Cancel</Button>

			{#if reportState.reportURL}
				<Button href={reportState.reportURL} class="text-lg no-underline">
					<DownloadIcon class="size-4" />
					Download report
				</Button>
			{:else if !reportState.inProgress && reportState.error === null}
				<Button onclick={handleCreateReport} class="text-lg">Create report</Button>
			{/if}
		</div>
	</Content>
</Root>
