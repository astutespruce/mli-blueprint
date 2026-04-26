<script lang="ts">
	import { getContext } from 'svelte'

	import CheckIcon from '~icons/fa-solid/check'
	import type { MapData } from '$lib/components/map'
	import { Button } from '$lib/components/ui/button'
	import { cn } from '$lib/utils'

	const { indicator } = $props()

	const mapData: MapData = getContext('map-data')
</script>

<div
	class={cn('not-first:border-t-2 not-first:border-t-grey-1 p-1 w-full', {
		'hover:bg-grey-0': indicator.total > 0
	})}
>
	<Button
		class={cn(
			'shadow-none bg-transparent hover:bg-transparent flex gap-2 items-start justify-between py-1 px-0 text-grey-8 text-lg cursor-default w-full rounded-none text-wrap whitespace-break-spaces text-left h-auto leading-tight',
			{
				'text-primary cursor-pointer': indicator.total > 0
			}
		)}
		onclick={indicator.total > 0 ? () => (mapData.selectedIndicator = indicator.id) : () => {}}
	>
		{indicator.label}

		<CheckIcon class={cn('size-4 flex-none mt-1.5 invisible', { visible: indicator.total > 0 })} />
	</Button>
</div>
