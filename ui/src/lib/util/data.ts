/**
 * Flatten an array of arrays (2D) to an array (1D)
 * @param {Array} records
 */
export const flatten = (records: [[]]) =>
	records.reduce((prev, record) => {
		prev.push(...record)
		return prev
	}, [])

/**
 * Convert an array to an object, indexing on values of field
 * @param {Array} records
 * @param {String} field
 */
export const indexBy = (records: { [key: string]: any }, field: string) =>
	records.reduce(
		(prev: {}, record: { [key: string]: any }) => Object.assign(prev, { [record[field]]: record }),
		{}
	)

/**
 * Resolve a dot notation key into an object into its final value.
 * Example: resolveKey({foo: {bar: 'baz'}}, 'foo.bar') => 'baz'
 * @param {Object} item
 * @param {String} key
 */
export const resolveKey = (item: { [key: string]: {} }, key: string): any => {
	const [cur, remainder] = key.split('.', 2)
	if (remainder !== undefined) {
		return resolveKey(item[cur], remainder)
	}
	return item[cur]
}

/**
 * Groups array into an object, keyed by value of `field`.
 * Returns an object
 *
 * @param {Array } data
 * @param {String} groupField - name of group field to group by
 */
export const groupBy = (data: [{ [key: string]: any }], groupField: string) =>
	data.reduce((prev, d) => {
		const key = resolveKey(d, groupField)
		prev[key] = (prev[key] || []).concat([d])
		return prev
	}, {})

/**
 * Calculate the sum of an array of numbers
 * @param {Array} values - array of numbers
 */
export const sum = (values: number[]) => values.reduce((prev, value) => prev + value, 0)

/** Generate an array of values between [min, max)
 * range(10) => [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
 * range(1, 10) => [1, 2, 3, 4, 5, 6, 7, 8, 9]
 *
 * @param {min} - max value if starting from 0 and max is null, or min value if max is provided
 * @param {max} - max value, optional
 */
export const range = (min: number, max: number | null = null) =>
	max !== null ? Array.from(Array(max - min), (_, i) => i + min) : [...Array(min).keys()]

/**
 * Calculate the min and max values for an array of numbers
 * @param {Array} values
 */
export const extent = (values: number[]) => [Math.min(...values), Math.max(...values)]

/**
 * Create a sort function that can be used as input to .sort()
 * @param {String} field - field to sort on
 * @param {bool} ascending
 */
export const sortByFunc =
	(field: string, ascending: boolean = true) =>
	(a: { [key: string]: any }, b: { [key: string]: any }) => {
		if (a[field] < b[field]) {
			return ascending ? -1 : 1
		}
		if (a[field] > b[field]) {
			return ascending ? 1 : -1
		}
		return 0
	}

/**
 * Recursively compare a to b using fields
 * @param {*} a
 * @param {*} b
 * @param {Array} fields - array of objects: {field, ascending}
 */
const recursiveCompare = (
	a: { [key: string]: any },
	b: { [key: string]: any },
	[{ field, ascending }, ...fields]: { field: string; ascending: boolean }[]
) => {
	if (a[field] < b[field]) {
		return ascending ? -1 : 1
	}
	if (a[field] > b[field]) {
		return ascending ? 1 : -1
	}

	// this field is equal, recurse
	if (fields.length > 0) {
		return recursiveCompare(a, b, fields)
	}

	// no more fields, they are equal
	return 0
}

/**
 * Sort by multiple fields
 * For each field that is equal, will recurse into testing the next field
 * @param {Array} fields - array of objects: {field, ascending}
 */
export const sortByFuncMultiple =
	(fields: { field: string; ascending: boolean }[]) =>
	(a: { [key: string]: any }, b: { [key: string]: any }) =>
		recursiveCompare(a, b, fields)

export const applyFactor = (values: number[], factor: number) => {
	if (!values) return values

	return values.map((v) => v * factor)
}

/**
 * Calculate the average bin based on using percents vs total percent as weights
 * and bin index as value.
 * @param {*} percents
 */
export const percentsToAvg = (percents: number[]) => {
	const total = sum(percents)
	return sum(percents.map((p, i) => i * (p / total)))
}

const numericRegex = /\d+/
const nonNumericRegex = /[^0-9|]/

/**
 * Parse a pipe-delimited string of integers,strings, or blanks into an array of values.
 * Blanks are assumed to be 0.
 * "498||405|90|7" => [498, 0, 405, 90, 7]
 * "foo|bar" => ["foo", "bar"]
 * @param {String} text
 */
export const parsePipeEncodedValues = (text: string) => {
	if (!text) return null

	const parts = text.split('|')

	if (nonNumericRegex.test(text)) {
		return parts
	}

	return parts.map((d) => parseInt(d, 10) || 0)
}

/**
 * Parse delta-encoded string of integers or blanks into an array of values.
 * First value is always the baseline.  If delta values are absent, this assumes
 * there is no change.
 * "66^23^13^7^15^10^9" => [66, 89, 102, 109, 124, 134, 143]
 *
 * @param {String} text
 */
export const parseDeltaEncodedValues = (text: string) => {
	if (!text) return null

	const [baseline, ...deltas] = text.split('^').map((d) => parseInt(d, 10) || 0)

	const values = [baseline, ...Array(deltas.length)]
	for (let i = 1; i < values.length; i += 1) {
		values[i] = values[i - 1] + deltas[i - 1]
	}

	return values
}

/**
 * Parse dictionary encoded values to object.  Values may be pipe encoded.
 * Numeric values are parsed to floats.
 * "0:|437|||,1:|438|||" => {0: [0, 437, 0, 0, 0], 1: [0, 438, 0, 0, 0]}
 * @param {String} text
 */
export const parseDictEncodedValues = (text: string) => {
	if (!text) return null

	// if any of the values are pipe encoded assume they all are
	const alwaysArray = text.indexOf('|') !== -1

	return text
		.split(',')
		.map((d) => d.split(':'))
		.map(([k, v]) => {
			if ((v !== null && v !== undefined && v.indexOf('|') !== -1) || alwaysArray) {
				return [k, parsePipeEncodedValues(v)]
			}

			if (numericRegex.test(v)) {
				return [k, parseFloat(v)]
			}

			return [k, v]
		})
		.reduce((prev, [k, v]) => {
			prev[k] = v
			return prev
		}, {})
}

export const ifNull = (value: any, defaultValue: any) => (value === null ? defaultValue : value)

/**
 * Count number of entries for each value
 * @param {Array} a - array of values
 * @returns Object - {key:count, ...}
 */
export const histogram = (a: any[]) =>
	a.reduce((prev, cur) => Object.assign(prev, { [cur]: (prev[cur] || 0) + 1 }), {})

/**
 * Return the set intersection of two sets
 * @param {Set} a
 * @param {Set} b
 * @returns Set
 */
export const setIntersection = (a: Set<any>, b: Set<any>) =>
	a.size === 0 || b.size === 0 ? new Set() : new Set([...a].filter((v) => b.has(v)))
