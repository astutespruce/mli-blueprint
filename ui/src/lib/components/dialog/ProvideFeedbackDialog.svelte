<script lang="ts">
	import { Root, Trigger, Content, Header, Title } from '$lib/components/ui/dialog'
	import { CONTACT_URL } from '$lib/env'

	let { children } = $props()
</script>

<Root>
	<Trigger>
		{@render children()}
	</Trigger>
	<Content class="pt-4 pb-6">
		<Header class="border-b pb-4 border-b-grey-3">
			<Title class="text-3xl">Give your feedback to Blueprint Staff</Title>
		</Header>
		<p class="text-lg">
			The Blueprint and its inputs are regularly revised based on input from people like you. Have a
			suggestion on how to improve the priorities? Let us know! We also welcome feedback on how to
			improve the Midwest Blueprint Explorer interface. Midwest Blueprint staff will read and
			respond to your comments&mdash;we promise.
			<br />
			<br />
			Please reach out to
			<a href={CONTACT_URL} target="_blank"> Blueprint user support staff </a>.
		</p>
	</Content>
</Root>
