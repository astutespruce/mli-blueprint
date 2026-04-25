<script lang="ts">
	const { points, minX, baseline, radius = 4, fill } = $props()

	let activeIndex: number | null = $state(null)

	const handleMouseOver = ({
		target: {
			dataset: { index }
		}
	}) => {
		activeIndex = parseInt(index, 10)
	}

	const handleMouseOut = () => {
		activeIndex = null
	}
</script>

<g>
	<!-- render points in reverse order so that tooltips how up properly with increasing trend -->

	{#each points.slice().reverse() as { x, y, yLabel }, i}
		<g>
			<circle r={radius} cx={x} cy={y} {fill} stroke-width={0} />

			{#if activeIndex !== null && activeIndex === i}
				<line
					x1={minX}
					y1={y}
					x2={x}
					y2={y}
					stroke-width={1}
					stroke-dasharray="2 4"
					class="stroke-grey-9"
				/>
				<circle r={3} cx={minX} cy={y} fill="#666" />
				<line
					x1={x}
					y1={baseline}
					x2={x}
					y2={y}
					stroke-width={1}
					stroke-dasharray="2 4"
					class="stroke-grey-9"
				/>
				<circle r={3} cx={x} cy={baseline} fill="#666" />
			{/if}

			<circle
				role="graphics-symbol"
				r={radius * 2}
				cx={x}
				cy={y}
				fill={activeIndex !== null && activeIndex === i ? fill : 'transparent'}
				stroke="none"
				data-index={i}
				onmouseenter={handleMouseOver}
				onmouseleave={handleMouseOut}
				class="cursor-pointer"
			/>

			<!-- this has to be after everything else to be on top  -->

			{#if activeIndex !== null && activeIndex === i}
				<rect
					x={x - Math.max(yLabel.length * 10, 44) / 2}
					y={y - 32}
					width={Math.max(yLabel.length * 10, 44)}
					height={24}
					rx="6"
					fill="#f5fafe"
					stroke="#FFF"
					stroke-width={2}
				/>
				<text {x} y={y - 14} text-anchor="middle" class="text-md text-grey-9">
					{yLabel}%
				</text>
			{/if}
		</g>
	{/each}
</g>
