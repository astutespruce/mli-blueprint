<script lang="ts">
	const { ticks, label = '', labelOffset = 30 } = $props()

	const midpointY = $derived((ticks[ticks.length - 1].y - ticks[0].y) / 2 + ticks[0].y)
</script>

<g>
	<line
		x1={0}
		y1={ticks[0].y}
		x2={0}
		y2={ticks[ticks.length - 1].y}
		stroke-width={1}
		class="stroke-grey-9"
	/>

	{#if label}
		<text
			x={-labelOffset}
			y={midpointY}
			text-anchor="middle"
			transform={`rotate(-90 ${-labelOffset} ${midpointY})`}
			class="fill-grey-8 text-md"
		>
			{label}
		</text>
	{/if}

	{#each ticks as { y, label: tickLabel }}
		<g transform={`translate(-4, ${y})`}>
			<line x1={0} y1={0} x2={8} y2={0} stroke-width={1} class="stroke-grey-9" />

			<text text-anchor="end" x={-4} y={5 / 2} class="fill-grey-8">
				{tickLabel}
			</text>
		</g>
	{/each}
</g>
