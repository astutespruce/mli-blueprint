import { indexBy, range, sortByFunc } from '$lib/util/data'
import type { Filters } from '$lib/types'
import {
	blueprint,
	indicatorGroups as rawIndicatorGroups,
	indicators,
	indicatorsIndex,
	urban,
	protectedAreas
} from './constants'

// setup default filters
export const defaultFilters: Filters = Object.fromEntries(
	indicators.map(({ id, values }) => {
		const valuesIndex = indexBy(values, 'value')

		return [
			id,
			{
				enabled: false,
				activeValues: Object.fromEntries(
					range(values[0].value, values[values.length - 1].value + 1).map((v) => [
						v,
						// disable value if we don't normally show it
						valuesIndex[v] && valuesIndex[v].color !== null
					])
				)
			}
		]
	})
)

defaultFilters.blueprint = {
	enabled: false,
	// skip not a priority class; values 1-4
	activeValues: Object.fromEntries(range(1, 5).map((v) => [v, true]))
}

defaultFilters.urban = {
	enabled: false,
	// values 1-5
	activeValues: Object.fromEntries(range(1, 6).map((v) => [v, true]))
}

defaultFilters.protectedAreas = {
	enabled: false,
	// values 0-1
	activeValues: { 0: false, 1: true }
}

export const priorityFilters = [
	{
		id: 'blueprint',
		label: 'Blueprint priority',
		description:
			'The Blueprint is a basemap of priority lands and waters for conservation in the Midwest.',
		values: blueprint.slice().sort(sortByFunc('value')).slice(1, blueprint.length).reverse()
	}
]

export const indicatorGroupFilters = indexBy(
	rawIndicatorGroups.map(({ indicators: groupIndicators, ...ecosystem }) => ({
		...ecosystem,
		indicators: groupIndicators.map((id) => ({
			...indicatorsIndex[id],
			// sort indicator values in descending order
			values: indicatorsIndex[id].values.slice().reverse()
		}))
	})),
	'id'
)

export const otherInfoFilters = [
	{
		id: 'urban',
		label: 'Probability of urbanization by 2060',
		values: urban
			.slice()
			// values are not in order and need to be sorted in ascending order
			.sort(sortByFunc('value')),
		description:
			'Past and current (2021) urban levels based on developed land cover classes from the National Land Cover Database. Future urban growth estimates derived from the FUTURES model developed by the Center for Geospatial Analytics, NC State University.'
	},
	{
		id: 'protectedAreas',
		label: 'Protected areas',
		values: protectedAreas,
		description:
			'Protected areas information is derived from the Protected Areas Database of the United States (PAD-US v4.1).'
	}
]
