import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import Home from '../views/Home.vue';
import Login from '../views/Login.vue';
import Register from '../views/Register.vue';

const routes = [
    {
        path: '/',
        name: 'Home',
        component: Home,
    },
    {
        path: '/login',
        name: 'Login',
        component: Login,
    },
    {
        path: '/register',
        name: 'Register',
        component: Register,
    },
    {
        path: '/post/:id',
        name: 'PostDetail',
        component: () => import('../views/PostDetail.vue'),
    },
    {
        path: '/my-posts',
        name: 'MyPosts',
        component: () => import('../views/MyPosts.vue'),
        meta: { requiresAuth: true }
    },

];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

// Navigation Guard
router.beforeEach((to, from, next) => {
    // const authStore = useAuthStore(); // Can't use here directly outside of component or valid injection context unless Pinia is active?
    // Actually Pinia stores can be used anywhere after instance is created and installed.
    // We need to pass pinia instance or rely on single instance pattern.
    // Best practice: internal usage inside beforeEach

    // Checking public pages
    const publicPages = ['/login', '/register', '/'];
    const authRequired = !publicPages.includes(to.path);
    const loggedIn = localStorage.getItem('token');

    // If auth required and not logged in, redirect to login
    // Note: For now, Home is public. Create Post will be private.
    next();
});

export default router;
