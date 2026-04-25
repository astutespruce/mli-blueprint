import { range } from '$lib/util/data'

/**
 * Construct WebGL filter expressions to inject into fragment shader
 * because we can't do this in a loop in the shader.
 * The ranges are defined in getFilterRanges below.
 * @param {Array} encodingSchemes - array of encoding config
 * @returns GLSL code to inject into the fragment shader
 */
export const getFilterExpr = (encodingSchemes) => {
	let code = ''
	const conditions = []
	let i = 0
	encodingSchemes.forEach((layers, textureIndex) => {
		const expressions = []
		layers.forEach(({ offset, bits }) => {
			expressions.push(
				`\n((filterValues[${i}] < 0) || matchValue(valueRGB${textureIndex}, ${offset}, ${bits}, filterValues[${i}]))`
			)
			i += 1
		})

		const condition = `canRender${textureIndex}`
		conditions.push(condition)

		code += `\nbool ${condition} = (${expressions.join(' &&')});\n`
	})

	return `\n${code}\n\nbool canRender = (${conditions.join(' && ')});\n`
}

/**
 * Construct uniform of int values of encoded filter values.
 * The bit in the position of each value (after accounting for value shift) is
 * set to 1 for each active filter.
 * Value is set to -1 to ignore this indicator when filtering.
 * @param {Array} encodingSchemes - array of encoding config
 * @param {Object} filters - key:{<value>: true / false} for filters
 */
export const getFilterValues = (encodingSchemes, filters) => {
	const filterValues = []

	encodingSchemes.forEach((layers) => {
		layers.forEach(({ id, valueShift }) => {
			const activeValues = filters[id]
			if (activeValues) {
				const encodedFilterValue = parseInt(
					range(0, Math.max(...Object.keys(activeValues)) + 1 + valueShift)
						.map((i) => (activeValues[i - valueShift] ? 1 : 0))
						.reverse()
						.join(''),
					2
				)

				filterValues.push(encodedFilterValue)
			} else {
				// use -1 as a sentinel value not to filter this layer
				filterValues.push(-1)
			}
		})
	})

	return filterValues
}
