/* load mapbox GL to ensure token is properly initialized */

import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

import { MAPBOX_TOKEN } from '$lib/env'

mapboxgl.accessToken = MAPBOX_TOKEN

export { mapboxgl }
