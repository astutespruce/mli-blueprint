<script lang="ts">
	import CaretRightIcon from '~icons/fa-solid/caret-right'
	import CaretDownIcon from '~icons/fa-solid/caret-down'
	import { Button } from '$lib/components/ui/button'
	import { LatLon, Search } from '$lib/components/search'
	import { cn } from '$lib/utils'

	let placenameInputNode: HTMLInputElement | null = $state(null)
	let latLonInputNode: HTMLInputElement | null = $state(null)
	let showOptions: boolean = $state(false)
	let mode: string = $state('placename')
	let prevMode: string = $state('placename')
	let isFocused: boolean = $state(false)

	const toggleShowOptions = (e: Event) => {
		e.stopPropagation()
		showOptions = !showOptions
		isFocused = false
		mode = showOptions ? 'select-mode' : prevMode
	}

	const handlePlacenameSelect = () => {
		isFocused = false
	}

	const handlePlacenameFocus = () => {
		showOptions = false
		isFocused = true
	}

	const handleLatLonFocus = () => {
		showOptions = false
		isFocused = true
	}

	const setPlacenameMode = (e: Event) => {
		e.stopPropagation()
		placenameInputNode?.focus()

		mode = 'placename'
		prevMode = mode
		showOptions = false
		isFocused = true
	}

	const setLatLonMode = (e: Event) => {
		e.stopPropagation()
		latLonInputNode?.focus()

		mode = 'latlon'
		prevMode = mode
		showOptions = false
		isFocused = true
	}

	const handleWindowClick = () => {
		showOptions = false
		isFocused = false
		mode = prevMode
	}

	$effect(() => {
		if (!isFocused) {
			return
		}

		if (mode === 'placename') {
			placenameInputNode?.focus()
		} else if (mode === 'latlon') {
			latLonInputNode?.focus()
		}
	})
</script>

<svelte:document
	onclick={() => {
		handleWindowClick()
	}}
/>

<div
	class={cn(
		'hidden md:block absolute p-[6px] text-grey-9 bg-white pointer-events-auto rounded-lg border-2 border-grey-2 shadow-md shadow-grey-9/50 user-select-none z-2 top-0 right-0 w-[150px]',
		{
			'w-[290px]': isFocused || showOptions
		}
	)}
>
	<div class="flex gap-1 items-start">
		<Button
			aria-label="toggle search options"
			class="flex-none text-grey-8 bg-white p-0 w-3 h-8 border-none shadow-none hover:bg-white"
			onclick={toggleShowOptions}
		>
			{#if showOptions}
				<CaretDownIcon class="size-7 mt-1" />
			{:else}
				<CaretRightIcon class="size-7 mt-1" />
			{/if}
		</Button>
		<div class="flex-auto">
			{#if mode === 'placename'}
				<div class="[&_.search-results]:-ml-7">
					<Search
						bind:ref={placenameInputNode}
						isCompact={!isFocused}
						onFocus={handlePlacenameFocus}
						onSelect={handlePlacenameSelect}
					/>
				</div>
			{:else if mode === 'latlon'}
				<LatLon bind:ref={latLonInputNode} isCompact={!isFocused} onFocus={handleLatLonFocus} />
			{:else}
				<Button
					class="flex-none text-md mt-0.5 text-grey-8 bg-white p-0 h-8 border-none shadow-none hover:bg-white"
					onclick={toggleShowOptions}>Select one of the following:</Button
				>
			{/if}
		</div>
	</div>

	{#if showOptions}
		<div class="mt-1 pt-1 border-t border-t-grey-2 leading-none">
			<Button
				onclick={setPlacenameMode}
				class="text-md bg-white hover:bg-grey-0 text-foreground h-8 w-full shadow-none justify-start"
			>
				Find by a name or address
			</Button>
			<Button
				onclick={setLatLonMode}
				class="text-md bg-white hover:bg-grey-0 text-foreground h-8 w-full shadow-none justify-start mt-[2px]"
				>Find by latitude & longitude</Button
			>
		</div>
	{/if}
</div>
