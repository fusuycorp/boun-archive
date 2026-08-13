<script lang="ts">
    import { auth } from '$lib/stores/auth.svelte';
    import { X } from 'lucide-svelte';

    let { show = $bindable(false) } = $props();
    let email = $state('');
    let status = $state<'idle' | 'loading' | 'success' | 'error'>('idle');
    let errorMessage = $state('');

    async function handleSubmit(e: Event) {
        e.preventDefault();
        if (!email) return;

        status = 'loading';
        try {
            await auth.sendMagicLink(email);
            status = 'success';
        } catch (err: any) {
            status = 'error';
            errorMessage = err.message || 'An error occurred';
        }
    }

    function close() {
        show = false;
        status = 'idle';
        email = '';
        errorMessage = '';
    }
</script>

{#if show}
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
        <div class="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl dark:bg-gray-800">
            <div class="mb-4 flex items-center justify-between">
                <h2 class="text-xl font-bold">Sign In</h2>
                <button onclick={close} class="rounded-full p-2 hover:bg-gray-100 dark:hover:bg-gray-700">
                    <X class="h-5 w-5" />
                </button>
            </div>

            {#if status === 'success'}
                <div class="rounded-lg bg-green-50 p-4 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                    <p class="font-medium">Check your email!</p>
                    <p class="text-sm">We've sent a magic link to {email}.</p>
                </div>
            {:else}
                <form onsubmit={handleSubmit} class="space-y-4">
                    <div>
                        <label for="email" class="mb-1 block text-sm font-medium">Student Email</label>
                        <input
                            type="email"
                            id="email"
                            bind:value={email}
                            placeholder="username@boun.edu.tr"
                            required
                            class="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-700"
                            disabled={status === 'loading'}
                        />
                    </div>

                    {#if status === 'error'}
                        <p class="text-sm text-red-500">{errorMessage}</p>
                    {/if}

                    <button
                        type="submit"
                        disabled={status === 'loading'}
                        class="w-full rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                        {status === 'loading' ? 'Sending...' : 'Send Magic Link'}
                    </button>
                </form>
            {/if}
        </div>
    </div>
{/if}
