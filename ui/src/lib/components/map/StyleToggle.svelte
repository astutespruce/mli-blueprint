<script lang="ts">
	import LightIcon from '$images/light-v9.jpg'
	import SatelliteIcon from '$images/satellite-streets-v11.jpg'
	import { Button } from '$lib/components/ui/button'

	const styles = [
		{ id: 'light-v9', label: 'Light Basemap', icon: LightIcon },
		{
			id: 'satellite-streets-v11',
			label: 'Satellite Basemap',
			icon: SatelliteIcon
		}
	]

	const { onChange } = $props()
	let index = $state(0)

	const handleToggle = () => {
		index = index === 0 ? 1 : 0
		onChange(styles[index].id)
	}

	const { label, icon } = $derived(styles[index === 0 ? 1 : 0])
</script>

<Button
	onclick={handleToggle}
	class="absolute z-1 overflow-hidden right-[10px] md:right-auto md:left-[10px] top-[14px] md:top-auto md:bottom-[40px] w-[40px] md:w-[64px] h-[40px] md:h-[64px] rounded-full border md:border-2 border-white shadow-lg shadow-grey-8 ring-1 ring-grey-4 p-0 focus-visible:ring-accent"
>
	<img src={icon} alt={label} class="w-full h-full" />
</Button>
