import { defaultFilters } from '$lib/config/filters'
import { logGAEvent } from '$lib/util/log'
import type { Filter, Filters } from '$lib/types'

export class MapData {
	#mapMode: string = $state('unit') // one of: unit, pixel, filter
	#data: any | null = $state.raw(null) // FIXME: typing
	#selectedIndicator: any | null = $state.raw(null) // FIXME: typing
	#filters: Filters = $state.raw(defaultFilters)
	#activeFilterValues = $derived.by(() =>
		Object.fromEntries(
			Object.entries(this.#filters)
				.filter(([_, { enabled }]) => enabled)
				.map(([id, { activeValues }]) => [id, activeValues])
		)
	)
	#numEnabledFilters = $derived.by(
		() => Object.values(this.#filters).filter(({ enabled }) => enabled).length
	)
	#visibleSubregions: Set<string> = $state.raw(new Set<string>())
	#filtersLoading: boolean = $state(true) // set to false on first set of visible subregions

	get mapMode(): string {
		return this.#mapMode
	}

	set mapMode(mode: string) {
		this.#mapMode = mode
		this.#data = null
		this.#selectedIndicator = null
	}

	get data() {
		return this.#data
	}

	setData(data: any | null) {
		console.log('set map data', data)
		this.#data = data
		if (data === null) {
			this.#selectedIndicator = null
		} else if (data.type !== 'pixel') {
			logGAEvent('set-map-data', {
				type: data.type,
				id: `${data.type}:${data.id}`
			})
		}
	}

	get selectedIndicator() {
		return this.#selectedIndicator
	}

	set selectedIndicator(indicator) {
		this.#selectedIndicator = indicator

		if (indicator) {
			logGAEvent('show-indicator-details', {
				indicator
			})
		}
	}

	get filters() {
		return this.#filters
	}

	get numEnabledFilters() {
		return this.#numEnabledFilters
	}

	get hasVisibleFilters() {
		return this.#visibleSubregions.size > 0 || this.numEnabledFilters > 0
	}

	setLayerFilterValues(id: string, { enabled, activeValues }: Filter) {
		this.#filters = {
			...this.#filters,
			[id]: { enabled, activeValues }
		}
	}

	get activeFilterValues() {
		return this.#activeFilterValues
	}

	resetFilters() {
		this.#filters = defaultFilters
	}

	get filtersLoading() {
		return this.#filtersLoading
	}

	get visibleSubregions() {
		return this.#visibleSubregions
	}

	set visibleSubregions(visibleSubregions: Set<string>) {
		this.#visibleSubregions = visibleSubregions
		this.#filtersLoading = false
	}

	// for logging state
	toJSON() {
		return {
			mapMode: this.#mapMode,
			data: this.#data,
			selectedIndicator: this.#selectedIndicator,
			filters: this.#filters,
			visibleSubregions: this.#visibleSubregions
		}
	}
}
