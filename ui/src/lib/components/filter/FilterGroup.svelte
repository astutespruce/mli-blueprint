<script lang="ts">
	import { cn } from '$lib/utils'
	import Filter from './Filter.svelte'

	const { id, icon, label, color, borderColor, entries, onChange } = $props()

	console.log('id', id)
</script>

<div class="w-full flex-none">
	<!-- header  -->
	<div
		class="py-2 px-3 border-b border-t"
		style={`background-color:${color}; border-color:${borderColor};`}
	>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<img
					src={icon}
					alt={`${label} icon`}
					class={cn('w-[2em] h-[2em] bg-white rounded-full ', {
						'border-[1.5px] border-grey-8': id !== 'priorities' && id !== 'other-info'
					})}
				/>
				<h3 class="text-lg">{label}</h3>
			</div>
		</div>
	</div>

	<!-- filters list -->
	<div class="mb-4">
		{#each entries as entry (entry.id)}
			<Filter {...entry} {onChange} />
		{:else}
			<div class="mt-4 text-grey-8 text-center">no filters available for this area</div>
		{/each}
	</div>
</div>
