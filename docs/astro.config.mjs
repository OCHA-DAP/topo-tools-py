// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// Empty for a custom domain; "/<repo>" for GitHub's default project-pages
// subpath. Set by .github/workflows/docs.yml via actions/configure-pages.
const base = process.env.BASE_PATH ?? '';

// https://astro.build/config
export default defineConfig({
	site: 'https://ocha-dap.github.io',
	base,
	integrations: [
		starlight({
			title: 'Topo Tools',
			social: [
				{ icon: 'github', label: 'topo-tools-py', href: 'https://github.com/OCHA-DAP/topo-tools-py' },
			],
			sidebar: [
				{ label: 'Tutorials', items: [{ autogenerate: { directory: 'tutorials' } }] },
				{ label: 'How-to', items: [{ autogenerate: { directory: 'how-to' } }] },
				{ label: 'Explanation', items: [{ autogenerate: { directory: 'explanation' } }] },
				{ label: 'Reference', items: [{ autogenerate: { directory: 'reference' } }] },
			],
		}),
	],
});
