<script lang="ts">
	import ExclamationTriangle from '~icons/fa-solid/exclamation-triangle'
	import FilterIcon from '~icons/fa-solid/filter'
	import Plus from '~icons/fa-solid/plus'
	import { Checkbox } from '$lib/components/ui/checkbox'
	import { Label } from '$lib/components/ui/label'
	import { InfoTooltip } from '$lib/components/tooltip'
	import { cn } from '$lib/utils'

	import { logGAEvent } from '$lib/util/log'

	const {
		id,
		label,
		description,
		values,
		valueLabel: indicatorValueLabel,
		enabled,
		activeValues,
		canBeVisible,
		onChange
	} = $props()

	let checkboxNode: HTMLElement | null = $state(null)

	const handleFilterToggle = () => {
		const isNowEnabled = !enabled
		onChange({ id, enabled: isNowEnabled, activeValues })

		if (isNowEnabled) {
			logGAEvent('enable-filter', { filter: id })
		}

		// blur on uncheck
		if (checkboxNode && enabled) {
			checkboxNode.blur()
		}
	}

	const handleToggleValue = (value: number) => () => {
		const newActiveValues = {
			...activeValues,
			[value]: !activeValues[value]
		}
		logGAEvent('set-filter-values', {
			filter: id,
			values: `${id}:${Object.entries(newActiveValues)
				.filter(([_, v]) => v)
				.map(([k]) => k.toString())
				.join(',')}`
		})

		onChange({ id, enabled, activeValues: newActiveValues })
	}

	const handleKeyDown = ({ key }: { key: string }) => {
		if (key === 'Enter' || key === ' ') {
			const isNowEnabled = !enabled
			onChange({ id, enabled: isNowEnabled, activeValues })

			if (isNowEnabled) {
				logGAEvent('enable-filter', { filter: id })
			}
		}
	}
</script>

<div class="pr-2 not-first:border-t-2 border-t-grey-1">
	<div class="flex justify-between items-center gap-2">
		<div
			tabindex="0"
			role="button"
			onclick={handleFilterToggle}
			onkeydown={handleKeyDown}
			class={cn(
				'label flex-auto pl-4 py-1 border-2 border-transparent cursor-pointer group hover:bg-grey-0',
				{
					'font-bold': enabled
				}
			)}
		>
			<div class="flex flex-auto items-center gap-2">
				<div class="relative">
					<FilterIcon
						class={cn('size-4 top-0 relative text-grey-9/30 group-hover:text-grey-9', {
							'text-grey-9': enabled
						})}
						aria-hidden="true"
					/>
					<Plus
						class={cn(
							'size-[0.7em] absolute top-[0.1rem] -left-2 text-grey-9/40  group-hover:text-grey-9',
							{
								hidden: enabled
							}
						)}
						aria-hidden="true"
					/>
				</div>
				{label}
			</div>
		</div>
		<InfoTooltip title={label} {description} aria-label={`Show details for ${label}`} />
	</div>

	{#if enabled}
		<div class="ml-11 mr-4 pb-2">
			{#if canBeVisible}
				{#if indicatorValueLabel}
					<div class="leading-snug mb-2">
						{indicatorValueLabel}
					</div>
				{/if}

				{#each values as { value, label: valueLabel } (value)}
					<div class="flex gap-3 not-first:mt-2">
						<Checkbox
							bind:ref={checkboxNode}
							id={`checkbox-${id}-${value}`}
							checked={activeValues[value]}
							onCheckedChange={handleToggleValue(value)}
							aria-label={`Toggle filter for ${valueLabel}`}
						/>
						<Label
							for={`checkbox-${id}-${value}`}
							class="text-md cursor-pointer leading-tight mt-[-0.1rem]"
						>
							{valueLabel}
						</Label>
					</div>
				{/each}
			{:else}
				<div class="flex gap-1 items-center justify-center text-grey-8">
					<ExclamationTriangle class="size-4" aria-hidden="true" />
					not visible in this area
				</div>
			{/if}
		</div>
	{/if}
</div>
