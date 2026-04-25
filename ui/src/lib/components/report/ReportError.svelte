<script lang="ts">
	import ExclamationTriangle from '~icons/fa-solid/exclamation-triangle'
	import { Button } from '$lib/components/ui/button'
	import { Root, Title, Description } from '$lib/components/ui/alert'
	import { CONTACT_EMAIL } from '$lib/env'
	import { cn } from '$lib/utils'

	const { error, onReset = null, class: className = '' } = $props()
</script>

<div class={cn('container', className)}>
	<Root variant="destructive" class="flex gap-4">
		<ExclamationTriangle width="2rem" height="2rem" class="flex-none" />
		<div>
			<Title class="text-2xl">Uh oh! There was an error!</Title>
			<Description class="text-xl">
				<p class="text-error">
					{#if error}
						The server says {error}
					{:else}
						Please try again. If that does not work, try a different file or <a
							href={`mailto:${CONTACT_EMAIL}`}>contact us</a
						>.
					{/if}
				</p>
			</Description>
		</div>
	</Root>

	{#if onReset}
		<div class="flex justify-center border-t border-t-grey-2 mt-8 pt-8">
			<Button onclick={onReset} class="text-xl">Try again?</Button>
		</div>
	{/if}
</div>
