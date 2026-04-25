<script lang="ts">
	import TimesCircleIcon from '~icons/fa-regular/times-circle'
	import { Button } from '$lib/components/ui/button'

	const { type, name, location, onClose } = $props()
</script>

<div
	class="bg-primary md:hidden drop-shadow-sm drop-shadow-black z-10000 py-1 px-2 flex gap-2 justify-between flex-auto items-center leading-none min-h-[2.5rem] text-white"
>
	{#if type === 'pixel'}
		<div class="flex-auto text-sm">
			Coordinates:
			<br />
			{location.latitude.toPrecision(5)}°N,
			{location.longitude.toPrecision(5)}°
		</div>
	{:else}
		<div class="flex-auto text-lg leading-none">
			{name}
			{#if type === 'subwatershed'}
				<div class="text-xs">(HUC12)</div>
			{/if}
		</div>
	{/if}

	<Button
		onclick={onClose}
		class="flex-none m-0 p-0 bg-transparent hover:bg-transparent text-white border-none shadow-none rounded-full size-6"
	>
		<TimesCircleIcon class="size-6" />
	</Button>
</div>
