import { defineStore } from 'pinia';
import api from '../api';
import router from '../router';

export const useAuthStore = defineStore('auth', {
    state: () => ({
        token: localStorage.getItem('token') || null,
        user: null,
    }),
    getters: {
        isAuthenticated: (state) => !!state.token,
    },
    actions: {
        async login(username, password) {
            try {
                // Form Data for OAuth2
                const formData = new URLSearchParams();
                formData.append('username', username);
                formData.append('password', password);

                const response = await api.post('/token', formData, {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                });

                this.token = response.data.access_token;
                localStorage.setItem('token', this.token);

                await this.fetchUser();

                router.push('/');
                return true;
            } catch (error) {
                console.error("Login failed", error);
                throw error;
            }
        },
        async register(username, password, avatar_url) {
            try {
                await api.post('/users', {
                    username,
                    password,
                    avatar_url
                });
                return true;
            } catch (error) {
                console.error("Registration failed", error);
                throw error;
            }
        },
        async fetchUser() {
            try {
                const response = await api.get('/users/me');
                this.user = response.data.data;
            } catch (error) {
                this.logout();
            }
        },
        logout() {
            this.token = null;
            this.user = null;
            localStorage.removeItem('token');
            router.push('/login');
        }
    }
});
