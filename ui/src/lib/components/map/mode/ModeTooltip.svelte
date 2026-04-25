<script lang="ts">
	import { Provider, Root, Trigger, Content } from '$lib/components/ui/tooltip'
	import { cn } from '$lib/utils'

	const { content, children, class: className, onClick } = $props()
</script>

<Provider delayDuration={0}>
	<Root disableHoverableContent>
		<Trigger
			class={cn(
				'text-sm md:text-[1rem] py-2 px-3  first:rounded-l-md last:rounded-r-md leading-none min-w-[6em] cursor-pointer focus-visible:outline-2 outline-accent',
				className
			)}
			onclick={onClick}
		>
			{@render children()}
		</Trigger>
		<Content side="bottom" class="py-2 px-3 max-w-60 z-10000 hidden md:block">
			<p class="text-[0.9rem] leading-tight">
				{content}
			</p>
		</Content>
	</Root>
</Provider>
