<script lang="ts">
	const { ticks, label = '', labelOffset = 30 } = $props()

	const midpointX = $derived((ticks[ticks.length - 1].x - ticks[0].x) / 2 + ticks[0].x)
</script>

<g>
	<line
		y1={0}
		x1={ticks[0].x}
		y2={0}
		x2={ticks[ticks.length - 1].x}
		stroke-width={1}
		class="stroke-grey-9"
	/>

	{#if label}
		<text x={midpointX} y={labelOffset} text-anchor="middle" class="fill-grey-8 text-md">
			{label}
		</text>
	{/if}

	{#each ticks as { x, label: tickLabel }}
		<g transform={`translate(${x}, -4)`}>
			<line x1={0} y1={0} x2={0} y2={8} stroke-width={1} class="stroke-grey-9" />

			<text text-anchor="middle" x={0} y={22} class="fill-grey-8 text-md">
				{tickLabel}
			</text>
		</g>
	{/each}
</g>
