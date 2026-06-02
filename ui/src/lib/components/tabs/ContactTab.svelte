<script lang="ts">
	import { CONTACT_URL } from '$lib/env'
	import { cn } from '$lib/utils'

	const { class: className } = $props()
</script>

<section class={cn('py-6 pl-4 pr-8 overflow-y-auto h-full', className)}>
	<h3 class="mb-2 text-xl">Contact us</h3>
	<p class="text-lg leading-snug">
		Did you encounter an error while using this application?
		<br /><br />
		Do you have a question about the blueprint?<br /><br />
		Would you like help using the blueprint to
		<a href="https://www.mlimidwest.org/support/" target="_blank"
			>support a proposal or inform a decision</a
		>?
		<br /><br />
		Midwest Landscape Initiative staff are here to support you! We really mean it. It is what we do!
		<br /><br />
		Please reach out to
		<a href={CONTACT_URL} target="_blank"> Midwest Landscape Initiative staff</a>.
	</p>
</section>
