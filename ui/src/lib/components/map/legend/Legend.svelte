<script lang="ts">
	import EyeIcon from '~icons/fa-solid/eye'
	import EyeSlashIcon from '~icons/fa-solid/eye-slash'
	import { Button } from '$lib/components/ui/button'

	import LegendElement from './LegendElement.svelte'

	const { title, subtitle, categories, isVisible, onToggleLayerVisibility } = $props()

	let isOpen = $state(true)

	const toggleVisibility = () => {
		isOpen = !isOpen
	}

	const handleKeyDown = ({ target: { role }, key }: { target: { role: string }; key: string }) => {
		if (key === 'Enter' && role === 'button') {
			toggleVisibility()
		}
	}

	const toggleLayerVisibility = (e: Event) => {
		onToggleLayerVisibility()
		e.stopPropagation()
	}
</script>

<div
	class="absolute z-1 text-grey-9 bg-white cursor-pointer bottom-10 lg:bottom-6 right-2.5 border border-grey-9/50 rounded-sm shadow-md shadow-grey-9/75 max-w-52.5 select-none hidden md:block focus-visible:outline-2 outline-accent"
	onclick={toggleVisibility}
	onkeydown={handleKeyDown}
	role="button"
	tabindex={0}
>
	{#if isOpen}
		<div class="p-2" title="Click to hide legend">
			<div class="flex items-center justify-between gap-4">
				<div class="flex-auto font-bold leading-none text-base">
					{title}
				</div>
				<Button
					class="flex-none bg-grey-0 text-foreground border border-grey-9/50 hover:border-grey-9 rounded-sm p-0 leading-none hover:bg-grey-1 w-7 h-7"
					title={`Click to ${isVisible ? 'hide' : 'show'}`}
					onclick={toggleLayerVisibility}
					tabindex={0}
				>
					{#if isVisible}
						<EyeIcon class="size-5" />
					{:else}
						<EyeSlashIcon class="size-5" />
					{/if}
				</Button>
			</div>

			{#if subtitle}
				<div class="font-normal text-grey-8 leading-none text-[15px] mt-1 mb-3">
					{subtitle}
				</div>
			{/if}

			<div class="mt-2">
				{#each categories as element (`${element.label}-${element.color}`)}
					<LegendElement {...element} />
				{/each}
			</div>
		</div>
	{:else}
		<div class="py-1 px-2" title="Click to show legend">Show Legend</div>
	{/if}
</div>
