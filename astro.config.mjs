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
			disable404Route: true,
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
						{ label: 'Force Flow', slug: 'architecture/force-flow' },
						{ label: 'Jocasta MCP', slug: 'architecture/jocasta-mcp' },
						{ label: 'Sanctum Proxy', slug: 'architecture/proxy' },
						{ label: 'Smart Router', slug: 'architecture/dynamic-model-routing' },
						{ label: 'Sanctum MLX', slug: 'architecture/sanctum-mlx' },
						{ label: 'LoRA in Rust', slug: 'architecture/lora-rust' },
						{ label: 'The Carmack Optimization', slug: 'architecture/carmack-optimization' },
						{ label: 'Sanctum Olympics', slug: 'architecture/sanctum-olympics' },
						{ label: 'Model Comparison', slug: 'architecture/model-comparison' },
						{ label: 'Engineering Discipline', slug: 'architecture/engineering-discipline' },
						{ label: 'Model Tournament', slug: 'architecture/model-tournament' },
						{ label: 'Training Lessons', slug: 'architecture/training-lessons' },
						{ label: 'Config System', slug: 'architecture/config-system' },
						{ label: 'Node Topology', slug: 'architecture/node-topology' },
						{ label: 'Services', slug: 'architecture/services' },
						{ label: 'The Kitchen Loop', slug: 'architecture/kitchen-loop' },
					],
				},
				{
					label: 'Guides',
					items: [
						{ label: 'Dashboard', slug: 'guides/dashboard' },
						{ label: 'Holocron App', slug: 'guides/holocron-app' },
						{ label: 'Watchdog', slug: 'guides/watchdog' },
						{ label: 'Service Graph', slug: 'guides/service-graph' },
						{ label: 'Home Assistant', slug: 'guides/home-assistant' },
						{ label: 'AI Agents', slug: 'guides/agents' },
                                                { label: 'Agent Browser', slug: 'guides/agent-browser' },
						{ label: 'Autoresearch', slug: 'guides/autoresearch' },
						{ label: 'Gemma 4 Training', slug: 'guides/gemma4-training' },
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
						{ label: 'Yoda \u2014 Wise Mate', slug: 'agents/yoda' },
						{ label: 'Windu \u2014 Security', slug: 'agents/windu' },
						{ label: 'Qui-Gon \u2014 Efficiency', slug: 'agents/quigon' },
						{ label: 'Cilghal \u2014 Health', slug: 'agents/cilghal' },
						{ label: 'Mundi \u2014 Finance', slug: 'agents/mundi' },
						{ label: 'Jocasta \u2014 CRM', slug: 'agents/jocasta' },
						{ label: 'Mothma \u2014 Operations', slug: 'agents/mothma' },
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
						{ label: 'Operational State', slug: 'operations/operational-state' },
						{ label: 'Implementation Audit', slug: 'operations/implementation-audit' },
						{ label: 'Feature Status Matrix', slug: 'operations/feature-status-matrix' },
						{ label: 'Runtime Drift Audit', slug: 'operations/runtime-drift-audit' },
						{ label: 'Operational History', slug: 'operations/operational-history' },
						{ label: 'Stability Window', slug: 'operations/stability-window' },
						{ label: 'Roadmap', slug: 'operations/roadmap' },
					],
				},
			],
		}),
	],
});
