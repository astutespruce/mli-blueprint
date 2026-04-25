<script lang="ts">
	import Filter from './Filter.svelte'

	const { icon, label, color, borderColor, entries, onChange } = $props()
</script>

<div class="w-full flex-none">
	<!-- header  -->
	<div
		class="py-2 px-3 border-b border-t"
		style={`background-color:${color}; border-color:${borderColor};`}
	>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<img src={icon} alt={`${label} icon`} class="w-[2em] h-[2em] bg-white rounded-full" />
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
