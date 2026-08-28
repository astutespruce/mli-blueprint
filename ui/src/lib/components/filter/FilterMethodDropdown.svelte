<script lang="ts">
	import GearIcon from '~icons/fa-solid/cog'
	import CheckIcon from '~icons/fa-solid/check'
	import { getContext } from 'svelte'
	import type { AppState } from '$lib/types'
	import { cn } from '$lib/utils'
	import type { MapState } from '$lib/components/map'
	import { Button } from '$lib/components/ui/button'
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu'
	import * as Sheet from '$lib/components/ui/sheet'
	import AndLogicIcon from '$images/AndLogicIcon.svg'
	import OrLogicIcon from '$images/OrLogicIcon.svg'

	const appState: AppState = getContext('app-state')
	const mapState: MapState = getContext('map-state')
</script>

{#if appState.isMobile}
	<Sheet.Root>
		<Sheet.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" class="hover:bg-transparent h-auto p-1!">
					<GearIcon />
					<b>Change filter overlay method</b>
				</Button>
			{/snippet}
		</Sheet.Trigger>
		<Sheet.Content side="top" class="px-4 pt-4 pb-8 h-full">
			<div class="font-bold text-xl">Filter overlay method:</div>
			<Button
				onclick={() => (mapState.filterMode = 'AND')}
				variant="ghost"
				class="h-auto text-wrap wrap-normal whitespace-normal text-left w-full justify-between"
			>
				<div class="flex items-center gap-2">
					<img src={AndLogicIcon} alt="AND logic icon" class="size-7" />
					Display only the areas where the selected filters overlap.
				</div>
				<CheckIcon
					class={cn('invisible size-4 ml-4', {
						visible: mapState.filterMode === 'AND'
					})}
				/>
			</Button>
			<Button
				onclick={() => (mapState.filterMode = 'OR')}
				variant="ghost"
				class="h-auto text-wrap wrap-normal whitespace-normal text-left w-full justify-between"
			>
				<div class="flex items-center gap-2">
					<img src={OrLogicIcon} alt="OR logic icon" class="size-7" />
					Display all areas where any of the selected filters are present.
				</div>
				<CheckIcon
					class={cn('invisible size-4 ml-4', {
						visible: mapState.filterMode === 'OR'
					})}
				/>
			</Button>
		</Sheet.Content>
	</Sheet.Root>
{:else}
	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" class="hover:bg-transparent h-auto p-1!">
					<GearIcon />
					<b>Change filter overlay method</b>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content class="w-72 text-base">
			<DropdownMenu.Group>
				<DropdownMenu.Label class="text-base">Filter overlay method:</DropdownMenu.Label>
				<DropdownMenu.Separator />
				<DropdownMenu.RadioGroup bind:value={mapState.filterMode}>
					<DropdownMenu.RadioItem value="AND" class="gap-4">
						<img src={AndLogicIcon} alt="AND logic icon" class="size-7" />
						Display only the areas where the selected filters overlap.
					</DropdownMenu.RadioItem>
					<DropdownMenu.RadioItem value="OR" class="gap-4">
						<img src={OrLogicIcon} alt="OR logic icon" class="size-7" />
						Display all areas where any of the selected filters are present.
					</DropdownMenu.RadioItem>
				</DropdownMenu.RadioGroup>
			</DropdownMenu.Group>
		</DropdownMenu.Content>
	</DropdownMenu.Root>
{/if}
