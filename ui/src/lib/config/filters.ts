import { indexBy, range } from '$lib/util/data'
import type { Filters } from '$lib/types'
import {
	blueprint,
	indicators,
	indicatorGroups,
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

defaultFilters[blueprint.id] = {
	enabled: false,
	// skip not a priority class; values 1-4
	activeValues: Object.fromEntries(range(1, 5).map((v) => [v, true]))
}

defaultFilters[urban.id] = {
	enabled: false,
	// values 1-5
	activeValues: Object.fromEntries(range(1, 6).map((v) => [v, true]))
}

defaultFilters[protectedAreas.id] = {
	enabled: false,
	// values 0-1
	activeValues: { 0: false, 1: true }
}

export const priorityFilters = [
	{
		id: blueprint.id,
		label: blueprint.label,
		description: blueprint.description,
		values: blueprint.values.filter(({ value }) => value > 0).reverse()
	}
]

export const indicatorGroupFilters = Object.fromEntries(
	indicatorGroups.map(({ indicators: groupIndicators, ...group }) => [
		group.id,
		{
			...group,
			indicators: groupIndicators.map((id) => ({
				...indicatorsIndex[id],
				// sort indicator values in descending order
				values: indicatorsIndex[id].values.slice().reverse()
			}))
		}
	])
)
export const otherInfoFilters = [
	{
		id: urban.id,
		label: urban.label,
		values: urban.values,
		description: urban.description
	},
	{
		id: protectedAreas.id,
		label: protectedAreas.label,
		values: protectedAreas.values,
		description: protectedAreas.description
	}
]
export const allFilters = []
	// @ts-expect-error priorityFilters are fine
	.concat(priorityFilters)
	// @ts-expect-error indicatorGroupFilters are fine
	.concat(indicatorGroupFilters.l.indicators)
	// @ts-expect-error indicatorGroupFilters are fine
	.concat(indicatorGroupFilters.w.indicators)
	// @ts-expect-error indicatorGroupFilters are fine
	.concat(indicatorGroupFilters.h.indicators)
	// @ts-expect-error otherFilters are fine
	.concat(otherInfoFilters)

export const filterToIndex = Object.fromEntries(allFilters.map(({ id }, index) => [id, index]))
