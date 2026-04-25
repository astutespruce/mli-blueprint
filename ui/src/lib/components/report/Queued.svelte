<script>
	import Clock from '~icons/fa-solid/clock'
	import { cn } from '$lib/utils'

	const { message, queuePosition, elapsedTime, class: className = '' } = $props()
</script>

<div class={cn('container', className)}>
	<div class="flex items-center gap-4">
		<Clock width="2rem" height="2rem" />
		<h2 class="text-2xl">
			{message || 'Waiting for other jobs to complete'}...
		</h2>
	</div>
	<p class="text-xl mt-4">
		The server is currently working on reports that have already been submitted and it will start
		working on your report as soon as possible.
		<br />
		<br />
		{queuePosition > 0
			? `Waiting on ${queuePosition} other report${queuePosition > 1 ? 's' : ''} to complete`
			: 'Your report is next in line'}
		.
		<br />
		<br />
		{elapsedTime !== null
			? `You have been waiting for ${Math.floor(elapsedTime / 60)} minutes and ${(elapsedTime - Math.floor(elapsedTime / 60) * 60).toString().padStart(2, '0')} seconds.`
			: null}
	</p>
</div>
