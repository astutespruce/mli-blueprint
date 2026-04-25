export const formatPercent = (percent: number) => {
	if (percent === 0) {
		return '0'
	}
	if (percent < 1) {
		return '< 1'
	}
	if (percent > 99 && percent < 100) {
		return '> 99' // it looks odd to have 100% stack up next to categories with <1
	}
	if (percent > 100) {
		return 100
	}
	return Math.round(percent)
}

const decimalRegex = /\./

export const formatNumber = (number: number, decimals: number | null = null) => {
	const absNumber = Math.abs(number)
	let targetDecimals = decimals
	if (targetDecimals === null) {
		// guess number of decimals based on magnitude
		if (absNumber > 1000 || Math.round(absNumber) === absNumber) {
			targetDecimals = 0
		} else if (absNumber > 10) {
			targetDecimals = 1
		} else if (absNumber > 1) {
			targetDecimals = 2
		} else {
			targetDecimals = 3
		}
	}

	// override targetDecimals for integer values
	if (Math.round(absNumber) === absNumber) {
		targetDecimals = 0
	}

	const factor = 10 ** targetDecimals

	// format to localeString, and manually set the desired number of decimal places
	const formatted = (Math.round(number * factor) / factor).toLocaleString(undefined, {
		minimumFractionDigits: targetDecimals,
		maximumFractionDigits: targetDecimals
	})

	// trim trailing 0's and periods
	if (decimalRegex.test(formatted)) {
		return formatted.replace(/0+$/g, '').replace(/\.$/g, '')
	}

	return formatted
}
