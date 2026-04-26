<script lang="ts">
	import { CONTACT_URL } from '$lib/env'
	import { cn } from '$lib/utils'

	const { class: className } = $props()
</script>

<section class={cn('py-6 pl-4 pr-8 overflow-y-auto h-full', className)}>
	<h3 class="mb-2 text-xl">Give your feedback to Blueprint staff</h3>
	<p class="text-lg leading-snug">
		The Blueprint and its inputs are regularly revised based on input from people like you. Have a
		suggestion on how to improve the priorities? Let us know! We also welcome feedback on how to
		improve the Midwest Blueprint Explorer interface. Midwest Blueprint staff will read and respond
		to your comments&mdash;we promise.
		<br />
		<br />
		Please reach out to
		<a href={CONTACT_URL}> Blueprint user support staff</a>.
	</p>

	<hr />

	<h3 class="mb-2 text-xl">Contact Blueprint staff for help using the Blueprint</h3>
	<p class="text-lg leading-snug">
		Do you have a question about the Blueprint? Would you like help using the Blueprint to support a
		proposal or inform a decision? Midwest Blueprint staff are here to support you! We really mean
		it. It is what we do!
		<br />
		<br />
		Please reach out to
		<a href={CONTACT_URL}> Blueprint user support staff</a>.
	</p>
</section>
