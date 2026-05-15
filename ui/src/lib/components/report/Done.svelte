<script lang="ts">
	import CheckCircle from '~icons/fa-solid/check-circle'
	import Download from '~icons/fa-solid/download'
	import ExclamationTriangle from '~icons/fa-solid/exclamation-triangle'
	import { Root, Description } from '$lib/components/ui/alert'
	import { Button } from '$lib/components/ui/button'
	import { CONTACT_URL } from '$lib/env'
	import { cn } from '$lib/utils'

	const { reportURL = null, errors, onReset = null, class: className = '' } = $props()
</script>

<div class={cn('container', className)}>
	<h3 class="flex items-center gap-4 text-3xl">
		<CheckCircle width="2rem" height="2rem" class="text-ok" />

		All done!
	</h3>

	{#if errors && errors.length > 0}
		<Root variant="destructive" class="border-error mt-4 flex gap-4 mb-12 max-w-200">
			<ExclamationTriangle width="1.5rem" height="1.5rem" class="flex-none" />

			<Description class="text-lg text-error">
				<p>
					Unfortunately, the server had an unexpected error creating your report. It was able to
					create most of your report, but some sections may be missing. The server says:
				</p>
				<ul>
					{#each errors as error (error)}
						<li>{error}</li>
					{/each}
				</ul>
				<p class="mt-4">
					Please try again. If that does not work, please <a href={CONTACT_URL} target="_blank"
						>contact us</a
					>.
				</p>
			</Description>
		</Root>
	{/if}

	{#if reportURL !== null}
		<p class="mt-12 text-xl">
			Your report should download automatically. You can also click the link below to download your
			report.
		</p>
		<div class="mt-8">
			<a href={reportURL} target="_blank">
				<div class="flex gap-4 items-center text-xl">
					<Download width="1rem" height="1rem" />

					Download report
				</div>
			</a>
		</div>
	{/if}

	{#if onReset}
		<hr />

		<div class="flex justify-center">
			<Button onclick={onReset} class="text-xl">Create another report?</Button>
		</div>
	{/if}
</div>
