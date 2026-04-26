<script>
	import Comments from '~icons/fa-solid/comments'
	import Envelope from '~icons/fa-solid/envelope'
	import ExclamationCircle from '~icons/fa-solid/ExclamationCircle'
	import ExternalLinkAlt from '~icons/fa-solid/external-link-alt'
	import { BLUEPRINT_URL } from '$lib/env'

	import { ContactDialog, ProvideFeedbackDialog, ReportProblemDialog } from '$lib/components/dialog'
</script>

<footer
	class="hidden md:flex flex-none gap-4 items-center justify-between py-1 px-2 leading-none text-sm"
>
	<div class="flex flex-none gap-3 items-center">
		<div>Version: Midwest Blueprint 2026</div>
		<div>|</div>
		<a href={BLUEPRINT_URL} target="_blank" class="flex gap-2 items-center">
			<ExternalLinkAlt width="1em" height="1em" />
			Blueprint webpage
		</a>
		<div>|</div>
		<div class="flex-none">
			<ContactDialog>
				<div class="flex items-center gap-2 cursor-pointer hover:underline">
					<Envelope width="1em" height="1em" />
					Contact us
				</div>
			</ContactDialog>
		</div>
		<div class="hidden lg:block">|</div>
		<div class="flex-none">
			<ReportProblemDialog>
				<div class="items-center gap-2 cursor-pointer hover:underline hidden lg:flex">
					<ExclamationCircle width="1em" height="1em" />
					Report a problem
				</div>
			</ReportProblemDialog>
		</div>
		<div class="hidden lg:block">|</div>
		<div class="flex-none">
			<ProvideFeedbackDialog>
				<div class="items-center gap-2 cursor-pointer hover:underline hidden lg:flex">
					<Comments width="1em" height="1em" />
					Provide feedback
				</div>
			</ProvideFeedbackDialog>
		</div>
		<div class="hidden lg:block">|</div>
	</div>

	<div class="text-right">
		Created by the
		<span class="hidden xl:inline-block">U.S. Fish and Wildlife Service</span>
		<span class="inline-block xl:hidden">USFWS</span>
		and <a href="https://astutespruce.com" target="_blank">Astute Spruce</a>
	</div>
</footer>

<style>
	footer {
		background-color: #1e435b;
		color: #fff;
		a {
			color: #fff;
		}
	}
</style>
