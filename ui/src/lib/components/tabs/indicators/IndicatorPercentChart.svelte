<script lang="ts">
	import { Progress } from '$lib/components/ui/progress'
	import { formatPercent } from '$lib/util/format'

	const { label, percent, percentSuffix = '' } = $props()
</script>

<div class="flex-auto">
	<div class="flex justify-between items-end text-sm">
		<div class="flex-auto">{label}</div>
		<div class="text-grey-8 ml-4 text-right grow-0 shrink-0 basis-10">
			{formatPercent(percent)}% {percentSuffix}
		</div>
	</div>
	<Progress value={percent} max={100} class="h-4 bg-grey-1 [&>div]:bg-grey-8" />
</div>
