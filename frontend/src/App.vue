<template>
  <div id="app-container">
    <nav class="navbar">
      <div class="logo"><router-link to="/">学习社区</router-link></div>
      <div class="nav-links">
        <router-link to="/">首页</router-link>
        <span v-if="authStore.isAuthenticated">
          <router-link to="/my-posts">我的帖子</router-link>
          <a href="#" @click.prevent="logout">退出登录</a>
        </span>
        <span v-else>
          <router-link to="/login">登录</router-link>
          <router-link to="/register">注册</router-link>
        </span>
      </div>
    </nav>
    <main class="main-content">
      <router-view></router-view>
    </main>
  </div>
</template>

<script setup>
import { useAuthStore } from './stores/auth';
import { useRouter } from 'vue-router';

const authStore = useAuthStore();
const router = useRouter();

const logout = () => {
  authStore.logout();
};
</script>

<style scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.logo a {
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
  text-decoration: none;
}

.nav-links a {
  margin-left: 20px;
  text-decoration: none;
  color: #666;
}

.nav-links a.router-link-active {
  color: #42b983;
}

.main-content {
  padding: 2rem;
}
</style>
