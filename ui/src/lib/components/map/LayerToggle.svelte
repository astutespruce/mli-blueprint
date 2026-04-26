<script lang="ts">
	import EyeIcon from '~icons/fa-solid/eye'
	import EyeSlashIcon from '~icons/fa-solid/eye-slash'
	import LayerGroupIcon from '~icons/fa-solid/layer-group'
	import { Root, Trigger, Content, Header, Title } from '$lib/components/ui/dialog'
	import { renderLayerGroups, renderLayersIndex } from '$lib/config/pixelLayers'
	import { logGAEvent } from '$lib/util/log'
	import { cn } from '$lib/utils'

	const { renderLayer, onSetRenderLayer, class: className = '' } = $props()

	const handleSetRenderLayer = (id: string) => () => {
		onSetRenderLayer(renderLayersIndex[id])
		logGAEvent('set-render-layer', {
			layer: id
		})
	}

	const handleKeyDown =
		(id: string) =>
		({ key }: { key: string }) => {
			if (key === 'Enter') {
				onSetRenderLayer(renderLayersIndex[id])
				logGAEvent('set-render-layer', {
					layer: id
				})
			}
		}

	const isActiveLayer = (id: string) => renderLayer?.id === id
</script>

<Root>
	<Trigger
		class={cn(
			'absolute top-[70px] md:top-[160px] right-[12px] md:right-[10px]  p-[6px] text-grey-9 bg-white cursor-pointer  pointer-events-auto rounded-sm focus-visible:outline-2 outline-accent',
			className
		)}
		style="box-shadow:0 0 0 2px #0000001a;"
		aria-label="show layers popup to choose a different layer to display on the map"
	>
		<LayerGroupIcon class="w-6 h-6 md:w-5.25 md:h-5.25" />
	</Trigger>
	<Content class="pt-4 pb-6">
		<Header class="border-b pb-4 border-b-grey-3">
			<Title class="text-3xl">Choose layer to show on map</Title>
		</Header>
		<div class="overflow-y-auto max-h-[400px]">
			{#each renderLayerGroups as { label: groupLabel, layers } (groupLabel)}
				<div class="not-first:mt-2 not-first:pt-2 not-first:border-t not-first:border-t-grey-1">
					{#if groupLabel}
						<h4 class="text-xl not-first:mt-8">{groupLabel}</h4>
					{/if}
					{#each layers as { id, label } (id)}
						<div
							class="flex items-top cursor-pointer gap-2 grey-8"
							onclick={handleSetRenderLayer(id)}
							onkeydown={handleKeyDown(id)}
							role="button"
							tabindex={0}
						>
							{#if isActiveLayer(id)}
								<EyeIcon class="text-foreground size-4 mt-1" />
							{:else}
								<EyeSlashIcon class="text-grey-8 size-4 mt-1" />
							{/if}
							<div class={cn({ 'font-bold': isActiveLayer(id) })}>{label}</div>
						</div>
					{/each}
				</div>
			{/each}
		</div>
	</Content>
</Root>
