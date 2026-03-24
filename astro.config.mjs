// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	site: 'https://www.sanctum.run',
	vite: {
		server: {
			allowedHosts: ['sanctum.local'],
		},
	},
	integrations: [
		starlight({
			title: 'Le Sanctum',
			tagline: 'Your haus, wittily managed.',
			logo: {
				light: './src/assets/sanctum-logo-light.svg',
				dark: './src/assets/sanctum-logo-dark.svg',
				replacesTitle: false,
			},
			social: [
				{ icon: 'x.com', label: 'Follow @LeSanctum', href: 'https://x.com/LeSanctum' },
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/Ogilthorp3' },
			],
			customCss: ['./src/styles/custom.css'],
			head: [
				{
					tag: 'link',
					attrs: {
						rel: 'preconnect',
						href: 'https://fonts.googleapis.com',
					},
				},
				{
					tag: 'link',
					attrs: {
						rel: 'preconnect',
						href: 'https://fonts.gstatic.com',
						crossorigin: '',
					},
				},
				{
					tag: 'link',
					attrs: {
						rel: 'stylesheet',
						href: 'https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,300;1,6..72,400&family=JetBrains+Mono:wght@300;400;500&display=swap',
					},
				},
			{
					tag: 'link',
					attrs: {
						rel: 'icon',
						type: 'image/svg+xml',
						href: '/favicon.svg',
					},
				},
				{
					tag: 'meta',
					attrs: {
						property: 'og:image',
						content: 'https://www.sanctum.run/og-image.svg',
					},
				},
				{
					tag: 'meta',
					attrs: {
						property: 'og:image:width',
						content: '1200',
					},
				},
				{
					tag: 'meta',
					attrs: {
						property: 'og:image:height',
						content: '630',
					},
				},
			],
			sidebar: [
				{
					label: 'Getting Started',
					items: [
						{ label: 'What is Sanctum?', slug: 'getting-started/what-is-sanctum' },
						{ label: 'Requirements', slug: 'getting-started/requirements' },
						{ label: 'Installation', slug: 'getting-started/installation' },
						{ label: 'First Run', slug: 'getting-started/first-run' },
						{ label: 'Pricing', slug: 'getting-started/pricing' },
					],
				},
				{
					label: 'Architecture',
					items: [
						{ label: 'Overview', slug: 'architecture/overview' },
						{ label: 'The Living Force', slug: 'architecture/living-force' },
						{ label: 'Sanctum Proxy', slug: 'architecture/proxy' },
						{ label: 'Config System', slug: 'architecture/config-system' },
						{ label: 'Node Topology', slug: 'architecture/node-topology' },
						{ label: 'Services', slug: 'architecture/services' },
					],
				},
				{
					label: 'Guides',
					items: [
						{ label: 'Dashboard', slug: 'guides/dashboard' },
						{ label: 'Watchdog', slug: 'guides/watchdog' },
						{ label: 'Service Graph', slug: 'guides/service-graph' },
						{ label: 'Home Assistant', slug: 'guides/home-assistant' },
						{ label: 'AI Agents', slug: 'guides/agents' },
						{ label: 'Autoresearch', slug: 'guides/autoresearch' },
						{ label: 'Skills', slug: 'guides/skills' },
						{ label: 'Satellite Setup', slug: 'guides/satellite-setup' },
						{ label: 'Memory Vault', slug: 'guides/memory-vault' },
						{ label: 'Memory Service', slug: 'guides/memory' },
						{ label: 'Health Monitoring', slug: 'guides/health-monitoring' },
					],
				},
				{
					label: 'Agents',
					items: [
						{ label: 'Tommy \u2014 Guardian Spirit', slug: 'agents/tommy' },
						{ label: 'Yoda \u2014 Main Agent', slug: 'agents/yoda' },
						{ label: 'Windu \u2014 Security', slug: 'agents/windu' },
						{ label: 'Qui-Gon \u2014 Efficiency', slug: 'agents/quigon' },
						{ label: 'Cilghal \u2014 Health', slug: 'agents/cilghal' },
						{ label: 'Mundi \u2014 Finance', slug: 'agents/mundi' },
						{ label: 'Jocasta \u2014 CRM', slug: 'agents/jocasta' },
						{ label: 'Ahsoka \u2014 Satellite', slug: 'agents/ahsoka' },
					],
				},
				{
					label: 'Reference',
					items: [
						{ label: 'instance.yaml', slug: 'reference/instance-yaml' },
						{ label: 'Shell API', slug: 'reference/shell-api' },
						{ label: 'TypeScript API', slug: 'reference/typescript-api' },
						{ label: 'LaunchAgents', slug: 'reference/launchagents' },
						{ label: 'CLI', slug: 'reference/cli' },
					],
				},
				{
					label: 'Operations',
					items: [
						{ label: 'Backup & Restore', slug: 'operations/backup-restore' },
						{ label: 'Troubleshooting', slug: 'operations/troubleshooting' },
						{ label: 'Security', slug: 'operations/security' },
						{ label: 'Tooling', slug: 'operations/tooling' },
					],
				},
			],
		}),
	],
});
