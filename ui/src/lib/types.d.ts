export type IndicatorValue = {
	value: number
	label: string
	color: string | null
}

export type Indicator = {
	id: string
	label: string
	description: string
	values: IndicatorValue[]
	valueLabel: string
	captionLabel?: string | null
	goodThreshold?: number | null
	url: string
	subregions: Set<string>
	pos: number
}

export type ActiveValues = {
	[key: number]: boolean
}

export type Filter = {
	enabled: boolean
	activeValues: ActiveValues
}

type Filters = {
	[key: string]: Filter
}

export type PixelLayerBounds = {
	[key: number]: [number, number, number, number]
}

export interface PixelLayerEncoding {
	id: string
	offset: number
	bits: number
	valueShift: number
}

export type PixelLayerEncodings = {
	[key: number]: PixelLayerEncoding[]
}

interface PixelLayerIndexItem extends Omit<PixelLayerEncoding, 'id'> {
	textureIndex: number
}

export type PixelLayerIndex = {
	[key: string]: PixelLayerIndexItem
}

export type PixelLayer = {
	id: string
	label: string
	valueLabel?: string
	colors: (string | null)[]
	categories: {
		value: number
		label: string
		shortLabel?: string
		// percent: number
		// description: string
		color: string | null
	}[]
	layer: PixelLayerIndexItem
}

export type Bounds = [number, number, number, number]
export type MapConfig = {
	bounds: Bounds
	maxBounds: Bounds
	minZoom: number
	maxZoom: number
}

export type Coordinate = {
	latitude: number
	longitude: number
}

export type LocationData = {
	location: Coordinate | null
}

export type Point = {
	x: number
	y: number
}
