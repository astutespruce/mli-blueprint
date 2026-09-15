<script lang="ts">
	import { CONTACT_URL } from '$lib/env'
	import * as Select from '$lib/components/ui/select'

	type Props = {
		count: number
		fields: Record<string, number>
		selectedField: string
	}

	let { count, fields, selectedField = $bindable('') }: Props = $props()

	const options: { value: string; label: string; count?: number }[] = $derived(
		[{ value: '', label: '-- Group everything together --' }].concat(
			Object.entries(fields)
				.map(([value, count]) => ({
					value,
					label: value,
					count
				}))
				.sort(({ value: left }, { value: right }) => (left < right ? -1 : 1))
		)
	)
</script>

{#if count > 1 || true}
	<div class="sm:flex gap-4">
		<div class="text-2xl font-bold">
			Choose attribute that identifies analysis units (optional):
		</div>
		<Select.Root type="single" bind:value={selectedField}>
			<Select.Trigger class="text-base">
				{options.find(({ value: optionValue }) => optionValue === selectedField)?.label}
			</Select.Trigger>
			<Select.Content align="start">
				{#each options as option (option.value)}
					<Select.Item
						value={option.value}
						class="cursor-pointer text-base data-highlighted:bg-blue-2/50! data-highlighted:text-foreground!"
					>
						{option.label}
						{#if option.count !== undefined}
							<span class="text-sm text-muted-foreground">
								({option.count} unique {option.count === 1 ? 'value' : 'values'})
							</span>
						{/if}
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>
	{#if options.length <= 1}
		<div class="text-grey-8">
			We did not find any attributes that appear to identify unique analysis units in this dataset
			(limited to text or integer fields). All areas will be grouped together for analysis. If there
			is an attribute present in your dataset that we did not detect, please
			<a href={CONTACT_URL} target="_blank">let us know</a>.
		</div>
	{:else}
		<p class="mt-4">
			Choose the attribute in your dataset that uniquely identifies your analysis units. The value
			of this attribute will be used for aggregating the results in your report. You can choose to
			group everything together to combine all analysis units into a single area for analysis. If
			there is an attribute present in your dataset that we did not detect, please
			<a href={CONTACT_URL} target="_blank">let us know</a>.
		</p>
	{/if}

	<hr class="my-8" />
{/if}
