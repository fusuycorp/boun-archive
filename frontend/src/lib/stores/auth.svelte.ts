import { account } from '$lib/appwrite';
import { ID } from 'appwrite';
import type { Models } from 'appwrite';

class AuthStore {
    user = $state<Models.User<Models.Preferences> | null>(null);
    loading = $state(true);

    async checkSession() {
        try {
            this.loading = true;
            this.user = await account.get();
        } catch (error) {
            this.user = null;
        } finally {
            this.loading = false;
        }
    }

    async sendMagicLink(email: string) {
        try {
            await account.createMagicURLToken(
                ID.unique(),
                email,
                window.location.origin + '/calendar'
            );
            return true;
        } catch (error) {
            console.error(error);
            throw error;
        }
    }

    async logout() {
        try {
            await account.deleteSession('current');
            this.user = null;
        } catch (error) {
            console.error(error);
            throw error;
        }
    }
}

export const auth = new AuthStore();
