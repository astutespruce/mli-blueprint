<script lang="ts">
	import { Progress } from '$lib/components/ui/progress'
	import { cn } from '$lib/utils'

	const { message, progress, class: className = '' } = $props()
</script>

<div class={cn('container py-4', className)}>
	<h3 class="text-2xl">
		{#if message}
			{message}...
		{:else}
			Creating report...
		{/if}
	</h3>
	<div class="flex items-center gap-6 mt-2">
		<Progress max={100} value={progress} class="h-[1rem]" />
		<div class="text-xl">
			{progress}%
		</div>
	</div>
</div>
