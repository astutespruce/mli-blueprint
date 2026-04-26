<script lang="ts">
	import { cn } from '$lib/utils'

	import { ProtectedAreas, Urban } from './moreinfo'
	import { NeedHelp } from './general'

	const {
		type,
		urban,
		protectedAreas,
		protectedAreasList,
		numProtectedAreas,
		class: className = ''
	} = $props()
</script>

<section class={cn('flex-auto overflow-y-auto h-full py-8 pl-4 pr-8', className)}>
	<ProtectedAreas {type} {protectedAreas} {protectedAreasList} {numProtectedAreas} />
	<Urban {type} {urban} />

	<NeedHelp />
</section>
