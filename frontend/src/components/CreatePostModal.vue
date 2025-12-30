<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal-content">
      <header class="modal-header">
        <h3>发布新帖</h3>
        <button class="close-btn" @click="$emit('close')">×</button>
      </header>
      <form @submit.prevent="submitPost">
        <div class="form-group">
          <label>标题</label>
          <input v-model="title" type="text" required placeholder="请输入标题..." />
        </div>
        <div class="form-group">
          <label>内容</label>
          <textarea v-model="content" rows="6" required placeholder="分享你的想法..."></textarea>
        </div>
        <div class="modal-actions">
          <button type="button" class="cancel-btn" @click="$emit('close')">取消</button>
          <button type="submit" :disabled="loading" class="submit-btn">
            {{ loading ? '发布中...' : '发布' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import api from '../api';

const emit = defineEmits(['close', 'created']);
const title = ref('');
const content = ref('');
const loading = ref(false);

const submitPost = async () => {
  if (!title.value.trim() || !content.value.trim()) return;
  
  loading.value = true;
  try {
    const res = await api.post('/posts', {
      title: title.value,
      content: content.value
    });
    // Check code 201
    if (res.data.code === 201) {
       emit('created');
       emit('close');
    }
  } catch (error) {
    alert('发布失败');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 20px;
  border-radius: var(--radius);
  width: 90%;
  max-width: 500px;
  box-shadow: var(--shadow-md);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
}

.form-group {
  margin-bottom: 15px;
}
.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}
.form-group input, .form-group textarea {
  width: 100%;
  padding: 10px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.submit-btn {
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
}

.cancel-btn {
  background: transparent;
  border: 1px solid #ccc;
  padding: 8px 16px;
  border-radius: 4px;
}
</style>
