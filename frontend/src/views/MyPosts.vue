<template>
  <div class="my-posts">
    <div class="header-actions">
      <h1>我的帖子</h1>
      <button @click="showCreateModal = true" class="create-btn">
        + 发布新帖
      </button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    
    <div v-else class="post-list">
      <div v-for="post in posts" :key="post.id" class="post-card">
        <router-link :to="'/post/' + post.id" class="post-link">
          <h2>{{ post.title }}</h2>
          <p class="post-snippet">{{ post.content_snippet }}</p>
          <div class="post-meta">
            <span>浏览: {{ post.view_count }}</span>
            <span>评论: {{ post.comment_count }}</span>
            <span>{{ formatDate(post.created_at) }}</span>
          </div>
        </router-link>
        <div class="post-actions">
           <!-- Verify if delete logic is needed here or just in detail -->
           <button @click.prevent="deletePost(post.id)" class="delete-btn">删除</button>
        </div>
      </div>
      
      <div v-if="posts.length === 0" class="empty-state">
        您还没有发布过帖子。
      </div>

      <div class="pagination" v-if="total > pageSize">
        <button :disabled="page === 1" @click="changePage(page - 1)">上一页</button>
        <span>第 {{ page }} 页</span>
        <button :disabled="posts.length < pageSize" @click="changePage(page + 1)">下一页</button>
      </div>
    </div>

    <CreatePostModal 
      v-if="showCreateModal" 
      @close="showCreateModal = false"
      @created="fetchPosts" 
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api';
import { useAuthStore } from '../stores/auth';
import CreatePostModal from '../components/CreatePostModal.vue';

const authStore = useAuthStore();
const posts = ref([]);
const loading = ref(true);
const showCreateModal = ref(false);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);

const fetchPosts = async () => {
  loading.value = true;
  
  // Ensure user data is loaded
  if (!authStore.user && authStore.token) {
      await authStore.fetchUser();
  }

  if (!authStore.user) {
      loading.value = false;
      return;
  }
  
  try {
    const res = await api.get('/posts', {
      params: { 
        page: page.value, 
        pageSize: pageSize.value,
        user_id: authStore.user.id 
      }
    });
    const data = res.data.data;
    posts.value = data.list;
    total.value = data.pagination.total;
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};

const deletePost = async (postId) => {
  if (!confirm('确定要删除这条帖子吗？')) return;
  
  try {
    await api.delete(`/posts/${postId}`);
    // Optimistic update: remove from local list
    posts.value = posts.value.filter(p => p.id !== postId);
    total.value--;
  } catch (error) {
    alert('删除失败: ' + (error.response?.data?.detail || error.message));
  }
};

const changePage = (newPage) => {
  if (newPage < 1) return;
  page.value = newPage;
  fetchPosts();
};

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString();
};

onMounted(() => {
    fetchPosts();
});
</script>

<style scoped>
.my-posts {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.post-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.create-btn {
  background-color: var(--primary-color);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 20px;
  font-weight: bold;
  box-shadow: var(--shadow-sm);
}

.post-card {
  background: white;
  padding: 20px;
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s, box-shadow 0.2s;
  border: 1px solid transparent;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.post-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary-color);
}

.post-link {
  text-decoration: none;
  color: inherit;
  display: block;
  flex-grow: 1;
}

.post-snippet {
  color: #666;
  margin: 10px 0;
}

.post-meta {
  font-size: 0.85rem;
  color: #999;
  display: flex;
  gap: 15px;
  margin-top: auto;
}

.post-actions {
    margin-top: 15px;
    border-top: 1px solid #eee;
    padding-top: 10px;
    text-align: right;
}

.delete-btn {
    background: #ff4d4f;
    color: white;
    border: none;
    padding: 5px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85rem;
}

.pagination {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
  align-items: center;
  grid-column: 1 / -1;
}

.pagination button {
  padding: 5px 15px;
  background: white;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading, .empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
  grid-column: 1 / -1;
}

@media (max-width: 768px) {
  .post-list {
    grid-template-columns: 1fr;
  }
}
</style>
