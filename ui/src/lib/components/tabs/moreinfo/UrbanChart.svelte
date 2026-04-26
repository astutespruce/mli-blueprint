<script lang="ts">
	import { scaleLinear } from 'd3-scale'
	import { area, line } from 'd3-shape'

	import { Points, XAxis, YAxis } from '$lib/components/chart'
	import type { Point } from '$lib/types'
	import { extent } from '$lib/util/data'
	import { formatNumber } from '$lib/util/format'

	type Props = {
		data: Point[]
	}

	const { data }: Props = $props()

	let clientWidth: number | undefined = $state()

	const height = 200
	const margin = { left: 60, right: 10, top: 16, bottom: 50 }
	const splitIndex = 9 // split at 2021
	const colors = ['#666666', '#D90000']

	const [minX, maxX] = $derived(extent(data.map(({ x }) => x)))
	// minY is always set to 0
	const maxY = $derived(extent(data.map(({ y }: { y: number }) => y))[1])

	// project points into the drawing area
	// (note that scales are flipped here so that 0,0 is bottom left)
	const xScale = $derived(
		scaleLinear()
			.domain([minX, maxX])
			.range([0, (clientWidth || 300) - margin.right - margin.left])
			.nice()
	)

	// Y scale always starts at 0
	const yScale = $derived(
		scaleLinear()
			.domain([0, maxY])
			.range([height - margin.bottom, margin.top])
			.nice()
	)

	const points = $derived(
		data.map(({ x, y, ...rest }) => ({
			...rest,
			x: xScale(x),
			y: yScale(y),
			yLabel: `${x}: ${formatNumber(y)}`
		}))
	)

	// only show every other tick
	const xAxisTicks = $derived(
		xScale.ticks(6).map((x, i) => ({ x: xScale(x), label: i % 2 === 0 ? x : '' }))
	)

	const yAxisTicks = $derived(
		yScale.ticks(5).map((y) => ({ y: yScale(y), label: formatNumber(y) }))
	)

	// start right points at 2021
	const [leftPoints, rightPoints] = $derived([
		points.slice(0, splitIndex),
		points.slice(splitIndex - 1)
	])
</script>

<div bind:clientWidth class={`h-[${height}px] w-full`}>
	<svg viewBox={`0 0 ${clientWidth || 300} ${height}`} class="w-full overflow-visible">
		<g transform={`translate(${margin.left},${margin.top})`}>
			<!-- areas -->

			<path
				d={area()
					.x0(({ x }: Point) => x)
					.y0(yScale(0))
					.y1(({ y }: Point) => y)(leftPoints)}
				fill={colors[0]}
				fill-opacity="0.6"
			/>

			<path
				d={area()
					.x0(({ x }: Point) => x)
					.y0(yScale(0))
					.y1(({ y }: Point) => y)(rightPoints)}
				fill={colors[1]}
				fill-opacity="0.6"
			/>

			<!-- axis -->
			<g transform={`translate(0, ${height - margin.bottom})`}>
				<XAxis ticks={xAxisTicks} label="Decade" labelOffset={40} />
			</g>
			<YAxis ticks={yAxisTicks} label="Percent of area" labelOffset={48} />

			<!-- lines -->
			<path
				d={line()(leftPoints.map(({ x, y }) => [x, y]))}
				fill="none"
				stroke-width={1}
				stroke={colors[0]}
			/>
			<path
				d={line()(rightPoints.map(({ x, y }) => [x, y]))}
				fill="none"
				stroke-width={1}
				stroke={colors[1]}
			/>

			<!-- dividing line -->

			<line
				x1={xScale(2021)}
				y1={yScale(0)}
				x2={xScale(2021)}
				y2={yScale(maxY) - 22}
				class="stroke-grey-9"
			/>

			<text
				x={xScale(2021) - 6}
				y={yScale(maxY) - 12}
				text-anchor="end"
				class="fill-grey-8 text-sm"
			>
				&#x2190; Past trend
			</text>

			<text
				x={xScale(2021) + 6}
				y={yScale(maxY) - 12}
				text-anchor="start"
				class="fill-grey-8 text-sm"
			>
				Future trend &#x2192;
			</text>

			<!-- render in reverse order so that tooltips show properly with increasing trends -->
			<Points
				points={rightPoints.slice(1)}
				minX={xAxisTicks[0]}
				radius={4}
				fill={colors[1]}
				baseline={yScale(0)}
			/>
			<Points
				points={leftPoints}
				minX={xAxisTicks[0].x}
				radius={4}
				fill={colors[0]}
				baseline={yScale(0)}
			/>
		</g>
	</svg>
</div>
