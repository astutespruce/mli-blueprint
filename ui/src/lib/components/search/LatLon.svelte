<script lang="ts">
	import { getContext } from 'svelte'

	import SearchLocationIcon from '~icons/fa-solid/search-location'
	import TimesIcon from '~icons/fa-solid/times'
	import ExclamationTriangle from '~icons/fa-solid/exclamation-triangle'
	import { Button } from '$lib/components/ui/button'
	import { Input } from '$lib/components/ui/input'
	import { logGAEvent } from '$lib/util/log'
	import type { LocationData } from '$lib/types'

	let { ref = $bindable(null), isCompact, onFocus } = $props()
	const locationData: LocationData = getContext('location-data')

	let value: string = $state('')
	let hasCoordinates: boolean = $state(false)
	let isValid: boolean = $state(true)
	let invalidReason: string | null = $state(null)

	const hasCoordsRegex = /(?<lat>(\d+)[\s\w°'"\-.]*)[, ]+(?<lon>[\s\w°'"\-.]*(\d+))/g

	const parseValue = (value: string, isLatitude = false) => {
		const directionMatch = /[NSEW]/g.exec(value)
		const direction = directionMatch ? directionMatch[0] : null
		let factor = 1
		if (direction === 'S' || direction === 'W') {
			factor = -1
		}

		let decimalDegrees = null

		if (/[°'" ]/g.test(value)) {
			// drop blank parts
			const parts = value.split(/[^\d.-]+/).filter((p) => !!p)
			if (parts.length === 0) {
				return { isValid: false, invalidReason: 'Format is incorrect' }
			}
			let [degreesPart, minutesPart = '0', secondsPart = '0'] = parts
			const degrees = parseFloat(degreesPart)
			const minutes = parseFloat(minutesPart)
			const seconds = parseFloat(secondsPart)

			if (minutes < 0 || minutes > 60) {
				return {
					isValid: false,
					invalidReason: 'Minutes are out of bounds (must be 0-60)'
				}
			}

			if (seconds < 0 || seconds > 60) {
				return {
					isValid: false,
					invalidReason: 'Seconds are out of bounds (must be 0-60)'
				}
			}

			if (degrees < 0) {
				decimalDegrees = factor * (degrees - minutes / 60 - seconds / 3600)
			} else {
				decimalDegrees = factor * (degrees + minutes / 60 + seconds / 3600)
			}
		} else {
			const decimalMatch = /[\d+.*-]+/g.exec(value)
			if (decimalMatch) {
				decimalDegrees = factor * parseFloat(decimalMatch[0])
			} else {
				return {
					isValid: false,
					invalidReason: 'Format is incorrect'
				}
			}
		}

		let invalidReason = null

		let isWithinBounds = true
		if (decimalDegrees !== null) {
			if (isLatitude) {
				if (!(decimalDegrees <= 90 && decimalDegrees >= -90)) {
					isWithinBounds = false
					invalidReason = 'Latitude is out of bounds (must be -90 to 90)'
				}
			} else if (!(decimalDegrees <= 180 && decimalDegrees >= -180)) {
				isWithinBounds = false
				invalidReason = 'Longitude is out of bounds (must be -180 to 180)'
			}
		}

		return {
			decimalDegrees,
			isValid: decimalDegrees !== null && isWithinBounds,
			invalidReason
		}
	}

	const parseLatLon = (value: string) => {
		const match = hasCoordsRegex.exec(value)

		// reset so that global regex works each time
		hasCoordsRegex.lastIndex = 0

		if (match === null || match.index === -1) {
			return { isValid: false }
		}

		const { lat: rawLat, lon: rawLon } = match.groups
		if (rawLat === undefined || rawLon === undefined) {
			return {
				isValid: false
			}
		}

		const {
			decimalDegrees: lat,
			isValid: isLatValid,
			invalidReason: invalidLatReason
		} = parseValue(rawLat.trim(), true)
		const {
			decimalDegrees: lon,
			isValid: isLonValid,
			invalidReason: invalidLonReason
		} = parseValue(rawLon.trim(), false)

		return {
			lat,
			lon,
			isValid: isLatValid && isLonValid,
			invalidReason: invalidLatReason || invalidLonReason
		}
	}

	// prevent click from calling window click handler
	const handleClick = (e: Event) => {
		e.stopPropagation()
	}

	$effect(() => {
		// fires on every change to value; onchange handler does not
		hasCoordinates = value.search(hasCoordsRegex) !== -1

		isValid = true
		invalidReason = null
		if (hasCoordinates) {
			const { isValid: isValueValid = false, invalidReason: curInvalidReason = null } =
				parseLatLon(value)
			isValid = isValueValid
			invalidReason = curInvalidReason
		}
	})

	const handleSubmit = () => {
		const {
			lat,
			lon,
			isValid: isValueValid = false,
			invalidReason: nextInvalidReason = null
		} = parseLatLon(value)

		logGAEvent('search-lat-lon')

		if (isValueValid) {
			locationData.location = {
				latitude: lat!,
				longitude: lon!
			}
		} else {
			isValid = false
			invalidReason = nextInvalidReason
		}
	}

	const handleReset = (e: Event) => {
		e.stopPropagation()
		value = ''
		hasCoordinates = false
		isValid = true
		locationData.location = null
	}

	const handleInputKeyDown = (e: KeyboardEvent) => {
		const { key } = e
		if (key === 'Enter') {
			handleSubmit()
		} else if (key === 'Escape') {
			handleReset(e)
		}
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events,a11y_no_static_element_interactions -->
<div class="" onclick={handleClick}>
	<div class="flex items-center gap-2">
		<div class="relative flex-auto group">
			<SearchLocationIcon
				class="flex-none size-4 absolute left-1.5 top-2.5 z-1 text-grey-4 group-focus-within:text-grey-9"
			/>
			<Input
				bind:ref
				bind:value
				class="relative w-full flex-auto border-grey-3 placeholder:text-grey-8 z-0 pl-7 pr-8"
				placeholder="Enter latitude, longitude"
				aria-invalid={!isValid}
				onclick={handleClick}
				onkeydown={handleInputKeyDown}
				onfocus={onFocus}
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

		{#if !isCompact}
			<Button
				disabled={!(hasCoordinates && isValid)}
				variant={hasCoordinates && isValid ? 'default' : 'secondary'}
				onclick={handleSubmit}
				class="flex-none h-8 px-3 rounded-sm mr-2">Go</Button
			>
		{/if}
	</div>
	{#if !isCompact}
		<div class="mt-2 ml-[-1rem] pb-2 text-grey-8 text-sm leading-none">
			Use decimal degrees or degrees° minutes&apos; seconds&quot; in latitude, longitude order
		</div>
		{#if !isValid}
			<div class="mt-2 ml-[-1.5rem] pb-1 leading-none">
				<div class="flex items-center gap-1 text-sm">
					<ExclamationTriangle class="text-accent size-4" />
					<b>The value you entered is not valid</b>
				</div>
				{#if invalidReason}
					<div class="mt-1 text-sm">{invalidReason}</div>
				{/if}
			</div>
		{/if}
	{/if}
</div>
