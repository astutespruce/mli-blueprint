<script lang="ts">
	import { Root, Trigger, Content, Header, Title } from '$lib/components/ui/dialog'
	import { CONTACT_URL } from '$lib/env'
	import { cn } from '$lib/utils'

	let { children, triggerClass = '' } = $props()
</script>

<Root>
	<Trigger class={cn(triggerClass)}>
		{@render children()}
	</Trigger>
	<Content class="pt-4 pb-6">
		<Header class="border-b pb-4 border-b-grey-2">
			<Title class="text-3xl">Contact us</Title>
		</Header>
		<p class="text-lg">
			Do you have a question about the blueprint? Would you like help using the blueprint to support
			a proposal or inform a decision? Midwest Landscape Initiative staff are here to support you!
			We really mean it. It is what we do!
			<br />
			<br />
			Please reach out to
			<a href={CONTACT_URL} target="_blank"> Midwest Landscape Initiative staff</a>.
		</p>
	</Content>
</Root>
