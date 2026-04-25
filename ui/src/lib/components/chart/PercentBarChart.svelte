<script lang="ts">
	import { Progress } from '$lib/components/ui/progress'
	import { formatPercent } from '$lib/util/format'
	import { cn } from '$lib/utils'

	const { label, percent, class: className = '' } = $props()
</script>

<div class={className}>
	<div
		class={cn('flex gap-4 justify-between flex-nowrap items-end opacity-50 leading-tight', {
			'opacity-100': percent > 0
		})}
	>
		<div class={cn('flex-auto text-grey', { 'text-foreground': percent > 0 })}>
			{label}
		</div>
		<div class="text-grey-8 flex-none text-sm">
			{formatPercent(percent)}% of area
		</div>
	</div>
	<Progress
		value={percent}
		max={100}
		class={cn('h-3 bg-grey-1 [&>div]:bg-grey-8 opacity-50', { 'opacity-100': percent > 0 })}
	/>
</div>
