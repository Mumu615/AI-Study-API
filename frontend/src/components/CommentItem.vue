<template>
  <div class="comment-item" :class="{ 'is-reply': isReply }">
    <div class="comment-content-wrapper">
      <div v-if="comment.user || comment.content !== '该评论已删除'" class="comment-meta">
        <strong v-if="comment.user">{{ comment.user.username }}</strong>
        <span v-else class="deleted-user">[已注销]</span>
        
        <span class="meta-date">{{ formatDate(comment.created_at) }}</span>
        
        <span v-if="comment.reply_to_user" class="reply-to">
          回复 @{{ comment.reply_to_user.username }}
        </span>
      </div>

      <div class="comment-body" :class="{ 'deleted-text': comment.content === '该评论已删除' }">
        {{ comment.content }}
      </div>

      <div class="comment-actions" v-if="authStore.isAuthenticated && comment.content !== '该评论已删除'">
        <button @click="showReplyBox = !showReplyBox" class="action-btn">回复</button>
        <button v-if="canDelete" @click="deleteComment" class="action-btn delete-btn">删除</button>
      </div>

      <!-- Reply Box -->
      <div v-if="showReplyBox" class="reply-box">
        <textarea v-model="replyContent" placeholder="写下你的回复..."></textarea>
        <div class="reply-actions">
          <button @click="submitReply" :disabled="submitting">提交</button>
          <button @click="showReplyBox = false">取消</button>
        </div>
      </div>
    </div>

    <!-- Lazy Replies Toggle -->
    <div v-if="!isReply && comment.reply_count > 0 && !repliesLoaded" class="replies-toggle">
        <button @click="loadReplies" class="toggle-btn" :disabled="loadingReplies">
          {{ loadingReplies ? '加载中...' : `查看 ${comment.reply_count} 条回复` }}
        </button>
    </div>

    <!-- Recursive Replies -->
    <div v-if="repliesLoaded && localReplies.length > 0" class="replies-list">
      <CommentItem 
        v-for="reply in localReplies" 
        :key="reply.id" 
        :comment="reply"
        :is-reply="true"
        :post-user-id="postUserId"
        :post-id="postId"
        @refresh="$emit('refresh')"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useAuthStore } from '../stores/auth';
import api from '../api';

const props = defineProps({
  comment: Object,
  isReply: Boolean,
  postUserId: Number, // Need to know post owner to determine delete permissions
  postId: Number // Required for API calls since comment object might not have it
});

const emit = defineEmits(['refresh']);

const authStore = useAuthStore();
const showReplyBox = ref(false);
const replyContent = ref('');
const submitting = ref(false);

const localReplies = ref(props.comment.replies || []);
const repliesLoaded = ref(false);
const loadingReplies = ref(false);

// Initialize loaded state: if passed replies are non-empty, we assume loaded
if (localReplies.value.length > 0) {
    repliesLoaded.value = true;
} else if (props.isReply) {
    // Replies don't have further replies displayed in this 2-level system usually, 
    // or if they do, they are passed down? 
    // Actually, in 2-level system, replies are flat list under root.
    // So isReply items won't have children usually.
    repliesLoaded.value = true; 
}

const loadReplies = async () => {
    loadingReplies.value = true;
    try {
        const res = await api.get(`/comments/${props.comment.id}/replies`);
        localReplies.value = res.data.data;
        repliesLoaded.value = true;
    } catch (e) {
        console.error(e);
        alert('加载回复失败');
    } finally {
        loadingReplies.value = false;
    }
}

const formatDate = (date) => new Date(date).toLocaleString();

const canDelete = computed(() => {
  if (!authStore.user) return false;
  const uid = authStore.user.id;
  // 1. Admin (id=1) 
  if (uid === 1) return true;
  // 2. Author of comment
  if (props.comment.user_id === uid) return true;
  // 3. Author of post
  if (props.postUserId === uid) return true;
  return false;
});

const submitReply = async () => {
  if (!replyContent.value.trim()) return;
  submitting.value = true;
  try {
    await api.post(`/posts/${props.postId}/comments`, {
      content: replyContent.value,
      parent_id: props.comment.id,
      post_id: props.postId
      // root_id logic is handled by backend or derived? 
      // API expects parent_id. Backend sets root_id based on parent.
    });
    replyContent.value = '';
    showReplyBox.value = false;
    emit('refresh');
  } catch (error) {
    alert('回复失败');
  } finally {
    submitting.value = false;
  }
};

const deleteComment = async () => {
  if (!confirm('确定删除该评论吗？')) return;
  try {
    await api.delete(`/comments/${props.comment.id}`);
    emit('refresh');
  } catch (error) {
    alert('删除失败');
  }
};
</script>

<style scoped>
.comment-item {
  margin-bottom: 15px;
}

.comment-content-wrapper {
  background: white;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #eee;
}

.is-reply {
  margin-left: 20px; /* Indent for replies */
  border-left: 2px solid #eee;
  padding-left: 10px;
}

.comment-meta {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 5px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.deleted-user {
  font-style: italic;
  color: #999;
}

.reply-to {
  color: #888;
  font-size: 0.8rem;
}

.comment-body {
  margin-bottom: 8px;
  line-height: 1.4;
}

.deleted-text {
  color: #999;
  font-style: italic;
  background-color: #f5f5f5;
  padding: 2px 5px;
  border-radius: 3px;
}

.comment-actions {
  display: flex;
  gap: 10px;
  font-size: 0.8rem;
}

.action-btn {
  background: none;
  border: none;
  color: var(--primary-color);
  padding: 0;
  cursor: pointer;
  font-size: 0.8rem;
}

.delete-btn {
  color: #e74c3c;
}

.reply-box {
  margin-top: 10px;
}

.reply-box textarea {
  width: 100%;
  height: 60px;
  margin-bottom: 5px;
  padding: 5px;
}
.reply-box textarea {
  width: 100%;
  height: 60px;
  margin-bottom: 5px;
  padding: 5px;
}

.replies-toggle {
    margin-left: 20px;
    margin-top: 10px;
}

.toggle-btn {
    background: #f0f2f5;
    border: none;
    color: #555;
    padding: 5px 12px;
    border-radius: 12px;
    cursor: pointer;
    font-size: 0.85rem;
}
.toggle-btn:hover {
    background: #e4e6eb;
}
</style>
