<script lang="ts">
	import { cn } from '#lib/utils.js'
	import { NeedHelp } from './general'
	import { ProtectedAreas, Urban } from './moreinfo'

	const {
		type,
		urban,
		protected_areas,
		protected_areas_list,
		num_protected_areas,
		class: className = ''
	} = $props()
</script>

<section class={cn('flex-auto overflow-y-auto h-full py-8 pl-4 pr-8', className)}>
	<ProtectedAreas {type} {protected_areas} {protected_areas_list} {num_protected_areas} />
	<Urban {type} {urban} />

	<NeedHelp />
</section>
