<script lang="ts">
	import { cn } from '$lib/utils'
	import { sum } from '$lib/util/data'
	import { formatPercent } from '$lib/util/format'

	const { categories, radius = 35, lineWidth = 30, class: className = '' } = $props()

	// center x, y always at the cetner of the 100,100 domain
	const cx = 50
	const cy = 50

	const degreesToRadians = (degrees: number) => (degrees * Math.PI) / 180

	// adapted from https://github.com/derhuerst/svg-partial-circle/blob/master/index.js
	const circleSegment = (start: number, end: number) => {
		const length = end - start
		if (length === 0) {
			return []
		}

		const originX = radius * Math.cos(start) + cx
		const originY = radius * Math.sin(start) + cy
		const toX = radius * Math.cos(end) + cx
		const toY = radius * Math.sin(end) + cy
		const large = Math.abs(length) <= Math.PI ? '0' : '1'
		const sweep = length < 0 ? '0' : '1'

		return `M ${originX} ${originY} A ${radius} ${radius} 0 ${large} ${sweep} ${toX} ${toY}`
	}

	// adapted from https://github.com/toomuchdesign/react-minimal-pie-chart
	const entries = $derived.by(() => {
		const total = sum(categories.map(({ value }: { value: number }) => value))
		let prevAngle = 0
		return categories.map(({ value, ...rest }: { value: number }) => {
			const degrees = (360 * value) / total
			const startAngle = prevAngle
			prevAngle += degrees

			const path = circleSegment(
				degreesToRadians(startAngle),
				// must be < 360 degrees
				degreesToRadians(startAngle + Math.min(degrees, 359.999))
			)

			return {
				...rest,
				value,
				path
			}
		})
	})
</script>

<div class={cn('flex items-center gap-8', className)}>
	<div class="flex-auto max-w-[160px]">
		<svg viewBox="0 0 100 100" width="100%" height="100%">
			{#each entries as { path, color }}
				<path d={path} fill="none" stroke-width={lineWidth} stroke={color} />
			{/each}
		</svg>
	</div>
	<div class="min-w-[140px]">
		{#each categories as { value, label, color }}
			<div class="flex items-center gap-2 text-sm not-first:mt-2">
				<div
					class="w-5 h-5 flex-none border border-grey-2"
					style={`background-color:${color}`}
				></div>
				<div class="flex flex-wrap gap-2">
					{label}
					<div class="text-grey-8 flex-none">
						({formatPercent(value)}%)
					</div>
				</div>
			</div>
		{/each}
	</div>
</div>
