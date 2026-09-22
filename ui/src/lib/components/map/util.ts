import type { Map, LngLatLike } from 'mapbox-gl/esm'

// store map center / zoom in URL
export const serializeMapCenterZoomToURL = (map: Map) => {
	const mapCenter = map
		.getCenter()
		.toArray()
		.map((d) => Math.round(d * 1e5) / 1e5)
		.toString()
	const mapZoom = Math.round(map.getZoom() * 1e2) / 1e2
	window.location.hash = `${mapCenter}@${mapZoom}`
}

export const deserializeMapCenterZoomFromURL = () => {
	if (window.location.hash && window.location.hash.search('@') !== -1) {
		// use URL hash to determine cetner
		const [centerStr, zoomStr] = window.location.hash.slice(1).split('@')
		const center = centerStr.split(',').map((d) => parseFloat(d)) as LngLatLike
		const zoom = parseFloat(zoomStr)

		return { center, zoom }
	}

	return {}
}
