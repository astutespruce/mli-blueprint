<script lang="ts">
	import DownloadIcon from '~icons/fa-solid/download'
	import { createSummaryUnitReport } from '$lib/api'
	import { API_HOST } from '$lib/env'
	import { Root, Trigger, Close, Content, Footer, Header, Title } from '$lib/components/ui/dialog'
	import { Button } from '$lib/components/ui/button'
	import { captureException, logGAEvent } from '$lib/util/log'
	import Done from './Done.svelte'
	import Progress from './Progress.svelte'
	import Queued from './Queued.svelte'
	import Error from './Error.svelte'
	import type { SummaryUnitReportState, ReportJobResult, ProgressCallbackParams } from './types'

	let open: boolean = $state(false)

	const initState: SummaryUnitReportState = {
		status: 'not_started',
		progress: 0,
		queuePosition: 0,
		elapsedTime: null,
		message: null,
		result: null,
		errors: null // non-fatal errors reported to user
	}

	const { id, type } = $props()

	let reportState: SummaryUnitReportState = $state(initState)

	const handleModelOpenChange = () => {
		if (!open) {
			reportState = { ...initState }
		}
	}

	const handleClose = () => {
		// TODO: cancel report on server
		open = false
		reportState = { ...initState }
	}

	const handleCreateReport = async () => {
		reportState = {
			...initState,
			status: 'in_progress'
		}

		logGAEvent('create-summary-report', { type, id: `${type}:${id}` })

		try {
			const {
				status: jobStatus,
				result: jobResult,
				message: jobErrorMessage,
				errors: jobErrors
			}: ReportJobResult = await createSummaryUnitReport(
				id,
				type,
				({
					status: nextStatus,
					progress: nextProgress,
					queuePosition: nextQueuePosition,
					elapsedTime: nextElapsedTime,
					message: nextMessage = reportState.message,
					errors: nextErrors = reportState.errors
				}: ProgressCallbackParams) => {
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

			if (jobStatus === 'failed') {
				console.error(jobErrorMessage)

				reportState = {
					...initState,
					status: 'failed',
					message: jobErrorMessage
				}

				logGAEvent('summary-unit-report-error')

				return
			}

			// upload and processing completed successfully
			reportState = {
				...initState,
				status: 'success',
				progress: 100,
				result: jobResult,
				errors: jobErrors
			}

			window.location.href = `${API_HOST}/api${jobResult}` as string
		} catch (ex) {
			captureException(`Create summary report for ${id} (${type}) failed`, ex)
			console.error('Caught unhandled error from createSummaryUnitReport', ex)

			reportState = {
				...initState,
				status: 'failed'
				// NOTE: no meaningful error to show to user
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
	<Content class="pt-4 pb-6">
		<Header class="border-b pb-2 mb-2 border-b-grey-2">
			<Title class="text-3xl">Blueprint Summary Report</Title>
		</Header>
		{#if reportState.status === 'failed'}
			<Error message={reportState.message} />
		{:else if reportState.status === 'queued'}
			<Queued
				message={reportState.message}
				queuePosition={reportState.queuePosition}
				elapsedTime={reportState.elapsedTime}
			/>
		{:else if reportState.status === 'in_progress'}
			<Progress message={reportState.message} progress={reportState.progress} />
		{:else if reportState.status === 'success'}
			<Done errors={reportState.errors} />
			<p class="text-lg">You can also click the button below to download your report.</p>
		{:else}
			<p class="text-xl">
				Create and download a Blueprint summary report for this area. This detailed report includes
				maps and analysis of the Blueprint priorities and each indicator present in this area, as
				well as potential threats and protected areas.
			</p>
			<p class="text-md mt-2">
				Note: we have made every possible effort to ensure that the information provided in this
				viewer is accessible to people with disabilities. If you cannot fully access the
				information, please reach out to
				<a href="http://secassoutheast.org/staff" target="_blank"> Blueprint user support staff </a>
				so that we can provide the information in an alternate format.
			</p>
		{/if}

		<Footer class="gap-4 border-t border-t-grey-2 pt-2 mt-2">
			<Close onclick={handleClose} class="text-lg cursor-pointer">Cancel</Close>

			{#if reportState.status === 'success'}
				<Button href={`${API_HOST}/api${reportState.result}`} class="text-lg no-underline">
					<DownloadIcon class="size-4" />
					Download report
				</Button>
			{:else if reportState.status === 'not_started'}
				<Button onclick={handleCreateReport} class="text-lg">Create report</Button>
			{/if}
		</Footer>
	</Content>
</Root>
