<script lang="ts">
	import { getContext } from 'svelte'
	import { createQuery } from '@tanstack/svelte-query'

	import { CONTACT_EMAIL } from '$lib/env'
	import CompassIcon from '~icons/fa-solid/compass'
	import ExclamationTriangle from '~icons/fa-solid/exclamation-triangle'
	import SearchIcon from '~icons/fa-solid/Search'
	import TimesIcon from '~icons/fa-solid/Times'
	import { Button } from '$lib/components/ui/button'
	import { Input } from '$lib/components/ui/input'
	import type { LocationData } from '$lib/types'
	import { debounce } from '$lib/util/func'
	import { cn } from '$lib/utils'

	import { searchPlaces, getPlace } from './mapbox'

	let {
		ref = $bindable(null),
		isCompact = false,
		onSelect = () => {},
		onFocus = () => {}
	} = $props()
	const locationData: LocationData = getContext('location-data')

	let value = $state('')
	let index: number | null = $state(null)
	let resultsNode: Element | undefined = $state()

	// query is debounced from value
	// FIXME:
	// NOTE: we have to use a writable stores until Svelte 5 is properly supported by tanstack-query
	// let query = writable<string>('')
	// let selectedId = writable<string | null>(null)
	let query: string = $state('')
	let selectedId: string | null = $state(null)

	const suggestions = createQuery(() => ({
		queryKey: ['search', query],
		queryFn: () => (query ? searchPlaces(query) : null),
		enabled: !!query && query.length >= 3,
		staleTime: 60 * 60 * 1000 // 60 minutes
	}))

	const place = createQuery(() => ({
		queryKey: ['retrieve', selectedId],
		queryFn: () => (selectedId ? getPlace(selectedId!) : null),
		enabled: !!selectedId,
		staleTime: 60 * 60 * 1000 // 60 minutes
	}))

	$effect(() => {
		if (place.data !== null && place.data !== undefined) {
			locationData.location = place.data
			onSelect()
		}
	})

	const handleClick = (e: Event) => {
		// prevent click from calling window click handler and making unfocused
		e.stopPropagation()
	}

	const handleChange = debounce((newValue: string) => {
		index = null
		query = newValue
	}, 250)

	$effect(() => {
		handleChange(value)
	})

	$effect(() => {
		if (
			index !== null &&
			suggestions.data &&
			suggestions.data.length > 0 &&
			resultsNode &&
			resultsNode.children &&
			resultsNode.children.length >= index
		) {
			;(resultsNode.children[index] as HTMLElement).focus()
		}
	})

	const handleReset = (e: Event) => {
		e.stopPropagation()
		index = null
		value = ''
		query = ''
		locationData.location = null
	}

	const handleKeyDown = ({ key }: KeyboardEvent) => {
		if (!(suggestions.data && suggestions.data.length > 0)) {
			return
		}

		let nextIndex = 0
		if (key === 'ArrowUp' && index !== null) {
			if (index > 0) {
				nextIndex = index - 1
			} else {
				// wrap around
				nextIndex = suggestions.data.length - 1
			}
			index = nextIndex
		} else if (key === 'ArrowDown') {
			if (index !== null) {
				if (index < suggestions.data.length - 1) {
					nextIndex = index + 1
				}
				// else wrap around, handled by set = 0 above
			}
			index = nextIndex
		}
	}

	const handleResultClick = (id: string, nextIndex: number) => (e: Event) => {
		e.preventDefault()
		e.stopPropagation()
		if (id !== undefined) {
			selectedId = id
			index = nextIndex
		}
	}

	const handleResultKeyDown = (id: string, nextIndex: number) => (e: KeyboardEvent) => {
		const { key } = e
		if (key === 'Enter' && id !== undefined) {
			selectedId = id
			index = nextIndex
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div onkeydown={handleKeyDown}>
	<!-- Search field: -->
	<div class="search-input-container">
		<div class="relative group">
			<SearchIcon
				class="flex-none size-4 absolute left-1.5 top-2.5 z-1 text-grey-4 group-focus-within:text-grey-9"
			/>
			<Input
				bind:ref
				bind:value
				class={cn('relative w-full flex-auto border-grey-3 placeholder:text-grey-8 z-0 pl-7 pr-2', {
					'pr-8': query && query.length > 0
				})}
				placeholder={isCompact ? 'Find a place' : 'Find a place by name / address'}
				onclick={handleClick}
				onfocus={onFocus}
				autofocus={false}
			/>
			{#if value !== ''}
				<Button
					class="absolute right-1.5 top-2 z-1 bg-white hover:bg-white w-5 h-5 flex-none text-grey-5 hover:text-grey-9 shadow-none"
					onclick={handleReset}
				>
					<TimesIcon class="" />
				</Button>
			{/if}
		</div>
	</div>
	{#if query && query?.length >= 3}
		<div
			class={cn({
				hidden: isCompact
			})}
		>
			{#if suggestions.error || place.error}
				<div class="pl-4 pr-6 py-8 text-grey-8">
					<div class="flex items-center gap-2">
						<ExclamationTriangle class="size-6" />
						Error loading search results.
					</div>
					<div class="mt-4">
						Please try a different search term. If the error continues, please
						<a href={`mailto:${CONTACT_EMAIL}`}> let us know </a>
						.
					</div>
				</div>
			{:else if suggestions.isLoading || place.isLoading}
				<div class="flex gap-2 items-center justify-center px-4 py-8 text-grey-8">
					<CompassIcon class="animate-spin size-8 text-grey-5" />
					Loading...
				</div>
			{:else if !(suggestions.data && suggestions.data.length > 0)}
				<div class="flex items-center justify-center px-4 py-8 text-grey-8">No results found</div>
			{:else}
				<div bind:this={resultsNode} class="search-results mt-4">
					{#each suggestions.data as { id, name, address }, i}
						<div
							class="cursor-pointer leading-none bg-white hover:bg-grey-0 not-first:border-t not-first:border-t-grey-1 py-1 px-2"
							onclick={handleResultClick(id, i)}
							onkeydown={handleResultKeyDown(id, i)}
							role="button"
							tabindex={0}
						>
							<div class="text-grey-9 text-md">
								{name}
							</div>
							{#if address}
								<div class="text-grey-8 text-sm mt-1">
									{address}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>
