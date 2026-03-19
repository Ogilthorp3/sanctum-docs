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
			title: 'Sanctum',
			tagline: 'Your home, intelligently managed.',
			logo: {
				light: './src/assets/sanctum-logo-light.svg',
				dark: './src/assets/sanctum-logo-dark.svg',
				replacesTitle: false,
			},
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/Ogilthorp3' },
			],
			customCss: ['./src/styles/custom.css'],
			head: [
				{
					tag: 'link',
					attrs: {
						rel: 'preconnect',
						href: 'https://rsms.me/',
					},
				},
				{
					tag: 'link',
					attrs: {
						rel: 'stylesheet',
						href: 'https://rsms.me/inter/inter.css',
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
					],
				},
				{
					label: 'Architecture',
					items: [
						{ label: 'Overview', slug: 'architecture/overview' },
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
						{ label: 'Home Assistant', slug: 'guides/home-assistant' },
						{ label: 'AI Agents', slug: 'guides/agents' },
						{ label: 'Skills', slug: 'guides/skills' },
						{ label: 'Satellite Setup', slug: 'guides/satellite-setup' },
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
					],
				},
			],
		}),
	],
});
