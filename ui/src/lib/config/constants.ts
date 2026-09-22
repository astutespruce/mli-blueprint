import { indexBy } from '$lib/util/data'
import type { Indicator } from '$lib/types'

import blueprint from '$constants/blueprint.json'
import indicatorGroups from '$constants/indicator_groups.json'
import rawIndicators from '$constants/indicators.json'
import protectedAreas from '$constants/protected_areas.json'
import protectedAreasPoly from '$constants/protected_areas_poly.json'
import subregions from '$constants/subregions.json'
import urban from '$constants/urban.json'
import urbanByDecade from '$constants/urban_by_decade.json'

// import pixel layers
import pixelLayers0 from '$constants/pixel_layers_0.json'
import pixelLayers1 from '$constants/pixel_layers_1.json'
import pixelLayers2 from '$constants/pixel_layers_2.json'
import pixelLayers3 from '$constants/pixel_layers_3.json'
import pixelLayers4 from '$constants/pixel_layers_4.json'

// export unmodified values directly
export {
	blueprint,
	indicatorGroups,
	protectedAreas,
	protectedAreasPoly,
	urban,
	urbanByDecade,
	pixelLayers0,
	pixelLayers1,
	pixelLayers2,
	pixelLayers3,
	pixelLayers4
}

export const indicatorGroupIndex = indexBy(indicatorGroups, 'id')

// select subset of fields and add position within list
// use the order as defined in the indicator groups
const indicatorIds: string[] = []
indicatorGroups.forEach(({ indicators: groupIndicators }) => {
	indicatorIds.push(...groupIndicators)
})
const rawIndicatorsIndex = Object.fromEntries(
	rawIndicators.map((indicator) => [indicator.id, indicator])
)

export const indicators: Indicator[] = indicatorIds.map((id, i) => {
	const indicator = rawIndicatorsIndex[id]
	return {
		...indicator,
		subregions: new Set(indicator.subregions),
		pos: i
	}
})

export const indicatorsIndex = indexBy(indicators, 'id')

export const subregionIndex = indexBy(subregions, 'value')
