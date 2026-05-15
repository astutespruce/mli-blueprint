<script lang="ts">
	import { CONTACT_EMAIL } from '$lib/env'
	import { Root, Trigger, Content, Header, Title } from '$lib/components/ui/dialog'

	let { children } = $props()
</script>

<Root>
	<Trigger>
		{@render children()}
	</Trigger>
	<Content class="pt-4 pb-6">
		<Header class="border-b pb-4 border-b-grey-2">
			<Title class="text-3xl">Report a problem</Title>
		</Header>
		<p class="text-lg">
			Did you encounter an error while using this application? Do you see a problem with the
			Blueprint priorities or indicator areas?
			<br />
			<br />
			We want to hear from you!
			<br />
			<br />
			<b>email</b>:
			<a
				href={`mailto:${CONTACT_EMAIL}?subject=Midwest Blueprint Explorer Support - report a problem`}
				target="_blank"
				rel="noopener noreferrer"
			>
				{CONTACT_EMAIL}
			</a>
		</p>
	</Content>
</Root>
