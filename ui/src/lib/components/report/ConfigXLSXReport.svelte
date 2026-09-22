<script lang="ts">
	import ReplyAllIcon from '~icons/fa-solid/reply-all'
	import { protectedAreas, protectedAreasPoly } from '$lib/config/constants'
	import { Button } from '$lib/components/ui/button'
	import SelectField from './SelectField.svelte'
	import SelectDatasets from './SelectDatasets.svelte'

	type Props = {
		count: number
		fields: Record<string, number>
		datasets: string[]
		onStartOver: () => void
		onSubmit: (field: string, datasets: string[]) => void
	}

	const { count, fields, datasets: datasetIds = [], onStartOver, onSubmit }: Props = $props()
	const availableDatasets = $derived(Object.fromEntries(datasetIds.map((id) => [id, true])))

	let selectedField = $state('')
	let selectedDatasets = $derived.by(() => {
		// have to wrap in state for deep reactivity
		let out = $state({ ...availableDatasets })
		return out
	})

	const hasDatasets = $derived(Object.values(selectedDatasets).some((v) => v))

	const handleSubmit = () => {
		const datasets = Object.entries(selectedDatasets)
			.filter(([, selected]) => selected)
			.map(([id]) => id)

		// include polygon version of protected areas if needed
		if (selectedDatasets[protectedAreas.id]) {
			datasets.push(protectedAreasPoly.id)
		}

		onSubmit($state.snapshot(selectedField), datasets)
	}
</script>

<div class="container pt-8 pb-16">
	<SelectField {count} {fields} bind:selectedField />

	<SelectDatasets {availableDatasets} bind:selectedDatasets />

	<hr />

	<div class="flex justify-between gap-8 items-center">
		<Button onclick={onStartOver} variant="destructive" class="text-xl">
			<ReplyAllIcon class="size-5" aria-hidden="true" />
			Start over
		</Button>

		<Button onclick={handleSubmit} disabled={!hasDatasets} class="text-xl">Create report</Button>
	</div>
</div>
