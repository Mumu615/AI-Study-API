<template>
  <div class="post-detail-container" v-if="post">
    <div class="post-header">
      <div class="header-top">
        <router-link to="/" class="back-link">&larr; 返回首页</router-link>
        <button 
          v-if="authStore.user && post && authStore.user.id === post.user_id" 
          @click="deletePost" 
          class="delete-btn"
        >
          删除帖子
        </button>
      </div>
      <h1>{{ post.title }}</h1>
      <div class="post-info">
        <span>作者: {{ post.user_id }}</span>
        <span>{{ formatDate(post.created_at) }}</span>
        <span>浏览: {{ post.view_count }}</span>
      </div>
    </div>

    <div class="post-content">
      {{ post.content }}
    </div>

    <div class="comments-section">
      <h3>评论 ({{ post.comment_count }})</h3>
      
      <!-- Root Reply Box -->
      <div v-if="authStore.isAuthenticated" class="root-reply-box">
        <textarea v-model="newComment" placeholder="写下你的评论..."></textarea>
        <button @click="submitRootComment" :disabled="submitting">发表评论</button>
      </div>
      <div v-else>
        <p><router-link to="/login">登录</router-link> 参与评论。</p>
      </div>

      <div class="comments-list">
        <CommentItem 
          v-for="comment in comments" 
          :key="comment.id" 
          :comment="comment"
          :post-user-id="post.user_id"
          :post-id="post.id"
          @refresh="fetchComments"
        />
        
        <button v-if="hasMoreComments" @click="loadMoreComments" class="load-more">
          加载更多评论
        </button>
      </div>
    </div>
  </div>
  <div v-else-if="loading" class="loading">加载中...</div>
  <div v-else class="error">帖子不存在</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import api from '../api';
import { useAuthStore } from '../stores/auth';
import CommentItem from '../components/CommentItem.vue';

const route = useRoute();
const authStore = useAuthStore();

const post = ref(null);
const comments = ref([]);
const loading = ref(true);
const submitting = ref(false);
const newComment = ref('');

const page = ref(1);
const pageSize = ref(10);
const hasMoreComments = ref(false);

const postId = route.params.id;

const fetchPost = async () => {
  try {
    const res = await api.get(`/posts/${postId}`);
    post.value = res.data.data;
  } catch (error) {
    console.error("Fetch post error", error);
  }
};

const fetchComments = async (reset = true) => {
  if (reset) {
    page.value = 1;
    comments.value = [];
  }
  
  try {
    const res = await api.get(`/posts/${postId}/comments`, {
      params: { page: page.value, pageSize: pageSize.value }
    });
    const data = res.data.data;
    
    if (reset) {
      comments.value = data.list;
    } else {
      comments.value = [...comments.value, ...data.list];
    }
    
    // Check if more
    hasMoreComments.value = data.list.length === pageSize.value; // Approximate check, or use total
    
  } catch (error) {
    console.error("Fetch comments error", error);
  }
};

const loadMoreComments = () => {
  page.value++;
  fetchComments(false);
};

const submitRootComment = async () => {
  if (!newComment.value.trim()) return;
  submitting.value = true;
  try {
    await api.post(`/posts/${postId}/comments`, {
      content: newComment.value,
      post_id: postId
      // parent_id is null for root
    });
    newComment.value = '';
    // Refresh comments (and post to update count if we wanted, but count is on post obj)
    fetchComments(true);
    fetchPost(); // Update count
  } catch (error) {
    alert('发表评论失败');
  } finally {
    submitting.value = false;
  }
};

const formatDate = (d) => new Date(d).toLocaleString();

const deletePost = async () => {
  if (!confirm('确定要删除这条帖子吗？')) return;
  try {
    await api.delete(`/posts/${postId}`);
    alert('删除成功');
    // Go back to my posts or home
    window.location.href = '/my-posts'; 
  } catch (error) {
    alert('删除失败: ' + (error.response?.data?.detail || error.message));
  }
};

onMounted(async () => {
    loading.value = true;
    
    // Ensure user data is loaded for permission checks
    if (!authStore.user && authStore.token) {
       await authStore.fetchUser();
    }

    await Promise.all([fetchPost(), fetchComments()]);
    loading.value = false;
});
</script>

<style scoped>
.post-detail-container {
  max-width: 800px;
  margin: 0 auto;
  background: white;
  padding: 30px;
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.back-link {
  display: inline-block;
  /* margin-bottom removed as handled by flex container */
}

.delete-btn {
    background: #ff4d4f;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
}

.post-header h1 {
  margin-bottom: 10px;
}

.post-info {
  color: #666;
  font-size: 0.9rem;
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  border-bottom: 1px solid #eee;
  padding-bottom: 20px;
}

.post-content {
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: 40px;
  white-space: pre-wrap;
}

.comments-section h3 {
  border-bottom: 2px solid var(--primary-color);
  display: inline-block;
  margin-bottom: 20px;
  padding-bottom: 5px;
}

.root-reply-box {
  margin-bottom: 30px;
}

.root-reply-box textarea {
  width: 100%;
  height: 80px;
  padding: 10px;
  margin-bottom: 10px;
}

.root-reply-box button {
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 8px 20px;
  border-radius: 4px;
}

.load-more {
  display: block;
  margin: 20px auto;
  padding: 10px 20px;
  background: #f8f9fa;
  border: 1px solid #ddd;
}
</style>
