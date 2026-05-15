<script lang="ts">
	import { cn } from '$lib/utils'

	const { isPresent, values, currentValue, isZeroValue, valueLabel, goodThreshold } = $props()
</script>

{#if isPresent && !!valueLabel}
	<div class="text-sm text-grey-8 leading-tight text-wrap">
		{valueLabel}
	</div>
{/if}

<div
	class={cn('flex items-center mt-2 relative', {
		'mt-5': !!goodThreshold,
		'opacity-25': isZeroValue
	})}
>
	<div class="text-grey-8 font-sm flex-none">Low</div>
	<div
		class={cn('flex items-center flex-auto mx-4 border border-grey-9/40', {
			'border-grey-9/50': isPresent
		})}
	>
		<!-- always have a 0 bin -->
		{#if values[0].value > 0}
			<div
				class="relative flex-auto h-3 bg-grey-0 not-first:border-l not-first:border-l-grey-2"
			></div>
		{/if}
		{#each values as { value, percent } (value)}
			<div
				class={cn('relative flex-auto h-3 bg-grey-0 not-first:border-l not-first:border-l-grey-2', {
					'bg-grey-8': percent === 100
				})}
			>
				{#if value === goodThreshold}
					<div
						class="absolute text-grey-8 text-xs border-l border-dashed border-l-grey-9/50 w-[94px] top-[-1.2rem]"
					>
						&rarr; good condition
					</div>
				{/if}

				<!-- marker -->
				{#if percent === 100}
					<div
						class="absolute left-[50%] -ml-2 top-3.5 border-b-[0.6rem] border-b-grey-9 border-r-[0.5rem] border-r-transparent border-l-[0.5rem] border-l-transparent"
					></div>
				{/if}
			</div>
		{/each}
	</div>

	<div class="text-grey-8 font-sm flex-none">High</div>
</div>

<div class="text-grey-8 font-sm mt-4 max-w-full text-wrap">
	Value: {isPresent ? currentValue.label : 'Not present'}
</div>
