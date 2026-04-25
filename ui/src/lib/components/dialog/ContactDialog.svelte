<script lang="ts">
	import { Root, Trigger, Content, Header, Title } from '$lib/components/ui/dialog'
	import { cn } from '$lib/utils'

	let { children, triggerClass = '' } = $props()
</script>

<Root>
	<Trigger class={cn(triggerClass)}>
		{@render children()}
	</Trigger>
	<Content class="pt-4 pb-6">
		<Header class="border-b pb-4 border-b-grey-3">
			<Title class="text-3xl">Contact us</Title>
		</Header>
		<p class="text-lg">
			Do you have a question about the Blueprint? Would you like help using the Blueprint to support
			a proposal or inform a decision? Midwest Blueprint staff are here to support you! We really
			mean it. It is what we do!
			<br />
			<br />
			Please reach out to
			<a href="https://www.mlimidwest.org/support" target="_blank">
				Blueprint user support staff</a
			>.
		</p>
	</Content>
</Root>
