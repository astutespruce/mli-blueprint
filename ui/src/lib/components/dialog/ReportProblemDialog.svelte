<script lang="ts">
	import { CONTACT_URL } from '$lib/env'
	import { Root, Trigger, Content, Header, Title } from '$lib/components/ui/dialog'

	let { children } = $props()
</script>

<Root>
	<Trigger>
		{@render children()}
	</Trigger>
	<Content class="pt-4 pb-6 pr-12">
		<Header class="border-b pb-4 border-b-grey-2">
			<Title class="text-3xl">Report a problem</Title>
		</Header>
		<p class="text-lg mt-2">
			Did you encounter an error while using this application? Do you see a problem with the
			blueprint priorities or indicator areas?
			<br />
			<br />
			We want to hear from you!
			<br />
			<br />
			Please contact
			<a href={CONTACT_URL} target="_blank" rel="noopener noreferrer">
				Midwest Landscape Initiative staff
			</a>
		</p>
	</Content>
</Root>
