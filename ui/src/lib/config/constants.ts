import { indexBy } from '$lib/util/data'
import type { Indicator } from '$lib/types'

import rawBlueprint from '$constants/blueprint.json'
import indicatorGroups from '$constants/indicator_groups.json'
import rawIndicators from '$constants/indicators.json'
import protectedAreas from '$constants/protected_areas.json'
import subregions from '$constants/subregions.json'
import urban from '$constants/urban.json'

// import pixel layers
import pixelLayers0 from '$constants/pixel_layers_0.json'
import pixelLayers1 from '$constants/pixel_layers_1.json'
import pixelLayers2 from '$constants/pixel_layers_2.json'
import pixelLayers3 from '$constants/pixel_layers_3.json'
import pixelLayers4 from '$constants/pixel_layers_4.json'

// export unmodified values directly
export {
	indicatorGroups,
	protectedAreas,
	subregions,
	urban,
	pixelLayers0,
	pixelLayers1,
	pixelLayers2,
	pixelLayers3,
	pixelLayers4
}

export const indicatorGroupIndex = indexBy(indicatorGroups, 'id')

export const subregionsIndex = indexBy(subregions, 'subregion')

// Sort by descending value
export const blueprint = rawBlueprint.sort(({ value: leftValue }, { value: rightValue }) =>
	rightValue > leftValue ? 1 : -1
)
// skip the first value
export const blueprintCategories = blueprint.slice(0, blueprint.length - 1)

// select subset of fields and add position within list
export const indicators: Indicator[] = rawIndicators.map(
	(
		{
			id,
			label,
			url,
			description,
			// goodThreshold, // this is not currently used
			values,
			valueLabel,
			subregions: indicatorSubregions
		},
		i
	) => ({
		id,
		label,
		url,
		description,
		// goodThreshold,
		values,
		valueLabel,
		subregions: new Set(indicatorSubregions),
		pos: i // position within list of indicators, used to unpack packed indicator values
	})
)

export const indicatorsIndex = indexBy(indicators, 'id')

export const subregionIndex = indexBy(subregions, 'value')
